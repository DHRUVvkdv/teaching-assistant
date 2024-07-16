# agents/result_processing_agent.py

from utils.query_processing import process_query
from utils.config import PROMPT_TEMPLATE
from langchain.prompts import ChatPromptTemplate
from models.agent_state import AgentState


def result_processing_agent(state: AgentState) -> AgentState:
    query_text = state["query"]
    teacher_name = state["teacher_name"]
    context_text = state["context_text"]
    sources = state["sources"]

    prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    result = process_query(
        query_text,
        teacher_name,
        context_text,
        prompt_template,
        {"sources": sources},
    )

    state["final_result"] = result
    return state
