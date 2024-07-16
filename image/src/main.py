import os
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from utils.api_key_middleware import ApiKeyMiddleware
from fastapi.openapi.utils import get_openapi
from mangum import Mangum
from pydantic import BaseModel
from models.query import QueryModel
from services.pinecone_service import (
    create_embeddings,
    query_pinecone,
    process_all_pdfs,
    list_processed_files,
    get_google_drive_link_pdf,
    update_missing_drive_links,
    update_drive_link_for_file,
    combined_query,
)
from workflow import multi_agent_query

from utils.s3_handler import get_s3_buckets, list_pdfs_in_s3
import logging
from pinecone import PineconeException
from tavily import TavilyClient
from typing import Optional, List
from utils.config import (
    TEACHER_CONFIG,
    PINECONE_API_KEY,
    BEDROCK_MODEL_ID,
    FILE_ID_SERVICE_URL,
    TAVILY_API_KEY,
    PROCESSED_FILES_TABLE,
    QUERIES_TABLE,
    PROMPT_TEMPLATE,
)


class CombinedQueryRequest(BaseModel):
    query_text: str
    teacher_name: str
    target_language: Optional[str] = None


WORKER_LAMBDA_NAME = os.environ.get("WORKER_LAMBDA_NAME", None)
# tavily_client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY", None))
tavily_client = TavilyClient(api_key=TAVILY_API_KEY)

app = FastAPI()


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Teaching Asssistant",
        version="1.0.0",
        description="API for the Teaching Assistant application",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "API-Key"}
    }
    openapi_schema["security"] = [{"ApiKeyAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi
app.add_middleware(ApiKeyMiddleware)
handler = Mangum(app)  # Entry point for AWS Lambda.


class SubmitQueryRequest(BaseModel):
    query_text: str


class EmbeddingRequest(BaseModel):
    sentences: list[str]


@app.get("/")
def index():
    return {"Hello": "World"}


@app.get("/get_query")
def get_query_endpoint(query_id: str) -> QueryModel:
    query = QueryModel.get_item(query_id)
    return query


@app.get("/get_s3")
def get_s3_endpoint():
    return get_s3_buckets()


@app.post("/create_embeddings")
def create_embeddings_endpoint(request: EmbeddingRequest, teacher_name: str):
    return create_embeddings(request.sentences, teacher_name)


@app.post("/process_all_pdfs")
def process_all_pdfs_endpoint(teacher_name: str):
    return process_all_pdfs(teacher_name)


@app.post("/query_documents")
def query_documents_endpoint(
    request: SubmitQueryRequest, teacher_name: str
) -> QueryModel:
    return query_pinecone(request.query_text, teacher_name)


@app.get("/list_processed_files")
def list_processed_files_endpoint(teacher_name: str):
    try:
        processed_files = list_processed_files(teacher_name)
        return {
            "status": "success",
            "teacher": teacher_name,
            "processed_files": processed_files,
            "total_processed_files": len(processed_files),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/list_pdfs")
async def list_pdfs_endpoint(teacher_name: str):
    try:
        config = TEACHER_CONFIG.get(teacher_name)
        if not config:
            raise ValueError(f"Error main, Invalid teacher name: {teacher_name}")
        pdfs = list_pdfs_in_s3(teacher_name)
        return {"status": "success", "total_pdfs": len(pdfs), "pdfs": pdfs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list PDFs: {str(e)}")


@app.get("/test_drive_link")
async def test_drive_link(
    pdf_name: str = Query(..., description="Name of the PDF file")
):
    try:
        drive_link = get_google_drive_link_pdf(pdf_name)
        if drive_link:
            return {"status": "success", "pdf_name": pdf_name, "drive_link": drive_link}
        else:
            return {
                "status": "not_found",
                "pdf_name": pdf_name,
                "message": "No Google Drive link found for this PDF",
            }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching Google Drive link: {str(e)}"
        )


@app.post(
    "/update_missing_drive_links", operation_id="update_missing_drive_links_endpoint"
)
async def update_missing_drive_links_endpoint(teacher_name: str):
    try:
        total_updated = update_missing_drive_links(teacher_name)
        return {
            "status": "success",
            "message": f"Updated {total_updated} vectors with missing Google Drive links for teacher {teacher_name}",
        }
    except Exception as e:
        logging.error(
            f"Error updating missing Google Drive links for teacher {teacher_name}: {str(e)}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Error updating missing Google Drive links: {str(e)}",
        )


@app.post("/update_drive_link", operation_id="update_drive_link_endpoint")
async def update_drive_link_endpoint(
    file_name: str = Query(..., description="Name of the PDF file"),
    drive_link: str = Query(..., description="Google Drive link for the file"),
    teacher_name: str = Query(..., description="Name of the teacher"),
):
    try:
        updated_count = update_drive_link_for_file(file_name, drive_link, teacher_name)
        if updated_count > 0:
            return {
                "status": "success",
                "message": f"Updated Google Drive link for {updated_count} vectors of {file_name} for teacher {teacher_name}",
                "file_name": file_name,
                "drive_link": drive_link,
                "teacher_name": teacher_name,
            }
        else:
            return {
                "status": "not_found",
                "message": f"No vectors found for {file_name} for teacher {teacher_name}",
                "file_name": file_name,
                "teacher_name": teacher_name,
            }
    except PineconeException as e:
        logging.error(f"Pinecone exception: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Pinecone error: {str(e)}")
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error updating Google Drive link: {str(e)}"
        )


@app.post("/tavily_search")
async def tavily_search(
    query: str = Query(..., description="Search query"),
    search_depth: Optional[str] = Query(
        "basic", description="Search depth: 'basic' or 'advanced'"
    ),
    max_results: Optional[int] = Query(
        5, description="Maximum number of results to return"
    ),
    include_images: Optional[bool] = Query(False, description="Include related images"),
    include_answer: Optional[bool] = Query(
        False, description="Include a short answer to the query"
    ),
    include_raw_content: Optional[bool] = Query(
        False, description="Include raw HTML content of results"
    ),
    include_domains: Optional[List[str]] = Query(
        None, description="Domains to include in search"
    ),
    exclude_domains: Optional[List[str]] = Query(
        None, description="Domains to exclude from search"
    ),
):
    try:
        # Make a call to Tavily API
        response = tavily_client.search(
            query=query,
            search_depth=search_depth,
            max_results=max_results,
            include_images=include_images,
            include_answer=include_answer,
            include_raw_content=include_raw_content,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
        )
        return {"status": "success", "query": query, "results": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in Tavily search: {str(e)}")


@app.post("/tavily_search_context")
async def tavily_search_context(
    query: str = Query(..., description="Search query"),
    search_depth: Optional[str] = Query(
        "basic", description="Search depth: 'basic' or 'advanced'"
    ),
    max_tokens: Optional[int] = Query(
        4000, description="Maximum number of tokens in the response"
    ),
):
    try:
        context = tavily_client.get_search_context(
            query=query, search_depth=search_depth, max_tokens=max_tokens
        )
        return {"status": "success", "query": query, "context": context}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error in Tavily search context: {str(e)}"
        )


@app.post("/tavily_qna_search")
async def tavily_qna_search(
    query: str = Query(..., description="Question to answer"),
    search_depth: Optional[str] = Query(
        "advanced", description="Search depth: 'basic' or 'advanced'"
    ),
):
    try:
        answer = tavily_client.qna_search(query=query, search_depth=search_depth)
        return {"status": "success", "query": query, "answer": answer}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error in Tavily QnA search: {str(e)}"
        )


# Commenting out for now, as it's being tested by the multi-agent system
# @app.post("/combined_query")
# async def combined_query_endpoint(request: CombinedQueryRequest):
#     try:
#         # Process the query
#         result = combined_query(request.query_text, request.teacher_name, tavily_client)

#         return {"status": "success", "query_id": result["query_id"], "result": result}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


@app.post("/combined_query")
async def process_combined_query(request: CombinedQueryRequest):
    try:
        result = await multi_agent_query(
            request.query_text, request.teacher_name, request.target_language
        )
        return {"status": "success", "result": result}
    except Exception as e:
        logging.error(f"Error processing combined query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    port = 8000
    print(f"Running the FastAPI server on port {port}.")
    uvicorn.run("main:app", host="0.0.0.0", port=port)
