from app.backend.models import ChatResponse, Message
from typing import List
from datetime import datetime
from app.backend.services.persona.commonPrompt import COMMAND_PERSONA_OUTPUT

def build_system_prompt( 
    user_message: str,
    history: List[Message],
    chat_response: ChatResponse) -> str:


    cur_date = datetime.now().strftime("%B %d, %Y")
    # IMPORTANT:
    # `persona/commonPrompt.py` already contains stage logic and expects stage
    # identifiers as strings (e.g. `shortlist`, `handover`, `shortlist_refinement`).
    # The previous approach tried to map these identifiers into
    # PRIMARY_MODES/SECONDARY_MODES/SUPPORT_MODES dicts, which caused KeyErrors
    # like `Stream chat error: 'shortlist'`.
    # We now pass the stage identifiers directly into the prompt.
    persona_state = chat_response.persona_state or "primary"
    persona_stage = chat_response.persona_stage or "qualification"
    support_stage = chat_response.support_stage or "faq"
    
    system_prompt = f"""
    {COMMAND_PERSONA_OUTPUT.format(persona_state=persona_state, persona_stage=persona_stage, support_stage=support_stage, current_date=cur_date)}
    """
    return system_prompt