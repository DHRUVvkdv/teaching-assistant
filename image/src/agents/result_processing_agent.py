# agents/result_processing_agent.py
# import logging
from utils.query_processing import process_query
from utils.config import COMBINED_PROMPT_TEMPLATE
from langchain.prompts import ChatPromptTemplate
from models.agent_state import AgentState
from typing import Dict

# logging.basicConfig(level=logging.DEBUG)
# logger = logging.getLogger(__name__)


def result_processing_agent(state: AgentState) -> AgentState:
    # logger.debug("Entering result_processing_agent")
    query_text = state["query"]
    teacher_name = state["teacher_name"]
    vector_db_context = state["vector_db_context"]
    vector_db_sources = state["vector_db_sources"]
    web_search_results = state["web_search_results"]
    web_search_sources = state["web_search_sources"]

    # logger.debug(f"Query: {query_text}")
    # logger.debug(f"Teacher: {teacher_name}")
    # logger.debug(f"Vector DB Context Length: {len(vector_db_context)}")
    # logger.debug(f"Vector DB Sources: {vector_db_sources}")
    # logger.debug(f"Web Search Results Length: {len(web_search_results)}")
    # logger.debug(f"Web Search Sources: {web_search_sources}")

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

    # logger.debug(f"Raw result length: {len(result)}")
    # logger.debug(f"Raw result preview: {result[:500]}...")  # First 500 characters

    state["combined_response"] = result
    state["final_result"] = parse_combined_response(result)

    # logger.debug(f"Parsed result: {state['final_result']}")
    # logger.debug("Exiting result_processing_agent")
    return state


def parse_combined_response(response: str) -> Dict[str, str]:
    # logger.debug("Entering parse_combined_response")
    sections = [
        "Professor's Notes",
        "Professor's Sources",
        "Internet Notes",
        "Internet Sources",
        "Cross-Verification and Contradictions",
        "Extra Sources",
    ]
    parsed_result = {}
    current_section = None
    for line in response.split("\n"):
        if any(section in line for section in sections):
            current_section = line.strip(":")
            parsed_result[current_section] = ""
            # logger.debug(f"Found section: {current_section}")
        elif current_section:
            parsed_result[current_section] += line + "\n"

    # logger.debug(f"Parsed sections: {list(parsed_result.keys())}")
    # logger.debug("Exiting parse_combined_response")
    return parsed_result
