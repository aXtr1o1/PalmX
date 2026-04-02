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
import re
# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PalmX-API")
HOTLINE_NUMBER = Config.HOTLINE_NUMBER
# ---------------------------------------------------------------------------
# Persona persistence (backend-only)
# ---------------------------------------------------------------------------
_PERSONA_BY_SESSION: dict[str, ChatResponse] = {}
_DOCS_BY_SESSION: dict[str, list] = {}  # Cache last non-empty retrieved_docs per session


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
    logger.info(
        "[Persona] source=%s session_id=%s mode=%s persona_state=%s persona_stage=%s support_stage=%s",
        source,
        session_id,
        cfg.mode,
        cfg.persona_state,
        cfg.persona_stage,
        cfg.support_stage,
    )

def _normalize_phone_for_links(phone: Optional[str]) -> Optional[str]:
    if not phone or not isinstance(phone, str):
        return None
    raw = phone.strip()
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return None
    if digits.startswith("01") and len(digits) == 11:
        return "20" + digits[1:]
    return digits

def _build_contact_cta_card(phone: Optional[str]) -> Optional[dict[str, Any]]:
    normalized = _normalize_phone_for_links(phone)
    if not normalized:
        return None

    portal_url = "https://www.palmhillsdevelopments.com/en-us/interestedIn"
    whatsapp_url = f"https://wa.me/{normalized}"

    return {
        "title": "Continue on WhatsApp",
        "cta": "Continue on WhatsApp",
        "actions": [
            {"label": "WhatsApp", "type": "link", "url": whatsapp_url},
            {"label": "Open Portal", "type": "link", "url": portal_url},
        ],
    }

# ---------------------------------------------------------------------------
# NEW: Build project_cards payload from retrieved docs
# ---------------------------------------------------------------------------
def _build_project_cards(projects: list) -> list[dict[str, Any]]:
    """
    Convert up to 3 Project objects into frontend-ready card dicts.
    Only called when persona_stage == 'recommendation'.
    """
    cards = []
    for p in projects[:3]:
        price_label = None
        if p.starting_price_value:
            val = p.starting_price_value
            if val >= 1_000_000:
                price_label = f"From {val / 1_000_000:.1f}M EGP"
            else:
                price_label = f"From {val:,} EGP"
        elif p.price_status:
            price_label = p.price_status

        location_parts = [x for x in [p.city_area, p.region] if x]
        location_label = " · ".join(location_parts) if location_parts else None

        cards.append({
            "id": p.project_id,
            "title": p.project_name,
            "price": price_label,
            "location": location_label,
            "type": p.project_type,
            "status": p.project_status,
            "amenities": p.key_amenities[:3] if p.key_amenities else [],
            "url": p.official_project_url or None,
        })
    return cards


def _decide_persona_via_model(
    session_id: str,
    intent: str,
    user_message: str,
    history: List[Message],
    current_cfg: ChatResponse,
) -> Optional[ChatResponse]:
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
    if session_id not in _PERSONA_BY_SESSION:
        _PERSONA_BY_SESSION[session_id] = _default_persona()
        _log_persona(session_id, _PERSONA_BY_SESSION[session_id], "init_neutral")
        return _PERSONA_BY_SESSION[session_id]

    cfg = _PERSONA_BY_SESSION[session_id]

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
    logger.info("Application shutdown")

app = FastAPI(title="PalmX Pilot API", version="1.0.0", lifespan=lifespan, root_path="/api")

app.include_router(admin_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
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

# ... (Imports and helper functions remain the same) ...

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        user_msg = request.messages[-1].content
        session_id = request.session_id
        
        history = request.messages[:-1]
        router_out = llm_service.router_completion(user_msg, history=history)

        retrieved_docs = []
        if router_out.intent not in ("support_contact", "lead_capture"):
            results = rag_service.search(router_out.query_rewrite, k=3, filters=router_out.filters)
            retrieved_docs = [r['project'] for r in results]

        context_text = ""
        for p in retrieved_docs:
            context_text += f"---\n{kb_service.build_project_card(p)}\n"
            
        current_cfg = _get_persona_for_session(session_id, router_out.intent, user_message=user_msg)
        decided_persona = _decide_persona_via_model(
            session_id=session_id,
            intent=router_out.intent,
            user_message=user_msg,
            history=history,
            current_cfg=current_cfg,
        )

        persona_cfg = decided_persona or current_cfg
        
        # --- LOGIC FOR RECOMMENDATION STAGE ---
        RECOMMENDATION_STAGES = {"recommendation", "shortlist"}
        project_cards = None
        trim_intro = False

        if persona_cfg.persona_stage in RECOMMENDATION_STAGES and retrieved_docs:
            project_cards = _build_project_cards(retrieved_docs)
            trim_intro = True
        # --------------------------------------

        full_system_msg = build_system_prompt(user_msg, history, persona_cfg) + f"\n\nCONTEXT:\n{context_text}"
        
        response_data = llm_service.answer_completion(full_system_msg, request.messages, tools=TOOLS)
        
        # ... (Remaining JSON parsing and Tool Call logic stays as is) ...

        return ChatResponse(
            message=final_text,
            retrieved_projects=[p.project_name for p in retrieved_docs],
            project_cards=project_cards, # Send the cards
            trim_intro=trim_intro,       # Signal the intro trim
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

# ... (Rest of main.py) ...

@app.post("/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    try:
        user_msg = request.messages[-1].content
        session_id = request.session_id
        
        history = request.messages[:-1]
        router_out = llm_service.router_completion(user_msg, history=history)
        logger.info(f"[Stream] Router intent: {router_out.intent}")

        retrieved_docs = []
        if router_out.intent not in ("support_contact", "lead_capture"):
            results = rag_service.search(router_out.query_rewrite, k=3, filters=router_out.filters)
            logger.info(f"the results are printed{results}")
            retrieved_docs = [r['project'] for r in results]

        # If RAG returned nothing, retry with a broader query (no filters)
        # This is the most common reason cards don't show — the query was too specific
        if not retrieved_docs and router_out.intent not in ("support_contact", "lead_capture"):
            logger.info(f"[RAG] No results for '{router_out.query_rewrite}' — retrying broad search")
            broad_results = rag_service.search(router_out.query_rewrite, k=3, filters={})
            if broad_results:
                retrieved_docs = [r['project'] for r in broad_results]
                logger.info(f"[RAG] Broad search found {len(retrieved_docs)} docs")
            else:
                # Last resort: search using raw user message
                fallback_results = rag_service.search(user_msg, k=3, filters={})
                if fallback_results:
                    retrieved_docs = [r['project'] for r in fallback_results]
                    logger.info(f"[RAG] Fallback search found {len(retrieved_docs)} docs")

        # If still empty, reuse the last known docs for this session
        if not retrieved_docs and session_id in _DOCS_BY_SESSION:
            retrieved_docs = _DOCS_BY_SESSION[session_id]
            logger.info(f"[RAG] Reusing cached docs for session={session_id}: {[p.project_name for p in retrieved_docs]}")

        # Cache non-empty docs for future turns
        if retrieved_docs:
            _DOCS_BY_SESSION[session_id] = retrieved_docs

        context_text = ""
        for p in retrieved_docs:
            context_text += f"---\n{kb_service.build_project_card(p)}\n"
        
        current_cfg = _get_persona_for_session(
            session_id, router_out.intent, model_persona=None, user_message=user_msg,
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
        
        persona_cfg = decided_persona or current_cfg
        full_system_msg = build_system_prompt(user_msg, history, persona_cfg) + f"\n\nCONTEXT:\n{context_text}"
        full_system_msg += (
            "\n\nSTREAM_OUTPUT_RULES (STRICT):\n"
            "- First, output __PERSONA_JSON__ then a SINGLE valid JSON object then __END_PERSONA_JSON__.\n"
            "- JSON keys must include: mode, persona_state, persona_stage, support_stage.\n"
            "- After __END_PERSONA_JSON__, output ONLY the user-visible assistant message text.\n"
        )

        def generate():
            pending = ""
            persona_extracted = False
            persona_start_marker = "__PERSONA_JSON__"
            persona_end_marker = "__END_PERSONA_JSON__"

            done_cta_card: Optional[dict[str, Any]] = None
            done_mode: Optional[str] = None
            # Track whether the final persona stage is "recommendation"
            is_recommendation: bool = False

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
                            done_cta_card = _build_contact_cta_card(HOTLINE_NUMBER)
                            done_mode = "lead_capture"
                            yield f"data: {json.dumps({'token': confirm_msg})}\n\n"
                    continue

                if persona_extracted:
                    yield f"data: {json.dumps({'token': chunk})}\n\n"
                    continue

                pending += chunk

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
                        done_mode = model_persona.mode
                        # -------------------------------------------------------
                        # NEW: detect recommendation stage so we can attach cards
                        # -------------------------------------------------------
                        RECOMMENDATION_STAGES = {"recommendation", "shortlist"}
                        is_recommendation = (model_persona.persona_stage in RECOMMENDATION_STAGES)
                except Exception as e:
                    logger.error(f"Error parsing persona json in stream: {e}")

                if remainder:
                    yield f"data: {json.dumps({'token': remainder})}\n\n"

            if not persona_extracted and pending:
                yield f"data: {json.dumps({'token': pending})}\n\n"

            if not persona_extracted:
                decided = _decide_persona_via_model(
                    session_id=session_id,
                    intent=router_out.intent,
                    user_message=user_msg,
                    history=history,
                    current_cfg=persona_cfg,
                )
                if decided is not None:
                    done_mode = decided.mode
                    RECOMMENDATION_STAGES = {"recommendation", "shortlist"}
                    is_recommendation = (decided.persona_stage in RECOMMENDATION_STAGES)

            # -------------------------------------------------------
            # Card trigger — clean two-source logic:
            #
            # Source A: __PERSONA_JSON__ marker inside the stream said recommendation/shortlist
            # Source B: decided_persona (the dedicated pre-stream model call) said recommendation/shortlist
            #
            # decided_persona is the most reliable source — it is a separate
            # structured JSON call made BEFORE the stream starts, so it never
            # gets lost due to streaming/marker parsing issues.
            #
            # Hard block: if decided_persona said qualification or discovery,
            # never show cards — the agent is still collecting preferences.
            # -------------------------------------------------------
            RECOMMENDATION_STAGES = {"recommendation", "shortlist"}
            BLOCKING_STAGES = {"qualification", "discovery"}

            # persona_cfg IS decided_persona (set at line: persona_cfg = decided_persona or current_cfg)
            pre_stream_stage = persona_cfg.persona_stage
            pre_stream_recommends = pre_stream_stage in RECOMMENDATION_STAGES
            is_blocked = pre_stream_stage in BLOCKING_STAGES

            should_show_cards = (
                bool(retrieved_docs)
                and not is_blocked
                and (is_recommendation or pre_stream_recommends)
            )

            logger.info(
                f"[Cards] marker={is_recommendation} pre_stream={pre_stream_stage} "
                f"blocked={is_blocked} docs={len(retrieved_docs)} → show={should_show_cards}"
            )

            # Resolve the final persona stage from the most reliable source:
            # 1. Stream marker parse (is_recommendation + stored session)
            # 2. Pre-stream decided_persona (most reliable)
            # 3. current_cfg fallback
            final_persona = _get_persona_for_session(session_id, router_out.intent)
            final_stage = final_persona.persona_stage

            payload: dict[str, Any] = {
                "done": True,
                "retrieved_projects": [p.project_name for p in retrieved_docs],
                "mode": done_mode or persona_cfg.mode,
                "persona_stage": final_stage,
            }

            if should_show_cards:
                payload["project_cards"] = _build_project_cards(retrieved_docs)
                payload["trim_intro"] = True
                logger.info(f"[Cards] Attaching {len(payload['project_cards'])} cards")
            
            try:
                logger.info(f"Before CTA card building")
                val = _get_persona_for_session(session_id, router_out.intent, model_persona=persona_cfg)
                if router_out.intent in ("support_contact", "handoff") or val.persona_stage in ("handoff", "support_contact"):
                    logger.info(f"Building cta card for {router_out.intent}")
                    payload["cta_card"] = _build_contact_cta_card(HOTLINE_NUMBER)
            except Exception as e:
                if router_out.intent in ("support_contact", "handoff") or persona_cfg.mode in ("handoff", "support_contact"):
                    logger.info(f"Building cta card for {router_out.intent}")
                    payload["cta_card"] = _build_contact_cta_card(HOTLINE_NUMBER)
                else:
                    logger.error(f"Error building cta card: {e}")
                    payload["cta_card"] = None

            if done_cta_card:
                payload["cta_card"] = done_cta_card

            yield f"data: {json.dumps(payload)}\n\n"
            
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