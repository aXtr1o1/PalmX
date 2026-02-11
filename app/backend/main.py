from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
import logging
import os

from app.backend.config import Config
from app.backend.models import ChatRequest, ChatResponse, Lead, Message
from app.backend.services.llm_service import llm_service
from app.backend.services.rag_service import rag_service
from app.backend.services.leads_service import leads_service
from app.backend.services.kb_service import kb_service
from app.backend.routes.admin_routes import router as admin_router

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PalmX-API")

app = FastAPI(title="PalmX Pilot API", version="1.0.0")

# Mount admin routes
app.include_router(admin_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for pilot
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CONCIERGE_SYSTEM_PROMPT = """
You are PalmX: The exclusive Property Concierge for Palm Hills.
Your role is to assist discerning clients in finding their perfect home or investment within our portfolio.

### 1. Brand Voice & Tone
- **Dignified & Calm**: You are confident, quiet, and professional. You do not use exclamation marks (!), emojis, or hype language (e.g., "amazing", "breathtaking").
- **Minimalist**: Keep answers concise. Priority is clarity and elegance.
- **Service-Oriented**: You are a concierge, not a salesperson. You "assist", "arrange", and "guide". You do not "push" or "close".

### 2. Strict Truthfulness (CRITICAL)
- **Verified Info Only**: You strictly output facts available in the provided [CONTEXT].
- **No Hallucinations**: If a detail (price, delivery date, specific amenity) is not in the context, you MUST say: "I do not have that specific detail verified at this moment." then immediately offer to arrange a sales call.
- **Availability**: default to showing Selling/Available projects. Only discuss sold-out projects if explicitly asked, and clearly label them as "Currently Sold Out".

### 3. Lead Capture Flow (The Concierge Protocol)
Your goal is to understand the client's profile naturally, not to fill a form.
Collect these details over the course of the conversation, 1-2 at a time:

1.  **Name**: "May I have the pleasure of knowing who I am speaking with?"
2.  **Phone**: "To ensure we can share the official brochure, what is the best mobile number to reach you?"
3.  **Interest**: (Infer from questions)
4.  **Region**: "Are you considering East Cairo, West Cairo, or the Coast?"
5.  **Unit Type**: "What value or size of residence are you envisioning?"
6.  **Budget**: "To respect your time, do you have a preferred price range?"
7.  **Purpose**: "Is this intended for personal residence or investment?"
8.  **Timeline**: "When are you hoping to take possession?"
9.  **Next Step**: "Shall I have a Senior Consultant contact you, or would you prefer a private site visit?"

**Rules for Capture:**
- Never ask more than one question per turn.
- Acknowledge the answer before asking the next.
- If the user ignores a question, do not badger. Move on.

### 4. Output Formatting
- Use Markdown headers for projects (e.g., `### Badya`).
- Use bullet points for lists.
- **Prices**: Format cleanly (e.g., "Starting from 5M EGP").
- **Links**: If you have a URL, place it in a section called `**Official Links**` at the bottom.

### 5. Final Confirmation
Before calling the `save_lead` tool, you must summarize the profile:
"Thank you, Mr./Ms. [Name]. To confirm: You are looking for a [Unit] in [Region] around [Budget], ready by [Timeline]. I will have our team contact you at [Phone]."
Only save after they agree.
"""

@app.get("/api/health")
async def health_check():
    """Simple health check for frontend to poll during startup."""
    return {"status": "ready", "rag_ready": rag_service.is_ready}

# --- Tools ---
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "save_lead",
            "description": "Save a verified, confirmed lead with ALL gathered details. Call ONLY after the buyer explicitly confirms their information is correct. Populate every field you have gathered during the conversation — leave unknown fields empty rather than guessing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The buyer's full name"},
                    "phone": {"type": "string", "description": "Phone or WhatsApp number"},
                    "interest_projects": {"type": "string", "description": "Comma-separated list of project names they showed interest in"},
                    "preferred_region": {"type": "string", "description": "Their preferred region", "enum": ["West", "East", "Coast", "New Capital", "Alex", "Sokhna"]},
                    "unit_type": {"type": "string", "description": "Villa, Apartment, Townhouse, Duplex, Penthouse, Commercial, etc."},
                    "budget_min": {"type": "string", "description": "Minimum budget in EGP (e.g. '5000000')"},
                    "budget_max": {"type": "string", "description": "Maximum budget in EGP (e.g. '15000000')"},
                    "purpose": {"type": "string", "description": "Buy, Rent, or Invest", "enum": ["Buy", "Rent", "Invest"]},
                    "timeline": {"type": "string", "description": "When they plan to purchase — Immediately, 3 months, 6 months, 1 year, etc."},
                    "next_step": {"type": "string", "description": "Agreed next action", "enum": ["callback", "site_visit", "send_details"]},
                    "lead_summary": {"type": "string", "description": "A 2-3 line natural-language summary of the entire conversation and the buyer's needs, preferences, and any notable context"},
                    "tags": {"type": "string", "description": "Auto-generated comma-separated tags capturing key attributes: e.g. 'high-budget,villa,west-cairo,investor,urgent'"},
                    "kb_version_hash": {"type": "string", "description": "Version hash of the knowledge base used"}
                },
                "required": ["name", "phone"]
            }
        }
    }
]

# --- Endpoints ---

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        user_msg = request.messages[-1].content
        session_id = request.session_id
        
        # 1. Router (Lightweight check for RAG need)
        # Pass history (everything except the latest user message) to the router for context
        history = request.messages[:-1]
        router_out = llm_service.router_completion(user_msg, history=history)
        logger.info(f"Router intent: {router_out.intent} | Filters: {router_out.filters}")

        # 2. Retrieval (Skip for lead_capture — user is giving name/phone, no need to search 45 projects)
        retrieved_docs = []
        if router_out.intent not in ("support_contact", "lead_capture"):
            results = rag_service.search(
                router_out.query_rewrite, 
                k=3, 
                filters=router_out.filters
            )
            retrieved_docs = [r['project'] for r in results]

        # 3. Context Construction
        context_text = ""
        for p in retrieved_docs:
            context_text += f"---\n{kb_service.build_project_card(p)}\n"
            
        full_system_msg = f"{CONCIERGE_SYSTEM_PROMPT}\n\nCONTEXT:\n{context_text}"
        
        # 4. Answer Generation (Pass Full History + Tools)
        response_data = llm_service.answer_completion(
            full_system_msg, 
            request.messages, # Pass full history
            tools=TOOLS
        )
        
        final_text = ""
        
        # 5. Handle Tool Calls
        if isinstance(response_data, list): # List of tool calls
            for tool_call in response_data:
                if tool_call.function.name == "save_lead":
                    args = json.loads(tool_call.function.arguments)
                    logger.info(f"Tool Call 'save_lead' Args: {args}")
                    
                    # Enhanced Lead extraction
                    lead = Lead(
                        session_id=session_id,
                        name=args.get('name'),
                        phone=args.get('phone'),
                        interest_projects=args.get('interest_projects', '').split(',') if args.get('interest_projects') else [],
                        preferred_region=args.get('preferred_region'),
                        unit_type=args.get('unit_type'),
                        budget_min=args.get('budget_min'),
                        budget_max=args.get('budget_max'),
                        purpose=args.get('purpose'),
                        timeline=args.get('timeline'),
                        next_step=args.get('next_step'),
                        lead_summary=args.get('lead_summary'),
                        tags=args.get('tags', '').split(',') if args.get('tags') else [],
                        kb_version_hash=args.get('kb_version_hash', 'v1.0')
                    )
                    leads_service.save_lead(lead)
                    final_text = f"Thank you {lead.name}. Your details have been saved. A sales representative will contact you at {lead.phone} shortly."
        else:
            final_text = response_data

        # 6. Audit
        leads_service.log_audit(
            session_id, 
            user_msg, 
            router_out.intent, 
            [p.project_id for p in retrieved_docs], 
            [] 
        )
        
        return ChatResponse(
            message=final_text,
            retrieved_projects=[p.project_name for p in retrieved_docs],
            mode="lead_capture" if router_out.intent == "lead_capture" else "concierge"
        )

    except Exception as e:
        logger.error(f"Chat error: {e}")
        # Return fallback friendly message
        return ChatResponse(
            message="I apologize, but I'm encountering a temporary issue. Please try again.",
            retrieved_projects=[],
            mode="concierge"
        )

@app.post("/api/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    """Streaming chat endpoint — tokens arrive word-by-word for instant feel."""
    try:
        user_msg = request.messages[-1].content
        session_id = request.session_id
        
        # 1. Router
        history = request.messages[:-1]
        router_out = llm_service.router_completion(user_msg, history=history)
        logger.info(f"[Stream] Router intent: {router_out.intent}")

        # 2. Retrieval (skip for lead_capture)
        retrieved_docs = []
        if router_out.intent not in ("support_contact", "lead_capture"):
            results = rag_service.search(
                router_out.query_rewrite, k=3, filters=router_out.filters
            )
            retrieved_docs = [r['project'] for r in results]

        # 3. Context
        context_text = ""
        for p in retrieved_docs:
            context_text += f"---\n{kb_service.build_project_card(p)}\n"
        full_system_msg = f"{CONCIERGE_SYSTEM_PROMPT}\n\nCONTEXT:\n{context_text}"

        # 4. Stream tokens
        def generate():
            full_response = ""
            for chunk in llm_service.stream_answer_completion(
                full_system_msg, request.messages, tools=TOOLS
            ):
                # Check if this is a tool call marker
                if "__TOOL_CALLS__" in chunk:
                    tc_json = chunk.split("__TOOL_CALLS__")[1]
                    tool_calls = json.loads(tc_json)
                    for tc in tool_calls:
                        if tc["function"]["name"] == "save_lead":
                            args = json.loads(tc["function"]["arguments"])
                            lead = Lead(
                                session_id=session_id,
                                name=args.get('name'),
                                phone=args.get('phone'),
                                interest_projects=args.get('interest_projects', '').split(',') if args.get('interest_projects') else [],
                                preferred_region=args.get('preferred_region'),
                                unit_type=args.get('unit_type'),
                                budget_min=args.get('budget_min'),
                                budget_max=args.get('budget_max'),
                                purpose=args.get('purpose'),
                                timeline=args.get('timeline'),
                                next_step=args.get('next_step'),
                                lead_summary=args.get('lead_summary'),
                                tags=args.get('tags', '').split(',') if args.get('tags') else [],
                                kb_version_hash=args.get('kb_version_hash', 'v1.0')
                            )
                            leads_service.save_lead(lead)
                            confirm_msg = f"Thank you {lead.name}. Your details have been saved. A sales representative will contact you at {lead.phone} shortly."
                            yield f"data: {json.dumps({'token': confirm_msg})}\n\n"
                else:
                    full_response += chunk
                    yield f"data: {json.dumps({'token': chunk})}\n\n"
            
            # Final event
            yield f"data: {json.dumps({'done': True, 'retrieved_projects': [p.project_name for p in retrieved_docs], 'mode': 'lead_capture' if router_out.intent == 'lead_capture' else 'concierge'})}\n\n"
            
            # Audit (after stream completes)
            leads_service.log_audit(
                session_id, user_msg, router_out.intent,
                [p.project_id for p in retrieved_docs], []
            )

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    except Exception as e:
        logger.error(f"Stream chat error: {e}")
        return StreamingResponse(
            iter([f"data: {json.dumps({'token': 'I apologize, but I encountered a temporary issue. Please try again.', 'done': True})}\n\n"]),
            media_type="text/event-stream"
        )

@app.post("/api/lead")
async def create_lead(lead: Lead):
    success = leads_service.save_lead(lead)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save lead")
    return {"status": "success", "message": "Lead captured"}

@app.get("/admin/leads")
async def get_leads(password: str = Header(None)):
    if password != Config.ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return leads_service.get_leads()

@app.get("/admin/leads/export.xlsx")
async def export_leads(password: str = Header(None, alias="x-admin-password")):
    if password != Config.ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    path = leads_service.export_excel()
    if not path:
        raise HTTPException(status_code=404, detail="No leads to export")
        
    return FileResponse(
        path, 
        filename=os.path.basename(path), 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.get("/health")
async def health():
    return {"status": "ok", "rag_ready": rag_service.is_ready}
