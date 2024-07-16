# agents/translator_agent.py

from models.agent_state import AgentState
from utils.translation_utils import translate_dict
import logging


async def translator_agent(state: AgentState) -> AgentState:
    logging.info(f"Starting translation to {state['target_language']}")
    if state["target_language"] and state["target_language"].lower() != "english":
        try:
            state["translated_result"] = await translate_dict(
                state["final_result"], state["target_language"]
            )
        except Exception as e:
            logging.error(f"Translation failed: {str(e)}")
            state["translated_result"] = state[
                "final_result"
            ]  # Fallback to original result
    else:
        state["translated_result"] = state["final_result"]  # No translation needed
    logging.info(f"Starting translation to {state['target_language']}")
    return state
