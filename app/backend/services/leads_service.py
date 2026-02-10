import csv
import os
import logging
import portalocker
from datetime import datetime
from openpyxl import Workbook
from app.backend.config import Config
from app.backend.models import Lead

logger = logging.getLogger(__name__)

class LeadsService:
    def __init__(self):
        self._init_files()

    def _init_files(self):
        # Leads CSV
        if not os.path.exists(Config.LEADS_PATH):
            with open(Config.LEADS_PATH, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "session_id", "name", "phone", "email", 
                    "interest_projects", "unit_type", "budget", "intent", 
                    "timeline", "region", "next_step"
                ])
        
        # Audit CSV
        if not os.path.exists(Config.AUDIT_PATH):
            with open(Config.AUDIT_PATH, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "session_id", "user_message", "router_intent", 
                    "retrieved_projects", "similarity_scores", "kb_version", "fields_used"
                ])

    def save_lead(self, lead: Lead):
        row = [
            datetime.now().isoformat(),
            lead.session_id,
            lead.name,
            lead.phone,
            lead.email or "",
            ",".join(lead.interest_projects),
            lead.unit_type or "",
            lead.budget or "",
            lead.intent or "",
            lead.timeline or "",
            lead.region or "",
            lead.next_step or ""
        ]
        
        try:
            with open(Config.LEADS_PATH, 'a', newline='', encoding='utf-8') as f:
                portalocker.lock(f, portalocker.LOCK_EX)
                writer = csv.writer(f)
                writer.writerow(row)
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
