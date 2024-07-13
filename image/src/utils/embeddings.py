from typing import Any
from langchain_aws import BedrockEmbeddings


def get_embedding_function() -> Any:
    """
    Returns an instance of BedrockEmbeddings.

    Returns:
        Any: An instance of BedrockEmbeddings.
    """
    return BedrockEmbeddings()
