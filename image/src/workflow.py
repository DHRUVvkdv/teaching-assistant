# src/workflow.py

from langgraph.graph import Graph
from models.agent_state import AgentState, create_initial_state
from agents.query_processing_agent import query_processing_agent
from agents.vector_db_agent import vector_db_agent
from agents.result_processing_agent import result_processing_agent


def create_workflow():
    workflow = Graph()

    workflow.add_node("query_processing", query_processing_agent)
    workflow.add_node("vector_db", vector_db_agent)
    workflow.add_node("result_processing", result_processing_agent)

    workflow.add_edge("query_processing", "vector_db")
    workflow.add_edge("vector_db", "result_processing")

    workflow.set_entry_point("query_processing")
    workflow.set_finish_point("result_processing")

    return workflow.compile()


app_workflow = create_workflow()


def multi_agent_query(query_text: str, teacher_name: str):
    initial_state = create_initial_state(query_text, teacher_name)

    result = app_workflow.invoke(initial_state)
    return result["final_result"]
