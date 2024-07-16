# utils/vector_db_utils.py

import logging
from fastapi import HTTPException
from utils.config import TEACHER_CONFIG
from utils.embeddings import get_embedding_function
from pinecone import Pinecone
from utils.config import (
    TEACHER_CONFIG,
    PINECONE_API_KEY,
    PROCESSED_FILES_TABLE,
    QUERIES_TABLE,
    FILE_ID_SERVICE_URL,
    PROMPT_TEMPLATE,
    BEDROCK_MODEL_ID,
    COMBINED_PROMPT_TEMPLATE,
)

pc = Pinecone(api_key=PINECONE_API_KEY)


def query_vector_db(query_text, teacher_name):
    try:
        config = TEACHER_CONFIG.get(teacher_name)
        if not config:
            raise ValueError(f"Invalid teacher name: {teacher_name}")

        index_name = config["index_name"]
        top_k = config["top_k"]

        index = pc.Index(index_name)
        embedding_function = get_embedding_function()
        query_embedding = embedding_function.embed_query(query_text)

        results = index.query(
            vector=query_embedding, top_k=top_k, include_metadata=True
        )

        context_text = "\n\n---\n\n".join(
            [match.metadata["text"] for match in results.matches]
        )

        sources = [
            f"{match.metadata['source']} (Page {match.metadata.get('page', 'N/A')}) - {match.metadata.get('google_drive_link', 'No link available')}"
            for match in results.matches
        ]

        return {
            "context_text": context_text,
            "sources": sources,
        }
    except Exception as e:
        logging.error(f"Failed to query vector database: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to query vector database: {str(e)}",
        )
