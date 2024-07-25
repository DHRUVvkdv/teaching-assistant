import os

TOP_K = 5

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
# BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "meta.llama3-8b-instruct-v1:0")
BEDROCK_MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"
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
# COMBINED_PROMPT_TEMPLATE = """
# You are an AI teaching assistant tasked with providing comprehensive answers using both professor's notes and internet sources. Please analyze the following information and respond to the question. Please answer based on the following context, don't use any external information:

# Professor's Notes:
# {professor_context}

# Professor's Sources:
# {professor_sources}

# Internet Information:
# {web_context}

# Question: {question}

# Please provide a detailed answer structured in the following format, keep everything in third person, don't give any external information apart from the headings:

# 1. Professor's Notes:
#    [Provide a summary of relevant information from the professor's notes]

# 2. Professor's Sources:
#    [List only the sources and the links used from the professor's notes.]

# 3. Internet Notes:
#    [Provide a summary of relevant information from internet sources]

# 4. Internet Sources:
#    [List only the sources used from internet information.]

# 5. Cross-Verification and Contradictions:
#    [Carefully compare the information from the professor's notes and internet sources. You MUST explicitly mention ANY contradictions or discrepancies found between the two sources, no matter how small or large. Pay special attention to dates, names, events, and key facts. If there are significant contradictions, emphasize them clearly. If no contradictions are found, leave this section empty.]

# 6. Extra Sources:
#    [List any sources (with their IDs) that were provided but not directly used in the answer]

# IMPORTANT: You MUST carefully check all dates, names, and key facts between the professor's notes and internet sources. Any discrepancies, especially in crucial information like the years of major historical events, MUST be highlighted and explained in detail in the Cross-Verification and Contradictions section. If no contradictions are found, leave that section empty. Failure to identify and report such contradictions when they exist is a critical error.

# Remember to be objective, accurate, and comprehensive in your response. If certain information is not available from either source, please indicate that as well.
# """
COMBINED_PROMPT_TEMPLATE = """
You are an AI teaching assistant tasked with providing comprehensive answers using both professor's notes and internet sources. Please analyze the following information and respond to the question. Please answer based on the following context, don't use any external information:

Professor's Notes:
{professor_context}

Professor's Sources:
{professor_sources}

Internet Information:
{web_context}

Question: {question}

Please provide a detailed answer strictly adhering to the following format. Use the exact headings provided and ensure each section is clearly separated:

1. Professor's Notes:
[Provide a summary of relevant information from the professor's notes]

2. Professor's Sources:
[List only the sources and the links used from the professor's notes.]

3. Internet Notes:
[Provide a summary of relevant information from internet sources]

4. Internet Sources:
[List only the sources used from internet information.]

5. Cross-Verification and Contradictions:
[Write in third person. Carefully compare the information from the professor's notes and internet sources. You MUST explicitly mention ANY contradictions or discrepancies found between the two sources, no matter how small or large. Pay special attention to dates, names, events, and key facts. If there are significant contradictions, emphasize them clearly. If no contradictions are found, write "No contradictions found." in this section.]

6. Extra Sources:
[List any sources (with their IDs) that were provided but not directly used in the answer. If no extra sources, write "No extra sources."]

IMPORTANT: You MUST carefully check all dates, names, and key facts between the professor's notes and internet sources. Any discrepancies, especially in crucial information like the years of major historical events, MUST be highlighted and explained in detail in the Cross-Verification and Contradictions section. Failure to identify and report such contradictions when they exist is a critical error.

Remember to be objective, accurate, and comprehensive in your response. If certain information is not available from either source, please indicate that as well.
"""
