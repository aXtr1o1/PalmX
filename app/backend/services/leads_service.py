import csv
import os
import logging
import portalocker
from datetime import datetime
from openpyxl import Workbook
from app.backend.config import Config
from app.backend.models import Lead
from app.backend.services.lead_scoring_engine import score_lead, to_csv_fields

logger = logging.getLogger(__name__)

class LeadsService:
    def __init__(self):
        self._init_files()

    def _init_files(self):
        # Leads CSV
        expected_headers = [
            "timestamp", "session_id", "name", "phone", 
            "interest_projects", "preferred_region", "unit_type", 
            "budget_min", "budget_max", "purpose", "timeline", 
            "next_step", "lead_summary", "tags", "temperature", "kb_version_hash",
            # SOP deterministic classification fields (added)
            "classification", "score", "reason_codes", "recommended_action", "handoff_summary",
            # Legacy columns already used by your runtime exports (kept for compatibility)
            "contact", "region", "action_taken", "raw_payload_hash"
        ]
        
        if not os.path.exists(Config.LEADS_PATH):
            with open(Config.LEADS_PATH, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(expected_headers)
        else:
            # Check if header is missing in existing file
            try:
                with open(Config.LEADS_PATH, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                    if first_line and "timestamp" not in first_line:
                        # Header likely missing (row starts with data), fix by prepending
                        content = f.read()
                        logger.info("Restoring missing headers to leads.csv")
                        with open(Config.LEADS_PATH, 'w', newline='', encoding='utf-8') as f2:
                            writer = csv.writer(f2)
                            writer.writerow(expected_headers)
                            f2.write(first_line + "\n" + content)
            except Exception as e:
                logger.error(f"Failed to verify/fix headers: {e}")
        
        # Audit CSV
        if not os.path.exists(Config.AUDIT_PATH):
            with open(Config.AUDIT_PATH, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "session_id", "user_message", "router_intent", 
                    "retrieved_projects", "similarity_scores", "kb_version", "fields_used"
                ])

    def _ensure_leads_schema(self, required_cols: list[str]) -> list[str]:
        """
        Ensure `runtime/leads/leads.csv` has all `required_cols` in its header.
        If columns are missing, rewrite the whole CSV with an expanded header (append-only).
        """
        try:
            with open(Config.LEADS_PATH, "r", encoding="utf-8") as f:
                header_line = f.readline().strip()
        except Exception:
            self._init_files()
            with open(Config.LEADS_PATH, "r", encoding="utf-8") as f:
                header_line = f.readline().strip()

        if not header_line or "timestamp" not in header_line:
            base = [
                "timestamp", "session_id", "name", "phone",
                "interest_projects", "preferred_region", "unit_type",
                "budget_min", "budget_max", "purpose", "timeline",
                "next_step", "lead_summary", "tags", "temperature", "kb_version_hash",
            ]
            fieldnames = base + required_cols
            with open(Config.LEADS_PATH, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(fieldnames)
            return fieldnames

        fieldnames = [h.strip() for h in header_line.split(",")]
        missing = [c for c in required_cols if c not in fieldnames]
        if not missing:
            return fieldnames

        # Lock to avoid concurrent schema rewrite races.
        lock_path = Config.LEADS_PATH + ".schema.lock"
        with open(lock_path, "w", encoding="utf-8") as lockf:
            portalocker.lock(lockf, portalocker.LOCK_EX)
            try:
                with open(Config.LEADS_PATH, "r", encoding="utf-8") as f:
                    header_line2 = f.readline().strip()
                fieldnames2 = [h.strip() for h in header_line2.split(",")] if header_line2 else []
                missing2 = [c for c in required_cols if c not in fieldnames2]
                if not missing2:
                    return fieldnames2

                new_fieldnames = fieldnames2 + missing2
                tmp_path = Config.LEADS_PATH + ".tmp"

                with open(Config.LEADS_PATH, "r", encoding="utf-8", newline="") as src:
                    reader = csv.DictReader(src)
                    rows = list(reader)

                with open(tmp_path, "w", encoding="utf-8", newline="") as dst:
                    writer = csv.DictWriter(dst, fieldnames=new_fieldnames)
                    writer.writeheader()
                    for r in rows:
                        for c in missing2:
                            r[c] = r.get(c, "") if r.get(c, "") is not None else ""
                        writer.writerow(r)

                os.replace(tmp_path, Config.LEADS_PATH)
                return new_fieldnames
            finally:
                portalocker.unlock(lockf)

    def save_lead(self, lead: Lead):
        # Deterministic SOP scoring at conversation completion.
        sop = score_lead(lead)
        # Override any pre-set temperature to keep deterministic SOP behavior.
        lead.temperature = sop.classification

        required_cols = [
            "classification",
            "score",
            "reason_codes",
            "recommended_action",
            "handoff_summary",
        ]

        fieldnames = self._ensure_leads_schema(required_cols)
        sop_fields = to_csv_fields(sop)

        row_dict = {
            "timestamp": datetime.now().isoformat(),
            "session_id": lead.session_id,
            "name": lead.name,
            "phone": lead.phone,
            "interest_projects": ",".join(lead.interest_projects),
            "preferred_region": lead.preferred_region or "",
            "unit_type": lead.unit_type or "",
            "budget_min": lead.budget_min or "",
            "budget_max": lead.budget_max or "",
            "purpose": lead.purpose or "",
            "timeline": lead.timeline or "",
            "next_step": lead.next_step or "",
            "lead_summary": lead.lead_summary or "",
            "tags": ",".join(lead.tags),
            "temperature": lead.temperature or "",
            "kb_version_hash": lead.kb_version_hash or "v1.0",
            **sop_fields,
            # Legacy columns exist in some datasets; keep blank for now.
            "contact": "",
            "region": "",
            "action_taken": "",
            "raw_payload_hash": "",
        }

        # Ensure any additional header columns exist in row_dict.
        for c in fieldnames:
            if c not in row_dict:
                row_dict[c] = ""

        try:
            with open(Config.LEADS_PATH, "a", newline="", encoding="utf-8") as f:
                portalocker.lock(f, portalocker.LOCK_EX)
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writerow({k: row_dict.get(k, "") for k in fieldnames})
                portalocker.unlock(f)
            return True
        except Exception as e:
            logger.error(f"Failed to save lead: {e}")
            return False

    def log_audit(self, session_id: str, user_msg: str, intent: str, retrieved: list, scores: list):
        row = [
            datetime.now().isoformat(),
            session_id,
            user_msg,
            intent,
            json.dumps(retrieved),
            json.dumps(scores),
            "v1.0", # KB Version placeholder
            "all" # Fields used placeholder
        ]
        
        try:
            with open(Config.AUDIT_PATH, 'a', newline='', encoding='utf-8') as f:
                portalocker.lock(f, portalocker.LOCK_EX)
                writer = csv.writer(f)
                writer.writerow(row)
                portalocker.unlock(f)
        except Exception as e:
            logger.error(f"Failed to log audit: {e}")

    def get_leads(self) -> list[dict]:
        leads = []
        if os.path.exists(Config.LEADS_PATH):
            with open(Config.LEADS_PATH, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                leads = list(reader)
        return leads

    def export_excel(self) -> str:
        wb = Workbook()
        ws = wb.active
        ws.title = "PalmX Leads"
        
        leads = self.get_leads()
        if not leads:
            return None
            
        # Headers
        headers = list(leads[0].keys())
        ws.append(headers)
        
        for lead in leads:
            ws.append(list(lead.values()))
            
        # Save to exports dir
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"leads_export_{timestamp}.xlsx"
        path = os.path.join(Config.RUNTIME_DIR, "exports", filename)
        wb.save(path)
        return path

import json
leads_service = LeadsService()
