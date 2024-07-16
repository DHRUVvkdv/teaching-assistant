# src/agent_state.py

from typing import TypedDict, Optional, List, Dict


class AgentState(TypedDict):
    query: str
    teacher_name: str
    processed_query: Optional[str]
    vector_db_context: Optional[str]
    vector_db_sources: Optional[List[str]]
    web_search_results: Optional[str]
    web_search_sources: Optional[List[str]]
    combined_response: Optional[str]
    final_result: Optional[Dict[str, str]]
    target_language: Optional[str]
    translated_result: Optional[Dict[str, str]]


def create_initial_state(
    query: str, teacher_name: str, target_language: Optional[str] = None
) -> AgentState:
    return AgentState(
        query=query,
        teacher_name=teacher_name,
        processed_query=None,
        vector_db_context=None,
        vector_db_sources=None,
        web_search_results=None,
        web_search_sources=None,
        combined_response=None,
        final_result=None,
        target_language=target_language,
        translated_result=None,
    )
