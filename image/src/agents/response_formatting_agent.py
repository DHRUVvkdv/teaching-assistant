# agents/response_formatting_agent.py

from models.agent_state import AgentState


def response_formatting_agent(state: AgentState) -> AgentState:
    raw_response = state.get("combined_response", "")

    formatted_result = {
        "Professor's Notes": "",
        "Professor's Sources": [],
        "Internet Notes": "",
        "Internet Sources": [],
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
        elif "5. Extra Sources:" in line:
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

    state["formatted_result"] = formatted_result
    return state
