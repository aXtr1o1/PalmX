from ast import Dict
from app.backend.models import ChatResponse, Message
from typing import List, Optional, Dict
from datetime import datetime
from app.backend.services.persona.commonPrompt import COMMAND_PERSONA_OUTPUT
from app.backend.services.persona.primaryMode import PRIMARY_MODES
from app.backend.services.persona.secondaryMode import SECONDARY_MODES
from app.backend.services.persona.supportMode import SUPPORT_MODES

def build_system_prompt( 
    user_message: str,
    history: List[Message],
    chat_response: ChatResponse) -> str:


    cur_date = datetime.now().strftime("%B %d, %Y")
    persona_state = chat_response.persona_state or "primary"
    persona_stage = chat_response.persona_stage or "qualification"
    support_stage = chat_response.support_stage or "faq"
   

    if persona_state == "primary":
        persona_state = "primary"
        persona_stage = PRIMARY_MODES[persona_stage]
        support_stage = SUPPORT_MODES[support_stage]
    elif persona_state == "secondary":
        persona_state = "secondary"
        persona_stage = SECONDARY_MODES[persona_stage]
        support_stage = SUPPORT_MODES[support_stage]
    elif persona_state == "support":
        persona_state = "support"
        # For support persona, only support_stage rules matter.
        support_stage = SUPPORT_MODES[support_stage]
    
    system_prompt = f"""
    {COMMAND_PERSONA_OUTPUT.format(persona_state=persona_state, persona_stage=persona_stage, support_stage=support_stage, current_date=cur_date)}
    """
    return system_prompt