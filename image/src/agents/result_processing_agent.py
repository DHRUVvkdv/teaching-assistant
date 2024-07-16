# agents/result_processing_agent.py

from utils.query_processing import process_query
from utils.config import COMBINED_PROMPT_TEMPLATE
from langchain.prompts import ChatPromptTemplate
from models.agent_state import AgentState
from typing import Dict


def result_processing_agent(state: AgentState) -> AgentState:
    query_text = state["query"]
    teacher_name = state["teacher_name"]
    vector_db_context = state["vector_db_context"]
    vector_db_sources = state["vector_db_sources"]
    web_search_results = state["web_search_results"]
    web_search_sources = state["web_search_sources"]

    prompt_template = ChatPromptTemplate.from_template(COMBINED_PROMPT_TEMPLATE)
    result = process_query(
        query_text,
        teacher_name,
        prompt_template,
        {
            "professor_context": vector_db_context,
            "professor_sources": "\n".join(vector_db_sources),
            "web_context": web_search_results,
            "question": query_text,
        },
    )

    state["combined_response"] = result
    state["final_result"] = parse_combined_response(result)
    return state


def parse_combined_response(response: str) -> Dict[str, str]:
    sections = [
        "Professor's Notes",
        "Professor's Sources",
        "Internet Notes",
        "Internet Sources",
        "Extra Sources",
    ]
    parsed_result = {}
    current_section = None
    for line in response.split("\n"):
        if any(section in line for section in sections):
            current_section = line.strip(":")
            parsed_result[current_section] = ""
        elif current_section:
            parsed_result[current_section] += line + "\n"
    return parsed_result
