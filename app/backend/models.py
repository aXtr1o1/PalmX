from typing import List, Optional, Any
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
    # Store full raw row for reference if needed, or specific mapped fields
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
    mode: str = "concierge" # concierge | lead_capture

# --- Lead Models ---
class Lead(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    interest_projects: List[str] = []
    unit_type: Optional[str] = None
    budget: Optional[str] = None
    intent: Optional[str] = None # buy | rent | invest
    timeline: Optional[str] = None
    region: Optional[str] = None
    next_step: Optional[str] = None # call | visit
    session_id: str
