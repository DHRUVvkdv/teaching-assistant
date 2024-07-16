# src/agents/vector_db_agent.py

from models.agent_state import AgentState
from utils.vector_db_utils import query_vector_db


async def vector_db_agent(state: AgentState) -> AgentState:
    vector_db_results = await query_vector_db(
        state["processed_query"], state["teacher_name"]
    )
    state["vector_db_context"] = vector_db_results["context_text"]
    state["vector_db_sources"] = vector_db_results["sources"]
    return state
