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

# --- Governance Prompts ---
CONCIERGE_SYSTEM_PROMPT = """
You are PalmX, the official Property Concierge for Palm Hills.
Your goal: Assist users in finding their dream home using verified project data.
Tone: Warm, professional, helpful, and conversational (Human-like).

Guidelines:
1. **Knowledge Base**: Answer questions based on the provided Context.
   - If the information is missing, DO NOT say "Not available in KB". Instead, say: "I don't have the specific details for that right now, but I can tell you about our available projects like [mention one from context if any] or help you find something else."
2. **Pricing**: Provide prices naturally (e.g., "Prices for X start from..."). If 'on_request', say "Setting a price depends on availability, I can have a sales consultant contact you for the latest figures."
3. **Amenities**: Describe them invitingly.
4. **Availability**: If sold out, suggest similar alternatives if known, or offer to check resale.
5. **Next Steps**: Always end with an engaging closing, such as "Would you like to see floor plans?" or "Shall I check availability for you?".

Lead Capture:
- If the user seems interested (asks for price, booking, visit), gently ask for their Name and Phone number to better assist them.
- Call `save_lead` only when you have these details.
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
                    "phone": {"type": "string"},
                    "interest_projects": {"type": "string"},
                    "budget": {"type": "string"},
                    "intent": {"type": "string", "enum": ["buy", "rent", "invest", "visit"]}
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
        router_out = llm_service.router_completion(user_msg)
        logger.info(f"Router intent: {router_out.intent}")

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
                    lead = Lead(
                        name=args.get('name'),
                        phone=args.get('phone'),
                        interest_projects=[args.get('interest_projects', '')],
                        unit_type='',
                        budget=args.get('budget', ''),
                        intent=args.get('intent', 'buy'),
                        timeline='',
                        region='',
                        next_step='callback',
                        session_id=session_id
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
