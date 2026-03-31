import json
import re
from dataclasses import dataclass
from typing import Any, Optional

from app.backend.models import Lead
from app.backend.services.kb_service import kb_service


@dataclass(frozen=True)
class ScoreResult:
    classification: str  # HOT | WARM | COLD
    score: int  # 0..100
    reason_codes: list[str]  # 3-6 bullet-like strings
    recommended_action: str
    handoff_summary: str
    primary_project: str
    scorer_version: str = "sop_v1"


def _norm(s: str) -> str:
    s = (s or "").strip().lower()
    # Remove non-alphanumerics to make matching tolerant to spaces/hyphens/underscores.
    return re.sub(r"[^a-z0-9]+", "", s)


def _parse_float_egp(v: Any) -> Optional[float]:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    s = s.replace(",", "").replace("EGP", "").strip()
    try:
        return float(s)
    except Exception:
        m = re.search(r"(\d+(\.\d+)?)", s)
        if not m:
            return None
        try:
            return float(m.group(1))
        except Exception:
            return None


def _parse_timeline_months(timeline: str) -> Optional[tuple[float, float]]:
    """
    Returns (min_months, max_months).
    None means "unknown" or "flexible".
    """
    t = (timeline or "").strip().lower()
    if not t:
        return None
    if "flex" in t or "not sure" in t:
        return None
    if "immediate" in t or "asap" in t:
        return (0.0, 0.0)

    range_m = re.search(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*month[s]?", t)
    if range_m:
        a = float(range_m.group(1))
        b = float(range_m.group(2))
        return (min(a, b), max(a, b))

    single_m = re.search(r"(\d+(?:\.\d+)?)\s*month[s]?", t)
    if single_m:
        a = float(single_m.group(1))
        return (a, a)

    # Some datasets might contain "6-12 months" without "month" exact token.
    # Best-effort fallback:
    range_m2 = re.search(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*mo", t)
    if range_m2:
        a = float(range_m2.group(1))
        b = float(range_m2.group(2))
        return (min(a, b), max(a, b))

    return None


def _timeline_points(timeline: str) -> tuple[int, str]:
    parsed = _parse_timeline_months(timeline)
    if parsed is None:
        return 25, "timeline unknown/flexible (low urgency points)"
    min_m, max_m = parsed
    if max_m <= 3:
        return 100, f"timeline bucket <= 3 months (parsed {min_m:.1f}-{max_m:.1f} months)"
    if max_m <= 6:
        return 70, f"timeline bucket <= 6 months (parsed {min_m:.1f}-{max_m:.1f} months)"
    if max_m <= 12:
        return 40, f"timeline bucket <= 12 months (parsed {min_m:.1f}-{max_m:.1f} months)"
    return 15, f"timeline bucket > 12 months (parsed {min_m:.1f}-{max_m:.1f} months)"


def _intent_points(purpose: str) -> tuple[int, str]:
    p = (purpose or "").strip().lower()
    if not p:
        return 30, "purpose missing/unclear"
    if "invest" in p:
        return 90, "intent is investment"
    if "rent" in p:
        return 60, "intent is rent"
    if "personal" in p or "primary home" in p:
        return 75, "intent is personal use"
    if "buy" in p:
        return 80, "intent is buy"
    return 40, "purpose present but not recognized"


def _contact_points(name: str, phone: str) -> tuple[int, str]:
    has_name = bool((name or "").strip())
    phone_s = (phone or "").strip()
    digits = re.sub(r"[^0-9]", "", phone_s)
    has_phone = bool(phone_s)
    if has_name and has_phone and len(digits) >= 10:
        return 100, "contact provided (name + valid phone)"
    if has_phone and len(digits) >= 8:
        return 70, f"phone present (digits={len(digits)}), name missing/short"
    if has_name:
        return 50, "name present, phone missing/short"
    return 0, "contact missing"


def _engagement_points(next_step: str, tags: list[str]) -> tuple[int, str]:
    ns = (next_step or "").strip().lower()

    if not ns:
        return 30, "next_step missing (default engagement points)"

    if "not interested" in ns or (ns.strip() == "no"):
        return 0, "next_step indicates not interested"

    # Deterministic mapping based on next_step text.
    if "site" in ns or "visit" in ns:
        return 100, "next_step is site visit"
    if "meet" in ns:
        return 90, "next_step is meeting scheduled"
    if "callback" in ns or "call back" in ns or ns == "call back":
        return 85, "next_step is callback"
    if "whatsapp" in ns:
        return 75, "next_step is WhatsApp follow-up"
    if "brochure" in ns:
        return 60, "next_step is send brochure"
    if "details" in ns:
        return 65, "next_step is send details"
    if "information requested" in ns or "info requested" in ns:
        return 60, "next_step requests information"
    if "send" in ns:
        return 60, "next_step indicates a send action"
    return 50, "next_step present but not recognized (medium engagement)"


def _match_projects(interest_projects: list[str]) -> list[dict[str, Any]]:
    """
    Deterministically match lead interest project tokens to KB projects.
    Returns list of {token, project_id, project_name}.
    """
    tokens = [t.strip() for t in (interest_projects or []) if str(t).strip()]
    if not tokens:
        return []

    kb_list: list[dict[str, Any]] = []
    for p in kb_service.projects.values():
        kb_list.append(
            {
                "project_id": p.project_id,
                "project_name": p.project_name,
                "pid_n": _norm(p.project_id),
                "pname_n": _norm(p.project_name),
            }
        )

    out: list[dict[str, Any]] = []
    for tok in tokens:
        tok_n = _norm(tok)
        if not tok_n:
            continue

        best = None
        for item in kb_list:
            pid_n = item["pid_n"]
            pname_n = item["pname_n"]

            if tok_n == pid_n or tok_n == pname_n:
                cand_score = 1000
            else:
                cand_score = 0
                if tok_n and (tok_n in pid_n or tok_n in pname_n):
                    cand_score = 600 + min(len(tok_n), 30)
                elif (pid_n and pid_n in tok_n) or (pname_n and pname_n in tok_n):
                    cand_score = 500 + min(len(tok_n), 30)

            if best is None or cand_score > best["cand_score"] or (
                cand_score == best["cand_score"] and item["project_id"] < best["project_id"]
            ):
                best = {
                    "token": tok,
                    "project_id": item["project_id"],
                    "project_name": item["project_name"],
                    "cand_score": cand_score,
                }

        if best and best["cand_score"] > 0:
            out.append({"token": tok, "project_id": best["project_id"], "project_name": best["project_name"]})

    return out


def _budget_fit_points(lead: Lead) -> tuple[int, str, str]:
    """
    Returns (points_0_100, primary_project_name, detail_str_for_reason).
    """
    lead_bmin = _parse_float_egp(lead.budget_min)
    lead_bmax = _parse_float_egp(lead.budget_max)

    if lead_bmax is None and lead_bmin is None:
        return 20, "—", "budget missing (fallback points)"

    if lead_bmin is not None and lead_bmax is not None and lead_bmin > lead_bmax:
        lead_bmin, lead_bmax = lead_bmax, lead_bmin
    elif lead_bmax is None:
        lead_bmax = lead_bmin

    matches = _match_projects(lead.interest_projects)
    if not matches:
        return 30, "—", "no KB project matches (fallback points)"

    best_points = -1
    best_proj_name = "—"
    best_project_id = ""
    best_detail = ""

    for m in matches:
        p = kb_service.get_project(m["project_id"])
        if not p:
            continue

        raw = p.raw_data or {}
        min_v = _parse_float_egp(raw.get("price_range_min"))
        max_v = _parse_float_egp(raw.get("price_range_max"))

        if min_v is None and max_v is None:
            points = 35
            detail = f"project={p.project_name}: KB price range unknown"
        else:
            if min_v is None:
                min_v = max_v
            if max_v is None:
                max_v = min_v

            if lead_bmin is None:
                lead_bmin = lead_bmax

            overlap = max(0.0, min(lead_bmax, max_v) - max(lead_bmin, min_v))
            if overlap > 0:
                points = 100
                detail = f"project={p.project_name}: budget overlaps KB range"
            else:
                if lead_bmax < min_v:
                    ratio = max(0.0, lead_bmax / min_v)
                    points = int(round(70 * ratio))
                    points = max(0, min(points, 95))
                    detail = f"project={p.project_name}: lead budget below KB min (ratio={ratio:.2f})"
                else:
                    ratio = max_v / max(lead_bmin, 1e-9)
                    if lead_bmax <= 1.5 * max_v:
                        points = 85
                    else:
                        points = int(round(85 * ratio))
                        points = max(0, min(points, 85))
                    detail = f"project={p.project_name}: lead budget above KB max (ratio={ratio:.2f})"

        if points > best_points or (points == best_points and p.project_id < (best_project_id or "")):
            best_points = points
            best_proj_name = p.project_name
            best_project_id = p.project_id
            best_detail = detail

    if best_points < 0:
        return 30, "—", "failed to compute budget fit (fallback)"
    return int(best_points), best_proj_name, best_detail


def score_lead(lead: Lead) -> ScoreResult:
    # Hard negative: not interested.
    ns = (lead.next_step or "").strip().lower()
    if ns in {"not interested", "no"} or "not interested" in ns:
        classification = "COLD"
        return ScoreResult(
            classification=classification,
            score=10,
            reason_codes=[
                "Engagement: next_step indicates not interested",
                "Timeline: evaluated but overridden by disengagement",
                "Contact: name/phone presence used for routing only",
            ],
            recommended_action="Nurture sequence within 48 hours",
            handoff_summary=f"Hi {lead.name}, thanks for your time. If your needs change, feel free to message us again with your preferred project/timeline.",
            primary_project="—",
        )

    # Dimension scoring.
    budget_points, primary_project, budget_detail = _budget_fit_points(lead)
    timeline_points, timeline_detail = _timeline_points(lead.timeline or "")
    intent_points, intent_detail = _intent_points(lead.purpose or "")
    engagement_points, engagement_detail = _engagement_points(lead.next_step or "", lead.tags or [])
    contact_points, contact_detail = _contact_points(lead.name or "", lead.phone or "")

    weights = {"budget": 0.30, "timeline": 0.25, "intent": 0.20, "engagement": 0.15, "contact": 0.10}
    score_float = (
        budget_points * weights["budget"]
        + timeline_points * weights["timeline"]
        + intent_points * weights["intent"]
        + engagement_points * weights["engagement"]
        + contact_points * weights["contact"]
    )
    score = int(round(score_float))
    score = max(0, min(100, score))

    classification = "HOT" if score >= 70 else "WARM" if score >= 40 else "COLD"

    if classification == "HOT":
        recommended_action = "Call within 10 minutes"
    elif classification == "WARM":
        recommended_action = "Follow-up within 6 hours"
    else:
        recommended_action = "Nurture sequence within 48 hours"

    ns = (lead.next_step or "").strip().lower()
    if ("site" in ns or "visit" in ns) and classification != "COLD":
        recommended_action = "Call within 5 minutes (confirm site visit)"

    lead_budget_min = lead.budget_min or "—"
    lead_budget_max = lead.budget_max or "—"
    tl = lead.timeline or "—"
    next_step = lead.next_step or "send details"

    handoff_summary = (
        f"Hi {lead.name}, thanks for reaching out. I noted interest in {primary_project}. "
        f"Your stated intent is {lead.purpose or '—'} with a budget of {lead_budget_min}-{lead_budget_max} EGP "
        f"and a timeline of {tl}. Next step: {next_step}. "
        f"Can I confirm the right units and lock a suitable call/site visit time?"
    )

    reason_codes = [
        f"Budget fit (project range): {budget_detail} | lead budget_max={lead.budget_max or '—'}",
        f"Timeline urgency: {timeline_detail}",
        f"Intent clarity: {intent_detail} (purpose={lead.purpose or '—'})",
        f"Engagement signals: {engagement_detail} (next_step={lead.next_step or '—'})",
        f"Contact shared: {contact_detail} (name present={bool((lead.name or '').strip())}, phone provided={bool((lead.phone or '').strip())})",
    ]

    # Keep 3-6 bullets: we currently have 5.
    reason_codes = reason_codes[:6]

    return ScoreResult(
        classification=classification,
        score=score,
        reason_codes=reason_codes,
        recommended_action=recommended_action,
        handoff_summary=handoff_summary,
        primary_project=primary_project,
    )


def to_csv_fields(result: ScoreResult) -> dict[str, str]:
    return {
        "classification": result.classification,
        "score": str(result.score),
        "reason_codes": json.dumps(result.reason_codes, ensure_ascii=True),
        "recommended_action": result.recommended_action,
        "handoff_summary": result.handoff_summary,
    }

