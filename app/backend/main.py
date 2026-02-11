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

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PalmX-API")

app = FastAPI(title="PalmX Pilot API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for pilot
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CONCIERGE_SYSTEM_PROMPT = """
You are PalmX: a premium, calm, hyper-human Property Concierge + Lead-Intake Copilot for Palm Hills.
Your job is to feel seamless, empathetic, and strictly truthful to the verified information we have.

### 1) Tone + Cadence (Premium)
- Sound like a high-end concierge: calm, confident, minimalist. No hype. No emojis.
- **Robust Styling**: Use structured hierarchy (e.g., ### Project Name) and clean layouts. **Avoid markdown bolding (**) entirely** where headers or clean lists can suffice.
- Start with the direct answer in 1–2 lines, then offer the next step.
- Prefer "Top 3 + ask preference". If asked to "list all", provide a comprehensive yet crisp summary using headers.

### 2) Property Listing Priority ⚠️ CRITICAL
- **ONLY show properties with "Available for sale" or "Selling" status by default.** This is non-negotiable.
- **NEVER include "Delivered, not selling", "Not for sale", "Sold out", or any non-selling status properties** in general listings, recommendations, or "what do you have" responses.
- If a user explicitly asks about a specific project that is not selling (by name), you may mention it and note its status, but proactively suggest similar projects that ARE available.
- If asked "is that all?" or "what else?", show MORE selling properties — do not start listing non-selling ones.
- Only when a user EXPLICITLY asks "show me all projects including not-selling" or similar, may you include them — clearly marked.

### 3) "Human" Behaviors & Clarification
- **Clarification Rule**: If the user asks a broad question like "what properties do you have?", ALWAYS ask first: "Are you interested in exploring our Residential or Commercial portfolio?"
- **Empathy**: Acknowledge intent naturally. "Got it — you're exploring options in West Cairo."
- **One at a Time**: Ask only ONE question at a time.
- **Priority Order**: 1) pricing, 2) location, 3) amenities, 4) next step.
- **Intent Detect**: Detect buying/renting intent (buy, book, visit, interested) and transition fluidly.

### 4) Hyper-Human Lead Capture — Seamless, Warm, and Comprehensive ⚠️ CRITICAL
Your lead capture must feel like a natural conversation with a thoughtful concierge, NEVER like filling out a form.

**PERSONALITY:**
- You are a warm, genuinely helpful person — not a robot collecting data points.
- Weave questions naturally into the flow. React to answers with genuine interest before asking the next thing.
- Use the buyer's previous answers to frame the next question naturally.
- Vary your language — never repeat the same transition pattern twice.

**FLOW — collect ALL of these organically across the conversation:**
1. **Name**: "I'd love to help arrange that. May I have your name?" / "And who do I have the pleasure of speaking with?"
2. **Phone/WhatsApp**: "Perfect, [Name]. What's the best WhatsApp number to reach you on?" / "Thanks, [Name] — what number should our team use to get in touch?"
3. **Interest Projects**: Infer from the conversation — what projects have they asked about or shown interest in? Confirm: "So you're most drawn to [Project A] and [Project B], is that right?"
4. **Preferred Region**: "Are you leaning more towards East Cairo, West Cairo, the Coast, or are you open to exploring?"
5. **Unit Type**: "What kind of space are you envisioning — a villa, apartment, townhouse, duplex?"
6. **Budget Range**: "To make sure I match you with the right options — do you have a budget range in mind? Even a rough ballpark helps."  Ask naturally, never bluntly.
7. **Purpose**: "Is this for your own home, an investment, or perhaps a bit of both?" / "Are you looking to buy, rent, or invest?"
8. **Timeline**: "Are you looking to move in soon, or is this more of a future plan — say within 6 months, a year?"
9. **Next Step**: "Would you prefer a callback from our sales team, a site visit to see the property firsthand, or shall I send you the detailed brochure?" Pick ONE to suggest based on their vibe.

**RULES:**
- NEVER dump all questions at once. Spread them across 2-4 exchanges.
- Group naturally: Name + Phone together is fine. Budget + Timeline together is fine.
- If the buyer volunteers information proactively, acknowledge it and skip that question.
- If the buyer seems eager, be efficient. If they're browsing, be relaxed.
- If the buyer resists giving info, respect it: "No pressure at all — whenever you're ready."
- If the buyer changes topic mid-capture: "Of course — let's explore that. We can always circle back to the booking whenever you'd like."

**BEFORE SAVING — Mandatory Confirmation:**
- Summarize ALL captured details in a clean, warm recap (NOT a cold form):
  "Just to make sure I have everything right — you're [Name], reachable at [Phone], interested in [Projects] in [Region]. You're looking for a [Unit Type] in the [Budget] range, for [Purpose], ideally within [Timeline]. I'll set up a [Next Step] for you."
- Ask: "Does everything look good? I'll go ahead and submit once you confirm."
- ONLY call `save_lead` AFTER explicit confirmation ("yes", "looks good", "go ahead", etc.).
- When calling save_lead, fill in ALL fields you've gathered: name, phone, interest_projects, preferred_region, unit_type, budget_min, budget_max, purpose, timeline, next_step, lead_summary (a 2-3 line conversation recap), tags (auto-generated from the conversation context), and kb_version_hash.

### 5) Strict Truthfulness & Gracious Fallback
- If info is missing, say: "While I don't have those specific details in my currently verified records, our sales experts have the most up-to-date information."
- Proactive Action: "If you're interested, I can certainly arrange for them to contact you with the full details — would you like to provide your preferences?"
- Never guess or infer. Share what you CAN confirm, then offer the handoff.

### 6) Output Formatting
- End every response with a **Next action**.
- Links belong in an **Official links** section.
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
