# utils/web_search_utils.py

from tavily import TavilyClient
from utils.config import TAVILY_API_KEY
import logging
from typing import List
from fastapi import HTTPException

tavily_client = TavilyClient(api_key=TAVILY_API_KEY)


async def perform_web_search(query: str):
    try:
        results = tavily_client.get_search_context(
            query=query,
            search_depth="advanced",
            max_tokens=2000,
        )
        return {"context": results, "sources": extract_sources(results)}
    except Exception as e:
        logging.error(f"Failed to perform web search: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to perform web search: {str(e)}",
        )


def extract_sources(results: str) -> List[str]:
    # Implement logic to extract sources from the Tavily results
    # This is a placeholder implementation
    return ["Web Source 1", "Web Source 2"]  # Replace with actual source extraction
