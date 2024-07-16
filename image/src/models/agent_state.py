# src/agent_state.py

from typing import TypedDict, Optional, List


class AgentState(TypedDict):
    query: str
    teacher_name: str
    processed_query: Optional[str]
    context_text: Optional[str]
    sources: Optional[List[str]]
    final_result: Optional[dict]


# class AgentState(TypedDict):
#     query: str
#     teacher_name: str
#     teacher_context: Optional[str]
#     teacher_sources: Optional[List[str]]
#     processed_query: Optional[str]
#     context_text: Optional[str]
#     sources: Optional[List[str]]
#     final_result: Optional[dict]


def create_initial_state(query: str, teacher_name: str) -> AgentState:
    return AgentState(
        query=query,
        teacher_name=teacher_name,
        processed_query=None,
        context_text=None,
        sources=None,
        final_result=None,
    )
