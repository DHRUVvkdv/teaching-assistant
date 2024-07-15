import os
from fastapi import HTTPException
from pinecone import Pinecone, ServerlessSpec
from models.query import QueryModel
from utils.embeddings import get_embedding_function
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


dynamodb = boto3.resource("dynamodb")
processedFilesTable = dynamodb.Table(PROCESSED_FILES_TABLE)
queriesTable = dynamodb.Table(QUERIES_TABLE)

pc = Pinecone(api_key=PINECONE_API_KEY)


def list_processed_files(teacher_name):
    try:
        response = processedFilesTable.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr("teacher").eq(teacher_name)
        )
        processed_files = [item["filename"] for item in response["Items"]]
        return processed_files
    except ClientError as e:
        logging.error(
            f"Failed to list processed files from DynamoDB for teacher {teacher_name}: {str(e)}"
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to list processed files: {str(e)}"
        )


def create_embeddings(sentences, teacher_name):
    try:
        config = TEACHER_CONFIG.get(teacher_name)
        if not config:
            raise ValueError(f"Invalid teacher name: {teacher_name}")

        embedding_function = get_embedding_function()
        embedding_vectors = embedding_function.embed_documents(sentences)

        index = pc.Index(config["index_name"])

        vectors_to_upsert = []
        for i, (text, vector) in enumerate(zip(sentences, embedding_vectors)):
            vectors_to_upsert.append(
                (f"vec_{i}", vector, {"text": text, "teacher": teacher_name})
            )

        index.upsert(vectors=vectors_to_upsert)

        return {
            "status": "success",
            "message": f"Added {len(sentences)} embeddings to Pinecone for teacher {teacher_name}",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create embeddings: {str(e)}"
        )


def query_pinecone(query_text, teacher_name):
    try:
        config = TEACHER_CONFIG.get(teacher_name)
        if not config:
            raise ValueError(f"Invalid teacher name: {teacher_name}")

        index_name = config["index_name"]
        top_k = config["top_k"]

        query_id = uuid.uuid4().hex
        create_time = int(time.time())

        index = pc.Index(index_name)
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

        sources = [
            f"{match.metadata['source']} (Page {match.metadata.get('page', 'N/A')}) - {match.metadata.get('google_drive_link', 'No link available')}"
            for match in results.matches
        ]

        new_query = QueryModel(
            query_id=query_id,
            create_time=create_time,
            query_text=query_text,
            answer_text=response_text,
            sources=sources,
            is_complete=True,
        )

        # Add query info to DynamoDB
        queriesTable.put_item(
            Item={
                "query_id": query_id,
                "create_time": create_time,
                "query_text": query_text,
                "answer_text": response_text,
                "sources": sources,
                "is_complete": True,
                "pinecone_index": index_name,
                "teacher": teacher_name,
            }
        )

        logging.info(
            f"Query processed and added to DynamoDB: {query_id} for teacher {teacher_name}"
        )

        return new_query
    except Exception as e:
        logging.error(
            f"Failed to process query or add to DynamoDB for teacher {teacher_name}: {str(e)}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process query or add to DynamoDB: {str(e)}",
        )


def process_pdf_file(pdf_key, teacher_name):
    try:
        config = TEACHER_CONFIG.get(teacher_name)
        if not config:
            raise ValueError(f"Invalid teacher name: {teacher_name}")

        index_name = config["index_name"]
        s3_prefix = config["s3_prefix"]

        # We don't need to add s3_prefix here as it's handled in get_pdf_from_s3
        pdf_content = get_pdf_from_s3(pdf_key, teacher_name)
        chunks = process_pdf(pdf_content, pdf_key)

        index = pc.Index(index_name)
        embedding_function = get_embedding_function()

        google_drive_link = get_google_drive_link_pdf(pdf_key)

        vectors_to_upsert = []
        for chunk in chunks:
            embedding = embedding_function.embed_query(chunk.page_content)
            metadata = chunk.metadata.copy()
            metadata.update(
                {
                    "text": chunk.page_content,
                    "google_drive_link": google_drive_link,
                    "processed_date": int(time.time()),
                    "teacher": teacher_name,
                }
            )
            vectors_to_upsert.append((metadata["id"], embedding, metadata))

        index.upsert(vectors=vectors_to_upsert)
        add_processed_file_dynamodb(pdf_key, teacher_name)
        return len(chunks)
    except Exception as e:
        logging.error(
            f"Failed to process PDF {pdf_key} for teacher {teacher_name}: {str(e)}"
        )
        return 0


def process_all_pdfs(teacher_name):
    try:
        config = TEACHER_CONFIG.get(teacher_name)
        if not config:
            raise ValueError(f"Invalid teacher name: {teacher_name}")

        s3_prefix = config["s3_prefix"]
        available_pdfs = list_pdfs_in_s3(teacher_name)
        processed_files = list_processed_files(teacher_name)

        total_chunks_added = 0
        newly_processed_files = 0
        already_processed_files = len(processed_files)
        newly_processed_file_details = []
        failed_files = []

        for pdf_key in available_pdfs:
            pdf_name = pdf_key.split("/")[-1]
            if pdf_name not in processed_files:
                chunks_added = process_pdf_file(pdf_name, teacher_name)
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
            "message": f"Processed {newly_processed_files} new PDF files and added {total_chunks_added} chunks to Pinecone for teacher {teacher_name}.",
            "details": {
                "already_processed_files": already_processed_files,
                "newly_processed_files": newly_processed_files,
                "total_chunks_added": total_chunks_added,
                "newly_processed_file_details": newly_processed_file_details,
                "failed_files": failed_files,
            },
        }

    except Exception as e:
        logging.error(f"Failed to process PDFs for teacher {teacher_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process PDFs: {str(e)}")


def list_processed_files(teacher_name):
    try:
        dynamodb = boto3.resource("dynamodb")
        processedFilesTable = dynamodb.Table(
            "teaching-assistant-tavily-processed-files"
        )

        response = processedFilesTable.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr("teacher").eq(teacher_name)
        )

        processed_files = [item["filename"] for item in response["Items"]]

        return processed_files
    except ClientError as e:
        logging.error(
            f"Failed to list processed files from DynamoDB for teacher {teacher_name}: {str(e)}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list processed files for teacher {teacher_name}: {str(e)}",
        )


def add_processed_file_dynamodb(filename, teacher_name):
    try:
        config = TEACHER_CONFIG.get(teacher_name)
        if not config:
            raise ValueError(f"Invalid teacher name: {teacher_name}")

        processedFilesTable.put_item(
            Item={
                "filename": filename,
                "index_name": config["index_name"],
                "teacher": teacher_name,
            }
        )
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


def update_missing_drive_links(teacher_name):
    config = TEACHER_CONFIG.get(teacher_name)
    if not config:
        raise ValueError(f"Invalid teacher name: {teacher_name}")

    index = pc.Index(config["index_name"])

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


def update_drive_link_for_file(file_name: str, drive_link: str, teacher_name: str):
    try:
        config = TEACHER_CONFIG.get(teacher_name)
        if not config:
            raise ValueError(f"Invalid teacher name: {teacher_name}")

        index = pc.Index(config["index_name"])

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


def combined_query(query_text, teacher_name, tavily_client):
    try:
        query_id = uuid.uuid4().hex
        create_time = int(time.time())

        # Query Pinecone
        pinecone_results = query_pinecone(query_text, teacher_name)

        # Query Tavily
        tavily_results = tavily_client.get_search_context(
            query=query_text,
            search_depth="advanced",
            max_tokens=2000,  # Adjust as needed
        )

        # Prepare the combined prompt
        prompt_template = ChatPromptTemplate.from_template(COMBINED_PROMPT_TEMPLATE)
        prompt = prompt_template.format(
            professor_context=pinecone_results.answer_text,
            professor_sources="\n".join(pinecone_results.sources),
            web_context=tavily_results,
            question=query_text,
        )

        # Get response from LLM
        model = ChatBedrock(model_id=BEDROCK_MODEL_ID)
        response = model.invoke(prompt)
        combined_response = response.content

        # Prepare the result
        result = {
            "query_id": query_id,
            "create_time": create_time,
            "query_text": query_text,
            "professor_answer": pinecone_results.answer_text,
            "professor_sources": pinecone_results.sources,
            "web_context": tavily_results,
            "combined_response": combined_response,
            "teacher": teacher_name,
            "status": "completed",
        }

        # Add query info to DynamoDB
        queriesTable.put_item(Item=result)

        logging.info(
            f"Combined query processed and added to DynamoDB: {query_id} for teacher {teacher_name}"
        )

        return result
    except Exception as e:
        logging.error(
            f"Failed to process combined query for teacher {teacher_name}: {str(e)}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process combined query: {str(e)}",
        )
