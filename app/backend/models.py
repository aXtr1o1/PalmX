from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field

# --- KB Models ---
class Project(BaseModel):
    project_id: str
    project_name: str
    brand_family: Optional[str] = None
    official_project_url: Optional[str] = None
    region: Optional[str] = None
    city_area: Optional[str] = None
    project_type: Optional[str] = None
    project_status: Optional[str] = None
    starting_price_value: Optional[int] = None
    price_status: Optional[str] = None
    key_amenities: List[str] = []
    raw_data: dict = {}

# --- Router Models ---
class RouterOutput(BaseModel):
    intent: str = Field(..., description="project_query | list_projects | compare | pricing | amenity_check | lead_capture | support_contact")
    entities: List[str] = Field(default_factory=list, description="Extracted project names")
    region: Optional[str] = None
    filters: dict = Field(default_factory=dict, description="project_type, project_status, etc.")
    needs: List[str] = Field(default_factory=list, description="Requested fields like pricing, location")
    query_rewrite: str = Field(..., description="Cleaned query for vector search")
    ambiguous: bool = False
    clarification_question: Optional[str] = None

# --- Chat Models ---
class Message(BaseModel):
    role: str # user | assistant | system
    content: str
    
class ChatRequest(BaseModel):
    session_id: str
    messages: List[Message]
    locale: str = "en"

class ChatResponse(BaseModel):
    message: str
    next_action: Optional[str] = None
    retrieved_projects: List[str] = []
    # --- NEW FIELDS FOR RECOMMENDATIONS ---
    project_cards: Optional[List[Dict[str, Any]]] = None 
    trim_intro: bool = False
    # --------------------------------------
    mode: str = "concierge"                            
    persona_state: str = "primary" 
    persona_stage: str = "qualification"
    support_stage: str = "faq"                          
    tool_calls: Optional[List[Dict]] = None            
    context_summary: Optional[str] = None              
    kb_version_hash: Optional[str] = "v1.0"            

# --- Lead Models ---
class Lead(BaseModel):
    name: str
    phone: str
    interest_projects: List[str] = Field(default_factory=list) 
    preferred_region: Optional[str] = None
    unit_type: Optional[str] = None 
    budget_min: Optional[str] = None
    budget_max: Optional[str] = None
    purpose: Optional[str] = None 
    timeline: Optional[str] = None 
    next_step: Optional[str] = None 
    lead_summary: Optional[str] = None 
    tags: List[str] = Field(default_factory=list) 
    temperature: Optional[str] = None 
    kb_version_hash: Optional[str] = "v1.0"
    session_id: str