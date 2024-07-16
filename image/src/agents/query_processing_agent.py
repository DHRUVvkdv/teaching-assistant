from models.agent_state import AgentState


def query_processing_agent(state: AgentState) -> AgentState:
    query = state["query"]
    teacher_name = state["teacher_name"]

    # TODO: Implement difficulty-based query modification
    # For now, we'll just pass the query as is
    processed_query = query

    state["processed_query"] = processed_query
    return state
