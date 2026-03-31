import csv
import json
import os
import shutil
import sys
from typing import Any

from pathlib import Path

# Ensure repo root is on sys.path so `import app.backend.*` works when this file
# is executed from within `runtime/leads/`.
ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

from app.backend.config import Config
from app.backend.models import Lead
from app.backend.services.lead_scoring_engine import score_lead, to_csv_fields


def _parse_list_field(val: Any) -> list[str]:
    if val is None:
        return []
    s = str(val).strip()
    if not s:
        return []
    # If stored as JSON array string.
    if s.startswith("["):
        try:
            parsed = json.loads(s)
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed if str(x).strip()]
        except Exception:
            pass
    # Otherwise treat as comma-separated.
    return [x.strip() for x in s.split(",") if x.strip()]


def backfill() -> None:
    leads_path = Config.LEADS_PATH
    if not os.path.exists(leads_path):
        raise FileNotFoundError(f"leads.csv not found at {leads_path}")

    required_cols = [
        "classification",
        "score",
        "reason_codes",
        "recommended_action",
        "handoff_summary",
    ]

    with open(leads_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    missing = [c for c in required_cols if c not in fieldnames]
    new_fieldnames = fieldnames + missing

    if not missing:
        # Still override temperature deterministically, but we can skip header expansion.
        new_fieldnames = fieldnames

    # Backup first.
    backup_path = leads_path + ".bak_sop"
    if not os.path.exists(backup_path):
        shutil.copy2(leads_path, backup_path)

    for row in rows:
        # Build Lead object from existing columns (deterministic scoring inputs).
        lead = Lead(
            session_id=row.get("session_id", ""),
            name=row.get("name", "") or "",
            phone=row.get("phone", "") or "",
            interest_projects=_parse_list_field(row.get("interest_projects", "")),
            preferred_region=row.get("preferred_region") or None,
            unit_type=row.get("unit_type") or None,
            budget_min=row.get("budget_min") or None,
            budget_max=row.get("budget_max") or None,
            purpose=row.get("purpose") or None,
            timeline=row.get("timeline") or None,
            next_step=row.get("next_step") or None,
            lead_summary=row.get("lead_summary") or None,
            tags=_parse_list_field(row.get("tags", "")),
            temperature=row.get("temperature") or None,
            kb_version_hash=row.get("kb_version_hash") or "v1.0",
        )

        sop = score_lead(lead)
        sop_fields = to_csv_fields(sop)

        # Override existing temperature.
        row["temperature"] = sop.classification

        row["classification"] = sop_fields["classification"]
        row["score"] = sop_fields["score"]
        row["reason_codes"] = sop_fields["reason_codes"]
        row["recommended_action"] = sop_fields["recommended_action"]
        row["handoff_summary"] = sop_fields["handoff_summary"]

        # Ensure keys exist for writer.
        for c in new_fieldnames:
            if c not in row or row[c] is None:
                row[c] = ""

    with open(leads_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=new_fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Backfilled SOP scoring for {len(rows)} leads.")


if __name__ == "__main__":
    backfill()

