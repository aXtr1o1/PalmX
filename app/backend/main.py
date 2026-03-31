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


def _safe_stage(val: Any, fallback: str) -> str:
    if isinstance(val, str):
        v = val.strip()
        return v if v else fallback
    return fallback


def _save_lead_from_args(session_id: str, args: dict[str, Any]) -> bool:
    """Build and persist lead from tool-call style arguments."""
    lead = Lead(
        session_id=session_id,
        name=args.get("name"),
        phone=args.get("phone"),
        interest_projects=args.get("interest_projects", "").split(",") if args.get("interest_projects") else [],
        preferred_region=args.get("preferred_region"),
        unit_type=args.get("unit_type"),
        budget_min=args.get("budget_min"),
        budget_max=args.get("budget_max"),
        purpose=args.get("purpose"),
        timeline=args.get("timeline"),
        next_step=args.get("next_step"),
        lead_summary=args.get("lead_summary"),
        tags=args.get("tags", "").split(",") if args.get("tags") else [],
        kb_version_hash=args.get("kb_version_hash", "v1.0"),
    )
    saved = leads_service.save_lead(lead)
    logger.info("Lead save attempted for session=%s saved=%s name=%s", session_id, saved, lead.name)
    return saved

def _log_persona(session_id: str, cfg: ChatResponse, source: str) -> None:
    """
    Log persona state transitions for easier debugging and audit.
    """
    logger.info(
        "[Persona] source=%s session_id=%s mode=%s persona_state=%s persona_stage=%s support_stage=%s",
        source,
        session_id,
        cfg.mode,
        cfg.persona_state,
        cfg.persona_stage,
        cfg.support_stage,
    )

def _decide_persona_via_model(
    session_id: str,
    intent: str,
    user_message: str,
    history: List[Message],
    current_cfg: ChatResponse,
) -> Optional[ChatResponse]:
    """
    Fallback persona selector: asks model for persona JSON explicitly.
    Used when stream marker-based persona extraction does not appear.
    """
    history_text = "\n".join([f"{m.role}: {m.content}" for m in history[-12:]])
    prompt = f"""
    You are an intelligent Persona-State Selector for PalmX.

Your job is to analyze the conversation context and select the MOST appropriate persona configuration.

You must return STRICT JSON ONLY with:

  "mode": "concierge | lead_capture | support",
  "persona_state": "primary | secondary | support",
  "persona_stage": "discovery | qualification | recommendation | exploration | objection | intent_escalation | cta | confirmation | handoff | fallback",
  "support_stage": "faq | comparison | detail_drilldown | shortlist_refinement | re_engagement"


-------------------------
PERSONA DEFINITIONS
-------------------------

PRIMARY PERSONA (Default user journey flow)
Use when the user is progressing toward a decision.

- discovery → User intent is unclear; ask ONE sharp question to clarify. (For the first 3 conversation, use this stage only if the user doesnot specify their intent or request.)
- qualification → Collect key details (budget, preferences, constraints).
- recommendation → Suggest best-fit options based on known inputs.
- exploration → Show alternatives when user is browsing or unsure.
- objection → Handle doubts, hesitations, or blockers.
- intent_escalation → Strong buying signals (ready, interested, serious).
- cta → Push user toward action (book, sign up, proceed).
- confirmation → Confirm selections, details, or decisions.
- handoff → Transfer to human agent or external process.
- fallback → Handle unknown, vague, or unsupported queries safely.

SECONDARY PERSONA (User-type signals)
Use ONLY when explicitly indicated.

- investor → Focus on ROI, returns, pricing value.
- end_user → Personal usage intent.
- overseas → User is remote or international.
- urgency → Immediate need or time pressure.
- personalization → Wants highly tailored/custom responses.

SUPPORT PERSONA (Information assistance mode)
Use when user is NOT progressing toward conversion but seeking info.

- faq → Direct factual question.
- comparison → Comparing multiple options.
- detail_drilldown → Deep dive into one option.
- shortlist_refinement → Narrowing choices.
- re_engagement → Revive inactive or disengaged user.

-------------------------
DECISION RULES
-------------------------

1. Default to PRIMARY persona unless clear signals suggest otherwise.
2. Use SECONDARY persona_state ONLY if a strong user trait is detected.
3. Use SUPPORT mode ONLY if the user is asking informational or comparison queries.
4. Always choose the MOST ADVANCED logical stage in the journey.
5. If intent is unclear → use discovery.
6. If user shows buying intent → prioritize intent_escalation or cta.
7. If conversation breaks or is invalid → fallback.
8. Never leave any field empty; always return valid non-empty strings for every field.

-------------------------
INPUTS
-------------------------

Current backend intent: {intent}

Current persona:
- mode: {current_cfg.mode}
- persona_state: {current_cfg.persona_state}
- persona_stage: {current_cfg.persona_stage}
- support_stage: {current_cfg.support_stage}

Conversation history:
{history_text}

Latest user message:
{user_message}

-------------------------
OUTPUT FORMAT (STRICT)
-------------------------

Return ONLY valid JSON. No explanation. No text outside JSON.
"""
    try:
        response = llm_service.client.chat.completions.create(
            model=llm_service.deployment,
            messages=[
                {"role": "system", "content": "Return only valid JSON object. No prose."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content)
        model_persona = ChatResponse(
            message="",
            retrieved_projects=[],
            mode=_safe_stage(data.get("mode"), current_cfg.mode),
            persona_state=_safe_stage(data.get("persona_state"), current_cfg.persona_state),
            persona_stage=_safe_stage(data.get("persona_stage"), current_cfg.persona_stage),
            support_stage=_safe_stage(data.get("support_stage"), current_cfg.support_stage),
        )
        _get_persona_for_session(session_id, intent, model_persona=model_persona)
        return model_persona
    except Exception as e:
        logger.error(f"Persona fallback model decision failed: {e}")
        return None

def _default_persona() -> ChatResponse:
    """
    Create a neutral initial persona configuration.
    Persona stage/state should be selected by `_decide_persona_via_model`.
    """
    return ChatResponse(
        message="",
        retrieved_projects=[],
        mode="concierge",
        persona_state="primary",
        persona_stage="discovery",
        support_stage="faq",
    )


def _get_persona_for_session(
    session_id: str,
    intent: str,
    model_persona: Optional[ChatResponse] = None,
    user_message: str = "",
) -> ChatResponse:
    """
    Return the persona configuration for this session, initializing on first contact.
    """
    if session_id not in _PERSONA_BY_SESSION:
        _PERSONA_BY_SESSION[session_id] = _default_persona()
        _log_persona(session_id, _PERSONA_BY_SESSION[session_id], "init_neutral")
        return _PERSONA_BY_SESSION[session_id]

    cfg = _PERSONA_BY_SESSION[session_id]

    # After the initial persona is chosen, backend must NOT decide persona_stage/mode.
    # The model decides those via its output; we only apply the model's values here.
    if model_persona is not None:
        if model_persona.mode:
            cfg.mode = model_persona.mode
        if model_persona.persona_state:
            cfg.persona_state = model_persona.persona_state
        if model_persona.persona_stage:
            cfg.persona_stage = model_persona.persona_stage
        if model_persona.support_stage:
            cfg.support_stage = model_persona.support_stage

        _PERSONA_BY_SESSION[session_id] = cfg
        _log_persona(session_id, cfg, "model_update")

    return cfg

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure RAG index is loaded once at application startup
    logger.info("Application startup: Ensuring RAG index is loaded...")
    try:
        rag_service._load_index()

        if not rag_service.is_ready:
            logger.warning("RAG index is not ready after loading attempt.")
            rag_service.build_index_if_needed()
            rag_service._load_index()


        if not rag_service.is_ready:
            rag_service._load_index()
            logger.info(f"RAG service didnt load properly")
        
        if rag_service.is_ready:
            logger.info("RAG index is ready.")
            
    except Exception as e:
        logger.error(f"Error during RAG index loading: {e}")

    yield
    # Shutdown (if needed)
    logger.info("Application shutdown")

app = FastAPI(title="PalmX Pilot API", version="1.0.0", lifespan=lifespan, )

# Mount admin routes.
# Provide compatibility for both URL styles:
# - `/admin/*` for clients that don't include the `/api` segment
# - `/api/admin/*` for clients that do
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
            
        # Persona is selected by the model before building the answer prompt.
        current_cfg = _get_persona_for_session(session_id, router_out.intent, user_message=user_msg)
        decided_persona = _decide_persona_via_model(
            session_id=session_id,
            intent=router_out.intent,
            user_message=user_msg,
            history=history,
            current_cfg=current_cfg,
        )
        logger.info(f"Decided persona: {decided_persona}")
        logger.info(f"Current persona: {current_cfg}")

        persona_cfg = decided_persona or current_cfg
        full_system_msg  = build_system_prompt(user_msg, history, persona_cfg) + f"\n\nCONTEXT:\n{context_text}"
        
        # 4. Answer Generation
        response_data = llm_service.answer_completion(
            full_system_msg, 
            request.messages,
            tools=TOOLS
        )
        response_json = None
        try:
            response_json = json.loads(response_data)
            persona_cfg.mode = _safe_stage(response_json.get("mode"), persona_cfg.mode)
            persona_cfg.persona_state = _safe_stage(response_json.get("persona_state"), persona_cfg.persona_state)
            persona_cfg.persona_stage = _safe_stage(response_json.get("persona_stage"), persona_cfg.persona_stage)
            persona_cfg.support_stage = _safe_stage(response_json.get("support_stage"), persona_cfg.support_stage)
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
                    _save_lead_from_args(session_id, args)
                    final_text = f"Thank you {args.get('name')}. Your details have been saved. A sales representative will contact you at {args.get('phone')} shortly."
        # Fallback: some models return `tool_calls` inside JSON payload instead of native tool_calls.
        elif isinstance(response_json, dict) and isinstance(response_json.get("tool_calls"), list):
            for tc in response_json.get("tool_calls", []):
                fn = tc.get("tool") or tc.get("name") or tc.get("function", {}).get("name")
                if fn != "save_lead":
                    continue
                raw_args = tc.get("args") or tc.get("arguments") or tc.get("function", {}).get("arguments") or {}
                if isinstance(raw_args, str):
                    try:
                        raw_args = json.loads(raw_args)
                    except Exception:
                        raw_args = {}
                if isinstance(raw_args, dict):
                    _save_lead_from_args(session_id, raw_args)
                    final_text = f"Thank you {raw_args.get('name')}. Your details have been saved. A sales representative will contact you at {raw_args.get('phone')} shortly."
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
        persona_cfg = _get_persona_for_session(
            session_id,
            router_out.intent,
            model_persona=persona_cfg,
            user_message=user_msg,
        )
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
            logger.info(f"the results are printed{results}")
            retrieved_docs = [r['project'] for r in results]

        # 3. Context
        context_text = ""
        for p in retrieved_docs:
            context_text += f"---\n{kb_service.build_project_card(p)}\n"
        
        # Persona is selected by the model before building the streaming prompt.
        current_cfg = _get_persona_for_session(
            session_id,
            router_out.intent,
            model_persona=None,
            user_message=user_msg,
        )
        decided_persona = _decide_persona_via_model(
            session_id=session_id,
            intent=router_out.intent,
            user_message=user_msg,
            history=history,
            current_cfg=current_cfg,
        )
        logger.info(f"Decided persona: {decided_persona}")
        logger.info(f"Current persona: {current_cfg}")
        
        logger.info(f"User message: {user_msg}")
        logger.info(f"History: {history}")
        logger.info(f"Router out: {router_out}")
        logger.info(f"Retrieved docs: {retrieved_docs}")
        logger.info(f"Context text: {context_text}")
        
        persona_cfg = decided_persona or current_cfg
        full_system_msg = build_system_prompt(user_msg, history, persona_cfg) + f"\n\nCONTEXT:\n{context_text}"
        full_system_msg += (
            "\n\nSTREAM_OUTPUT_RULES (STRICT):\n"
            "- First, output __PERSONA_JSON__ then a SINGLE valid JSON object then __END_PERSONA_JSON__.\n"
            "- JSON keys must include: mode, persona_state, persona_stage, support_stage.\n"
            "- After __END_PERSONA_JSON__, output ONLY the user-visible assistant message text.\n"
        )

        # Persist persona configuration for the next turn.
        

        # 4. Stream tokens
        def generate():
            pending = ""
            persona_extracted = False
            persona_start_marker = "__PERSONA_JSON__"
            persona_end_marker = "__END_PERSONA_JSON__"

            for chunk in llm_service.stream_answer_completion(
                full_system_msg, request.messages, tools=TOOLS
            ):
                if "__TOOL_CALLS__" in chunk:
                    tc_json = chunk.split("__TOOL_CALLS__")[1]
                    tool_calls = json.loads(tc_json)
                    for tc in tool_calls:
                        if tc["function"]["name"] == "save_lead":
                            args = json.loads(tc["function"]["arguments"])
                            _save_lead_from_args(session_id, args)
                            confirm_msg = f"Thank you {args.get('name')}. Your details have been saved. A sales representative will contact you at {args.get('phone')} shortly."
                            yield f"data: {json.dumps({'token': confirm_msg})}\n\n"
                    continue

                if persona_extracted:
                    yield f"data: {json.dumps({'token': chunk})}\n\n"
                    continue

                pending += chunk
                # logger.info(f"Pending: {pending}")
                # Failsafe: if the model never emits the persona marker, don't block the stream forever.
                if len(pending) > 5000 and persona_start_marker not in pending:
                    persona_extracted = True
                    yield f"data: {json.dumps({'token': pending})}\n\n"
                    pending = ""
                    continue

                start_idx = pending.find(persona_start_marker)
                if start_idx == -1:
                    continue

                end_idx = pending.find(persona_end_marker, start_idx + len(persona_start_marker))
                if end_idx == -1:
                    continue

                json_str = pending[start_idx + len(persona_start_marker): end_idx]
                remainder = pending[end_idx + len(persona_end_marker):]
                pending = ""

                try:
                    persona_data = json.loads(json_str)
                    logger.info(f"Persona data: {persona_data}")
                    if isinstance(persona_data, dict):
                        model_persona = ChatResponse(
                            message="",
                            retrieved_projects=[],
                            mode=_safe_stage(persona_data.get("mode"), persona_cfg.mode),
                            persona_state=_safe_stage(persona_data.get("persona_state"), persona_cfg.persona_state),
                            persona_stage=_safe_stage(persona_data.get("persona_stage"), persona_cfg.persona_stage),
                            support_stage=_safe_stage(persona_data.get("support_stage"), persona_cfg.support_stage),
                        )
                        _get_persona_for_session(session_id, router_out.intent, model_persona=model_persona)
                        persona_extracted = True
                except Exception as e:
                    logger.error(f"Error parsing persona json in stream: {e}")

                # If extraction succeeded, remainder is the user-visible message.
                # If extraction failed, fall back to emitting remainder so the user still sees something.
                if remainder:
                    yield f"data: {json.dumps({'token': remainder})}\n\n"

            if not persona_extracted and pending:
                yield f"data: {json.dumps({'token': pending})}\n\n"

            # Guaranteed persona update path:
            # if marker extraction did not happen, force a model persona decision.
            if not persona_extracted:
                _decide_persona_via_model(
                    session_id=session_id,
                    intent=router_out.intent,
                    user_message=user_msg,
                    history=history,
                    current_cfg=persona_cfg,
                )

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
