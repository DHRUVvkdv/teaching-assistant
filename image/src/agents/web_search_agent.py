# src/agents/web_search_agent.py

from models.agent_state import AgentState
from utils.web_search_utils import perform_web_search


async def web_search_agent(state: AgentState) -> AgentState:
    web_results = await perform_web_search(state["processed_query"])
    state["web_search_results"] = web_results["context"]
    state["web_search_sources"] = web_results["sources"]
    return state
