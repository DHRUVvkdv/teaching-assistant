# agents/translator_agent.py

# agents/translator_agent.py

from models.agent_state import AgentState
from utils.translation_utils import translate_dict
import logging


async def translator_agent(state: AgentState) -> AgentState:
    if state["target_language"] and state["target_language"].lower() != "english":
        try:
            state["translated_result"] = await translate_dict(
                state["formatted_result"], state["target_language"]
            )
        except Exception as e:
            logging.error(f"Translation failed: {str(e)}")
            state["translated_result"] = state[
                "formatted_result"
            ]  # Fallback to original result
    else:
        state["translated_result"] = state["formatted_result"]  # No translation needed
    return state
