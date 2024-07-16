# src/workflow.py

import asyncio
from langgraph.graph import Graph
from models.agent_state import AgentState, create_initial_state
from agents.query_processing_agent import query_processing_agent
from agents.vector_db_agent import vector_db_agent
from agents.web_search_agent import web_search_agent
from agents.result_processing_agent import result_processing_agent
from agents.translator_agent import translator_agent
from typing import Optional, Tuple, Dict, Any, TypedDict


# Define a TypedDict for the parallel search results
class ParallelSearchResults(TypedDict):
    vector_db: Dict[str, Any]
    web_search: Dict[str, Any]


def create_workflow():
    workflow = Graph()

    # Add nodes for each agent
    workflow.add_node("query_processing", query_processing_agent)
    workflow.add_node("parallel_search", parallel_search)
    workflow.add_node("result_processing", result_processing_agent)
    workflow.add_node("translator", translator_agent)

    # Set up edges
    workflow.add_edge("query_processing", "parallel_search")
    workflow.add_edge("parallel_search", "result_processing")
    workflow.add_edge("result_processing", "translator")

    # Set entry and finish points
    workflow.set_entry_point("query_processing")
    workflow.set_finish_point("translator")

    return workflow.compile()


async def parallel_search(state: AgentState) -> AgentState:
    vector_db_task = asyncio.create_task(vector_db_agent(state))
    web_search_task = asyncio.create_task(web_search_agent(state))
    vector_db_result, web_search_result = await asyncio.gather(
        vector_db_task, web_search_task
    )

    # Merge results from both tasks
    state.update(vector_db_result)
    state.update(web_search_result)
    return state


app_workflow = create_workflow()


async def multi_agent_query(
    query_text: str, teacher_name: str, target_language: Optional[str] = None
):
    initial_state = create_initial_state(query_text, teacher_name, target_language)

    result = await app_workflow.ainvoke(initial_state)
    return result[
        "translated_result"
    ]  # This will be the original result if no translation was needed
