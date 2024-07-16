# src/agents/query_processing_agent.py

from models.agent_state import AgentState


def query_processing_agent(state: AgentState) -> AgentState:
    query = state["query"]
    # Process the query (e.g., expand, reformat, etc.)
    processed_query = query  # Replace with actual processing logic
    state["processed_query"] = processed_query
    return state
