# agents/response_formatting_agent.py

# import logging
from models.agent_state import AgentState

# logging.basicConfig(level=logging.DEBUG)
# logger = logging.getLogger(__name__)


def response_formatting_agent(state: AgentState) -> AgentState:
    # logger.debug("Entering response_formatting_agent")
    raw_response = state.get("combined_response", "")
    # logger.debug(f"Raw response length: {len(raw_response)}")
    # logger.debug(
    #     f"Raw response preview: {raw_response[:500]}..."
    # )  # First 500 characters

    formatted_result = {
        "Professor's Notes": "",
        "Professor's Sources": [],
        "Internet Notes": "",
        "Internet Sources": [],
        "Cross-Verification and Contradictions": "",
        "Extra Sources": [],
    }

    current_section = None
    for line in raw_response.split("\n"):
        if "1. Professor's Notes:" in line:
            current_section = "Professor's Notes"
        elif "2. Professor's Sources:" in line:
            current_section = "Professor's Sources"
        elif "3. Internet Notes:" in line:
            current_section = "Internet Notes"
        elif "4. Internet Sources:" in line:
            current_section = "Internet Sources"
        elif "5. Cross-Verification and Contradictions:" in line:
            current_section = "Cross-Verification and Contradictions"
        elif "6. Extra Sources:" in line:
            current_section = "Extra Sources"
        elif current_section:
            if current_section in [
                "Professor's Sources",
                "Internet Sources",
                "Extra Sources",
            ]:
                if line.strip():
                    formatted_result[current_section].append(line.strip())
            else:
                formatted_result[current_section] += line + "\n"

        # if current_section:
        # logger.debug(f"Processing section: {current_section}")

    # Remove trailing newlines and whitespace
    for key in formatted_result:
        if isinstance(formatted_result[key], str):
            formatted_result[key] = formatted_result[key].strip()

    # logger.debug(f"Formatted result: {formatted_result}")
    state["formatted_result"] = formatted_result
    # logger.debug("Exiting response_formatting_agent")
    return state
