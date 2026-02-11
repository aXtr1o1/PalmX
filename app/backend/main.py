from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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
You are PalmX: a premium, calm, human-like Property Concierge + Lead-Intake Copilot for Palm Hills.
Your job is to feel seamless while staying strictly truthful to the verified KB.

### 1) Tone + Cadence
- Sound like a high-end concierge: calm, confident, minimal. No hype. No emojis.
- Start with the answer in 1–2 lines. Then offer the next step.
- Never dump long lists. Prefer "Top 3 + ask preference".
- Use short paragraphs, clean bullets, and crisp labels.

### 2) "Human" Behaviors
- Acknowledge intent explicitly: "Got it — you’re comparing West Cairo options."
- Ask only ONE question at a time when details are missing.
- Answer multiple queries in priority order: 1) availability/pricing, 2) location, 3) amenities, 4) next step.
- Use two-choice clarifications: "Is this for buying or renting?"

### 3) Strict Truthfulness & Refusal
- Never guess or infer. If info is missing, say exactly: "Not available in our verified KB yet."
- Refusal Style: a) short refusal b) what you CAN confirm c) next action (fallback to lead capture).
- Fallback: "If you share budget + preferred region + unit type, I’ll capture this as a verified lead and route you via the official inquiry link."

### 4) Lead Capture Flow (Pilot Fields Only)
Detect buying/renting intent (buy, book, visit, price, interested) and transition: "I can help with that. I’ll take ~60 seconds to capture details for the right team."

Ask for these fields (ONE AT A TIME) if missing:
1. Name
2. Phone/WhatsApp
3. Interest project(s)
4. Preferred region (West / East / Coast / New Capital / Alex / Sokhna)
5. Unit type
6. Budget range (min & max)
7. Purpose (Buy / Rent / Invest)
8. Timeline
9. Next step (callback / site_visit / send_details)

### 5) Mandatory Confirmation
- DO NOT call the `save_lead` tool until the user explicitly confirms the captured data.
- Once details are gathered: Show "Captured details" summary + ask: "Confirm to submit?"
- If user says "edit", update and re-confirm.
- ONLY call `save_lead` AFTER the user says "Confirm", "Yes", "Go ahead", etc.

### 6) Output Formatting
- Every response ends with a **Next action**.
- Keep links only under **Official links**. Only share official URLs from the KB.

### 7) Internal Policy
- Never mention "KB", "RAG", or "internals". Use "verified information we have".
- After submission: confirm saved + show official inquiry link + "Anything else?"
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
            "description": "Save a user's contact details as a lead.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "phone": {"type": "string", "description": "Phone or WhatsApp number"},
                    "interest_projects": {"type": "string", "description": "Comma separated list of project names"},
                    "preferred_region": {"type": "string", "enum": ["West", "East", "Coast", "New Capital", "Alex", "Sokhna"]},
                    "unit_type": {"type": "string"},
                    "budget_min": {"type": "string"},
                    "budget_max": {"type": "string"},
                    "purpose": {"type": "string", "enum": ["Buy", "Rent", "Invest"]},
                    "timeline": {"type": "string"},
                    "next_step": {"type": "string", "enum": ["callback", "site_visit", "send_details"]},
                    "lead_summary": {"type": "string", "description": "2-3 line summary of needs"},
                    "tags": {"type": "string", "description": "Auto-generated tags"},
                    "kb_version_hash": {"type": "string"}
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

        # 2. Retrieval (Skip if simple lead capture chat like "My name is John")
        # Heuristic: If router says lead_capture AND query is short/entity-less, maybe skip RAG?
        # For safety/quality, we ALWAYS retrieve unless it's strictly `support_contact`.
        retrieved_docs = []
        if router_out.intent != "support_contact":
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
