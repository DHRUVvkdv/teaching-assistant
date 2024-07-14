import os
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from utils.api_key_middleware import ApiKeyMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import get_swagger_ui_html
from mangum import Mangum
from pydantic import BaseModel
from models.query import QueryModel
from services.pinecone_service import (
    initialize_pinecone,
    create_embeddings,
    query_pinecone,
    process_resume_pdf,
    process_all_pdfs,
    list_processed_files,
    get_google_drive_link_pdf,
    update_missing_drive_links,
    update_drive_link_for_file,
)
from utils.s3_handler import get_s3_buckets, list_pdfs_in_s3
import logging
from pinecone import PineconeException


WORKER_LAMBDA_NAME = os.environ.get("WORKER_LAMBDA_NAME", None)

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


@app.post("/initialize_pinecone")
def initialize_pinecone_endpoint():
    return initialize_pinecone()


@app.post("/create_embeddings")
def create_embeddings_endpoint(request: EmbeddingRequest):
    return create_embeddings(request.sentences)


@app.post("/process_resume_pdf")
def process_resume_pdf_endpoint():
    return process_resume_pdf()


@app.post("/process_all_pdfs")
def process_all_pdfs_endpoint():
    return process_all_pdfs()


@app.post("/query_documents")
def query_documents_endpoint(request: SubmitQueryRequest) -> QueryModel:
    return query_pinecone(request.query_text)


@app.get("/list_processed_files")
def list_processed_files_endpoint():
    try:
        processed_files = list_processed_files()
        return {
            "status": "success",
            "processed_files": processed_files,
            "total_processed_files": len(processed_files),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/list_pdfs")
async def list_pdfs_endpoint():
    try:
        pdfs = list_pdfs_in_s3()
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
async def update_missing_drive_links_endpoint():
    try:
        total_updated = update_missing_drive_links()
        return {
            "status": "success",
            "message": f"Updated {total_updated} vectors with missing Google Drive links",
        }
    except Exception as e:
        logging.error(f"Error updating missing Google Drive links: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error updating missing Google Drive links: {str(e)}",
        )


@app.post("/update_drive_link", operation_id="update_drive_link_endpoint")
async def update_drive_link_endpoint(
    file_name: str = Query(..., description="Name of the PDF file"),
    drive_link: str = Query(..., description="Google Drive link for the file"),
):
    try:
        updated_count = update_drive_link_for_file(file_name, drive_link)
        if updated_count > 0:
            return {
                "status": "success",
                "message": f"Updated Google Drive link for {updated_count} vectors of {file_name}",
                "file_name": file_name,
                "drive_link": drive_link,
            }
        else:
            return {
                "status": "not_found",
                "message": f"No vectors found for {file_name}",
                "file_name": file_name,
            }
    except PineconeException as e:
        logging.error(f"Pinecone exception: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Pinecone error: {str(e)}")
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error updating Google Drive link: {str(e)}"
        )


if __name__ == "__main__":
    port = 8000
    print(f"Running the FastAPI server on port {port}.")
    uvicorn.run("main:app", host="0.0.0.0", port=port)
