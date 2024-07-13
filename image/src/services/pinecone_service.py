import os
from fastapi import HTTPException
from pinecone import Pinecone, ServerlessSpec
from models.query import QueryModel
from utils.embeddings import get_embedding_function
from langchain.prompts import ChatPromptTemplate
from langchain_aws import ChatBedrock
import logging
import uuid
import time
from utils.s3_handler import get_pdf_from_s3, list_pdfs_in_s3
from utils.pdf_processor import process_pdf
import boto3
from botocore.exceptions import ClientError
import requests
from pinecone import PineconeException

PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.environ.get("PINECONE_INDEX_NAME", "chatbot-index")
BEDROCK_MODEL_ID = "meta.llama3-8b-instruct-v1:0"
# BEDROCK_MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"

# Use host.docker.internal to refer to the host machine from within the container
FILE_ID_SERVICE_URL = "http://host.docker.internal:8001"


dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("lewas-chatbot-processed-files")

PROMPT_TEMPLATE = """
Answer the question based only on the following context:

{context}

---

Answer the question based on the above context: {question}
"""

pc = Pinecone(api_key=PINECONE_API_KEY)

# Add this function to pinecone_db.py


def list_processed_files():
    try:
        index = pc.Index(PINECONE_INDEX_NAME)

        # Get index stats
        stats = index.describe_index_stats()
        total_vector_count = stats["total_vector_count"]

        logging.info(f"Total vectors in index: {total_vector_count}")

        if total_vector_count == 0:
            return {
                "status": "success",
                "message": "No vectors found in the index.",
                "processed_files": [],
                "total_processed_files": 0,
            }

        # Fetch all vectors in batches of 1000
        batch_size = 1000
        processed_files = set()

        for i in range(0, total_vector_count, batch_size):
            batch_ids = [
                str(j) for j in range(i, min(i + batch_size, total_vector_count))
            ]
            vectors = index.fetch(ids=batch_ids)

            for _, vector in vectors["vectors"].items():
                metadata = vector.get("metadata", {})
                if "source" in metadata:
                    processed_files.add(
                        metadata["source"].split("/")[-1]
                    )  # Add just the filename

            logging.info(
                f"Processed batch {i//batch_size + 1}, total files found: {len(processed_files)}"
            )

        processed_files_list = list(processed_files)

        return processed_files_list  # Return just the list of files

    except Exception as e:
        logging.error(f"Failed to list processed files: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to list processed files: {str(e)}"
        )


def initialize_pinecone():
    try:
        if PINECONE_INDEX_NAME not in pc.list_indexes().names():
            pc.create_index(
                name=PINECONE_INDEX_NAME,
                dimension=1536,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east1-free"),
            )
        return {"status": "success", "message": "Pinecone initialized successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to initialize Pinecone: {str(e)}"
        )


def create_embeddings(sentences):
    try:
        embedding_function = get_embedding_function()
        embedding_vectors = embedding_function.embed_documents(sentences)

        index = pc.Index(PINECONE_INDEX_NAME)

        vectors_to_upsert = []
        for i, (text, vector) in enumerate(zip(sentences, embedding_vectors)):
            vectors_to_upsert.append((f"vec_{i}", vector, {"text": text}))

        index.upsert(vectors=vectors_to_upsert)

        return {
            "status": "success",
            "message": f"Added {len(sentences)} embeddings to Pinecone",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create embeddings: {str(e)}"
        )


def query_pinecone(query_text, top_k=3):
    try:
        index = pc.Index(PINECONE_INDEX_NAME)

        embedding_function = get_embedding_function()
        query_embedding = embedding_function.embed_query(query_text)

        results = index.query(
            vector=query_embedding, top_k=top_k, include_metadata=True
        )

        context_text = "\n\n---\n\n".join(
            [match.metadata["text"] for match in results.matches]
        )

        prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
        prompt = prompt_template.format(context=context_text, question=query_text)

        model = ChatBedrock(model_id=BEDROCK_MODEL_ID)
        response = model.invoke(prompt)
        response_text = response.content

        # Create a list of strings for sources
        sources = [
            f"{match.metadata['source']} (Page {match.metadata.get('page', 'N/A')}) - {match.metadata.get('google_drive_link', 'No link available')}"
            for match in results.matches
        ]

        new_query = QueryModel(
            query_id=uuid.uuid4().hex,
            create_time=int(time.time()),
            query_text=query_text,
            answer_text=response_text,
            sources=sources,
            is_complete=True,
        )

        logging.info(f"Query processed successfully: {new_query.query_id}")

        return new_query
    except Exception as e:
        logging.error(f"Failed to query Pinecone: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to query Pinecone: {str(e)}"
        )


def process_resume_pdf():
    try:
        pdf_content = get_pdf_from_s3("resume.pdf")
        chunks = process_pdf(pdf_content, "resume.pdf")

        index = pc.Index(PINECONE_INDEX_NAME)
        embedding_function = get_embedding_function()

        vectors_to_upsert = []
        for chunk in chunks:
            embedding = embedding_function.embed_query(chunk.page_content)
            vectors_to_upsert.append(
                (
                    chunk.metadata["id"],
                    embedding,
                    {
                        "text": chunk.page_content,
                        "source": chunk.metadata["source"],
                        "page": chunk.metadata.get("page", 0),
                    },
                )
            )

        index.upsert(vectors=vectors_to_upsert)

        return {
            "status": "success",
            "message": f"Processed and added {len(chunks)} chunks from resume.pdf to Pinecone",
        }

    except Exception as e:
        logging.error(f"Failed to process resume PDF: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to process resume PDF: {str(e)}"
        )


def process_pdf_file(pdf_key):
    try:
        pdf_content = get_pdf_from_s3(pdf_key)
        chunks = process_pdf(pdf_content, pdf_key)

        index = pc.Index(PINECONE_INDEX_NAME)
        embedding_function = get_embedding_function()

        google_drive_link = get_google_drive_link_pdf(pdf_key)

        vectors_to_upsert = []
        for chunk in chunks:
            embedding = embedding_function.embed_query(chunk.page_content)
            metadata = chunk.metadata.copy()  # Start with the existing metadata
            metadata.update(
                {
                    "text": chunk.page_content,
                    "google_drive_link": google_drive_link,
                    "processed_date": int(time.time()),
                }
            )
            vectors_to_upsert.append((metadata["id"], embedding, metadata))

        index.upsert(vectors=vectors_to_upsert)
        # Add the processed file to DynamoDB
        add_processed_file_dynamodb(pdf_key)
        return len(chunks)
    except Exception as e:
        logging.error(f"Failed to process PDF {pdf_key}: {str(e)}")
        return 0


def process_all_pdfs():
    try:
        available_pdfs = list_pdfs_in_s3()
        processed_files = list_processed_files()

        total_chunks_added = 0
        newly_processed_files = 0
        already_processed_files = len(processed_files)
        newly_processed_file_details = []
        failed_files = []

        for pdf_key in available_pdfs:
            pdf_name = pdf_key.split("/")[-1]  # Extract filename from the full path
            if pdf_name not in processed_files:
                chunks_added = process_pdf_file(pdf_name)
                if chunks_added > 0:
                    total_chunks_added += chunks_added
                    newly_processed_files += 1
                    newly_processed_file_details.append(
                        f"{pdf_name}: {chunks_added} chunks"
                    )
                else:
                    failed_files.append(pdf_name)

        return {
            "status": "success",
            "message": f"Processed {newly_processed_files} new PDF files and added {total_chunks_added} chunks to Pinecone.",
            "details": {
                "already_processed_files": already_processed_files,
                "newly_processed_files": newly_processed_files,
                "total_chunks_added": total_chunks_added,
                "newly_processed_file_details": newly_processed_file_details,
                "failed_files": failed_files,
            },
        }

    except Exception as e:
        logging.error(f"Failed to process PDFs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process PDFs: {str(e)}")


def list_processed_files():
    try:
        response = table.scan()
        processed_files = [item["filename"] for item in response["Items"]]

        return processed_files
    except ClientError as e:
        logging.error(f"Failed to list processed files from DynamoDB: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to list processed files: {str(e)}"
        )


def add_processed_file_dynamodb(filename):
    try:
        table.put_item(Item={"filename": filename})
    except ClientError as e:
        logging.error(f"Failed to add processed file to DynamoDB: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to add processed file: {str(e)}"
        )


def get_google_drive_link_pdf(pdf_name):
    try:
        response = requests.get(
            f"{FILE_ID_SERVICE_URL}/file_id",
            params={"file_type": "pdf", "file_name": pdf_name},
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()
        file_id = data.get("id", "")
        if file_id:
            return f"https://drive.google.com/file/d/{file_id}/view"
        else:
            logging.warning(f"No file_id found for {pdf_name}")
            return ""
    except requests.RequestException as e:
        logging.error(f"Failed to fetch Google Drive link for {pdf_name}: {str(e)}")
        return ""
    except Exception as e:
        logging.error(
            f"Unexpected error fetching Google Drive link for {pdf_name}: {str(e)}"
        )
        return ""


def update_missing_drive_links():
    index = pc.Index(PINECONE_INDEX_NAME)

    batch_size = 1000
    total_updated = 0
    cursor = None

    while True:
        try:
            query_response = index.query(
                vector=[0] * 1536,
                top_k=batch_size,
                include_metadata=True,
                include_values=True,
                filter={},
                cursor=cursor,
            )

            if not query_response.matches:
                break

            updates = []
            for match in query_response.matches:
                should_update = False
                new_metadata = dict(match.metadata)

                if (
                    "google_drive_link" not in new_metadata
                    or not new_metadata["google_drive_link"]
                ):
                    should_update = True

                if should_update:
                    pdf_name = new_metadata.get("source", "").split("/")[-1]
                    if pdf_name:
                        drive_link = get_google_drive_link_pdf(pdf_name)
                        if drive_link:
                            new_metadata["google_drive_link"] = drive_link
                            updates.append(
                                {
                                    "id": match.id,
                                    "values": match.values,
                                    "metadata": new_metadata,
                                }
                            )

            if updates:
                upsert_response = index.upsert(vectors=updates)
                total_updated += len(updates)
                logging.info(f"Upsert response: {upsert_response}")

            logging.info(
                f"Updated {len(updates)} vectors in this batch. Total updated: {total_updated}"
            )

            cursor = query_response.cursor
            if cursor is None:
                break

        except PineconeException as e:
            logging.error(f"Pinecone error during batch update: {str(e)}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error during batch update: {str(e)}")
            raise

    return total_updated


def update_drive_link_for_file(file_name: str, drive_link: str):
    try:
        index = pc.Index(PINECONE_INDEX_NAME)

        # Query for vectors with the given file name
        query_response = index.query(
            vector=[0] * 1536,  # Use a zero vector for querying
            top_k=10000,
            include_metadata=True,
            include_values=True,  # Include vector values in the response
            filter={"source": {"$eq": file_name}},
        )

        logging.info(f"Query response for {file_name}: {query_response}")

        if not query_response.matches:
            logging.warning(f"No matches found for file: {file_name}")
            return 0

        updates = []
        for match in query_response.matches:
            # Create a new metadata dictionary
            new_metadata = dict(match.metadata)
            new_metadata["google_drive_link"] = drive_link
            updates.append(
                {
                    "id": match.id,
                    "values": match.values,  # Include the original vector values
                    "metadata": new_metadata,
                }
            )

        if updates:
            # Use upsert with the correct format
            upsert_response = index.upsert(vectors=updates)
            logging.info(f"Upsert response: {upsert_response}")
            return len(updates)
        else:
            return 0
    except PineconeException as e:
        logging.error(f"Pinecone error updating drive link for {file_name}: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"Failed to update drive link for {file_name}: {str(e)}")
        raise
