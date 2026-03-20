from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
import logging
import os
from datetime import datetime

from app.backend.config import Config
from app.backend.models import ChatRequest, ChatResponse, Lead, Message
from app.backend.services.llm_service import llm_service
from app.backend.services.rag_service import rag_service
from app.backend.services.leads_service import leads_service
from app.backend.services.kb_service import kb_service
from app.backend.routes.admin_routes import router as admin_router
from app.backend.services.persona_llm import build_system_prompt
# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PalmX-API")

# ---------------------------------------------------------------------------
# Persona persistence (backend-only)
# ---------------------------------------------------------------------------
# The frontend currently sends only `{session_id, messages, locale}`.
# To keep persona_state/persona_stage/support_stage consistent across turns
# without touching frontend code, we store the persona configuration per session_id.
_PERSONA_BY_SESSION: dict[str, ChatResponse] = {}


def _default_persona_for_intent(intent: str) -> ChatResponse:
    """
    Create a safe default persona configuration for a new session.
    """
    mode = "concierge"
    persona_state = "primary"
    persona_stage = "exploration"
    support_stage = "faq"

    if intent == "lead_capture":
        mode = "lead_capture"
        persona_state = "primary"
        persona_stage = "qualification"
        support_stage = "faq"
    elif intent == "support_contact":
        mode = "support"
        persona_state = "support"
        persona_stage = "qualification"
        support_stage = "faq"
    elif intent in ("pricing", "compare", "amenity_check"):
        persona_state = "primary"
        persona_stage = "recommendation"
        mode = "concierge"
    else:
        # project_query, list_projects, etc.
        persona_state = "primary"
        persona_stage = "exploration"
        mode = "concierge"

    # message/retrieved_projects are not used by build_system_prompt(); keep minimal.
    return ChatResponse(
        message="",
        retrieved_projects=[],
        mode=mode,
        persona_state=persona_state,
        persona_stage=persona_stage,
        support_stage=support_stage,
    )


def _get_persona_for_session(session_id: str, intent: str, model_persona: Optional[ChatResponse] = None) -> ChatResponse:
    """
    Return the persona configuration for this session, initializing on first contact.
    """
    
    if session_id not in _PERSONA_BY_SESSION:
        _PERSONA_BY_SESSION[session_id] = _default_persona_for_intent(intent)
        return _PERSONA_BY_SESSION[session_id]

    cfg = _PERSONA_BY_SESSION[session_id]
    

    # Keep previous persona values (history-like behavior), but align with critical intent modes.
    if intent == "support_contact":
        cfg.mode = "support"
        cfg.persona_state = "support"
        cfg.persona_stage = "qualification"
        cfg.support_stage = "faq"
    elif intent == "lead_capture":
        cfg.mode = "lead_capture"
        cfg.persona_state = "primary"
        cfg.persona_stage = "qualification"
        cfg.support_stage = "faq"
    else:
        cfg.mode = "concierge"
        if cfg.persona_state == "support":
            cfg.persona_state = "primary"
            cfg.persona_stage = "exploration"
            cfg.support_stage = "faq"

    if intent in ("pricing", "compare", "amenity_check") and cfg.persona_state == "primary":
        cfg.persona_stage = "recommendation"
    if model_persona:
        cfg.mode = model_persona.mode
        cfg.persona_state = model_persona.persona_state
        cfg.persona_stage = model_persona.persona_stage
        cfg.support_stage = model_persona.support_stage

    print(f"Persona configuration: {cfg}")
    _PERSONA_BY_SESSION[session_id] = cfg
    return cfg

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure RAG index is loaded once at application startup
    logger.info("Application startup: Ensuring RAG index is loaded...")
    if not rag_service.is_ready:
        rag_service._load_index()
    logger.info(f"RAG service ready: {rag_service.is_ready}")
    yield
    # Shutdown (if needed)
    logger.info("Application shutdown")

app = FastAPI(title="PalmX Pilot API", version="1.0.0", lifespan=lifespan)

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
        
        # 1. Router
        history = request.messages[:-1]
        router_out = llm_service.router_completion(user_msg, history=history)
        logger.info(f"Router intent: {router_out.intent} | Filters: {router_out.filters}")

        # 2. Retrieval
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
            
        persona_cfg = _get_persona_for_session(session_id, router_out.intent)
        full_system_msg  = build_system_prompt(user_msg, history, persona_cfg) + f"\n\nCONTEXT:\n{context_text}"
        
        # 4. Answer Generation
        response_data = llm_service.answer_completion(
            full_system_msg, 
            request.messages,
            tools=TOOLS
        )
        try:
            response_json = json.loads(response_data)
            persona_cfg.mode = response_json.get("mode", persona_cfg.mode)
            persona_cfg.persona_state = response_json.get("persona_state", persona_cfg.persona_state)
            persona_cfg.persona_stage = response_json.get("persona_stage", persona_cfg.persona_stage)
            persona_cfg.support_stage = response_json.get("support_stage", persona_cfg.support_stage)
            retrieved_projects = response_json.get("retrieved_projects", [])
            message = response_json.get("message", "")
            
            _PERSONA_BY_SESSION[session_id] = persona_cfg
        except Exception:
            # fallback if model returns plain text
            message = response_data 
            retrieved_projects = []
        
        final_text = ""
        
        # 5. Handle Tool Calls
        if isinstance(response_data, list):
            for tool_call in response_data:
                if tool_call.function.name == "save_lead":
                    args = json.loads(tool_call.function.arguments)
                    logger.info(f"Tool Call 'save_lead' Args: {args}")
                    
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
        
        # Persist persona configuration for the next turn.
        persona_cfg = _get_persona_for_session(session_id, router_out.intent, model_persona=persona_cfg)
        _PERSONA_BY_SESSION[session_id] = persona_cfg

        return ChatResponse(
            message=final_text,
            retrieved_projects=[p.project_name for p in retrieved_docs],
            mode=persona_cfg.mode,
            persona_state=persona_cfg.persona_state,
            persona_stage=persona_cfg.persona_stage,
            support_stage=persona_cfg.support_stage,
        )


    except Exception as e:
        logger.error(f"Chat error: {e}")
        return ChatResponse(
            message="I apologize, but I'm encountering a temporary issue. Please try again.",
            retrieved_projects=[],
            mode="concierge"
        )

@app.post("/api/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    try:
        user_msg = request.messages[-1].content
        session_id = request.session_id
        
        # 1. Router
        history = request.messages[:-1]
        router_out = llm_service.router_completion(user_msg, history=history)
        logger.info(f"[Stream] Router intent: {router_out.intent}")

        # 2. Retrieval
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
        
        current_date = datetime.now().strftime("%B %d, %Y")
        persona_cfg = _get_persona_for_session(session_id, router_out.intent, model_persona=None)
        full_system_msg = build_system_prompt(user_msg, history, persona_cfg) + f"\n\nCONTEXT:\n{context_text}"

        # Persist persona configuration for the next turn.
        

        # 4. Stream tokens
        def generate():
            full_response = ""
            for chunk in llm_service.stream_answer_completion(
                full_system_msg, request.messages, tools=TOOLS
            ):
                if "__PERSONA_JSON__" in chunk:
                    try:
                        persona_json = chunk.split("__PERSONA_JSON__")[1]
                        persona_data = json.loads(persona_json)

                        model_persona = ChatResponse(
                            message="",
                            retrieved_projects=[],
                            mode=persona_data.get("mode", persona_cfg.mode),
                            persona_state=persona_data.get("persona_state", persona_cfg.persona_state),
                            persona_stage=persona_data.get("persona_stage", persona_cfg.persona_stage),
                            support_stage=persona_data.get("support_stage", persona_cfg.support_stage)
                        )
                        persona_cfg=_get_persona_for_session(session_id, router_out.intent, model_persona=model_persona)
                        _PERSONA_BY_SESSION[session_id] = persona_cfg
                    except Exception as e:
                        logger.error(f"Error parsing persona JSON: {e}")
                    continue
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

            yield f"data: {json.dumps({'done': True, 'retrieved_projects': [p.project_name for p in retrieved_docs]})}\n\n"
            
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

@app.get("/admin/leads-legacy")
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
