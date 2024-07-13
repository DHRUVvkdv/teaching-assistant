import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    # General Config
    DEBUG = os.getenv("DEBUG", "False") == "True"
    TESTING = os.getenv("TESTING", "False") == "True"
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")

    # AWS Configuration
    # AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID") Lambda error - AWS_ACCESS_KEY_ID environment variable is reserved by the lambda runtime and can not be set manually
    # AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    # AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

    # S3 Configuration
    S3_BUCKET = os.getenv("S3_BUCKET", "lewas-chatbot")
    PDF_PREFIX = os.getenv("PDF_PREFIX", "data/pdfs/")

    # DynamoDB Configuration
    DYNAMODB_TABLE_NAME = os.getenv("TABLE_NAME", "your-table-name")

    # Pinecone Configuration
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "chatbot-index")

    # Bedrock Configuration
    BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "meta.llama3-8b-instruct-v1:0")

    # File ID Service Configuration
    FILE_ID_SERVICE_URL = os.getenv(
        "FILE_ID_SERVICE_URL", "http://host.docker.internal:8001"
    )

    # FastAPI Configuration
    API_PORT = int(os.getenv("API_PORT", 8000))

    # Worker Lambda Configuration
    WORKER_LAMBDA_NAME = os.getenv("WORKER_LAMBDA_NAME")

    # Add any other configuration variables your application needs

    @staticmethod
    def is_production():
        return os.getenv("ENVIRONMENT") == "production"


config = Config()
