import os

TOP_K = 3

TEACHER_CONFIG = {
    "drvinay": {
        "index_name": "drvinay",
        "s3_prefix": "data/pdfs/drvinay/",
        "top_k": TOP_K,
    },
    "lewas": {"index_name": "lewas", "s3_prefix": "data/pdfs/lewas/", "top_k": TOP_K},
    "historyoftech": {
        "index_name": "historyoftech",
        "s3_prefix": "data/pdfs/historyoftech/",
        "top_k": TOP_K,
    },
}

# Environment variables
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "meta.llama3-8b-instruct-v1:0")
FILE_ID_SERVICE_URL = os.environ.get(
    "FILE_ID_SERVICE_URL", "http://host.docker.internal:8001"
)
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")

# S3 bucket name
S3_BUCKET = os.environ.get("S3_BUCKET", "teaching-assistant-tavily")

# DynamoDB table names
PROCESSED_FILES_TABLE = "teaching-assistant-tavily-processed-files"
QUERIES_TABLE = "teaching-assistant-tavily-queries-table"

# PDF Processor constants
PDF_CHUNK_SIZE = 600
PDF_CHUNK_OVERLAP = 120
# Other constants
PROMPT_TEMPLATE = """
Answer the question based only on the following context:

{context}

---

Answer the question based on the above context: {question}
"""
