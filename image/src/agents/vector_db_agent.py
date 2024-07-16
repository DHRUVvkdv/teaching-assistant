# agents/vector_db_agent.py

from utils.vector_db_utils import query_vector_db
from models.agent_state import AgentState


def vector_db_agent(state: AgentState) -> AgentState:
    processed_query = state["processed_query"]
    teacher_name = state["teacher_name"]

    vector_db_results = query_vector_db(processed_query, teacher_name)

    state["context_text"] = vector_db_results["context_text"]
    state["sources"] = vector_db_results["sources"]
    return state
