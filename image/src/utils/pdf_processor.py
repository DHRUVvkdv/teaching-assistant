from typing import List
import PyPDF2
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.schema.document import Document
from utils.config import PDF_CHUNK_SIZE, PDF_CHUNK_OVERLAP
import logging


def process_pdf(pdf_file: bytes, filename: str) -> List[Document]:
    """
    Process a PDF file and return a list of document chunks.

    Args:
        pdf_file (bytes): The PDF file content.
        filename (str): The name of the PDF file.

    Returns:
        List[Document]: A list of document chunks.
    """
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)

        documents = []
        for page_num, page in enumerate(pdf_reader.pages):
            try:
                text = page.extract_text()
                if text:  # Only create a Document if there's text content
                    documents.append(
                        Document(
                            page_content=text,
                            metadata={"page": page_num + 1, "source": filename},
                        )
                    )
            except Exception as e:
                logging.error(
                    f"Error extracting text from page {page_num + 1} of {filename}: {str(e)}"
                )

        if not documents:
            logging.warning(f"No text content extracted from {filename}")
            return []

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=PDF_CHUNK_SIZE,
            chunk_overlap=PDF_CHUNK_OVERLAP,
            length_function=len,
            is_separator_regex=False,
        )
        chunks = text_splitter.split_documents(documents)

        return calculate_chunk_ids(chunks, filename)
    except Exception as e:
        logging.error(f"Error processing PDF {filename}: {str(e)}")
        raise


def calculate_chunk_ids(chunks: List[Document], filename: str) -> List[Document]:
    """
    Calculate and assign unique IDs to document chunks.

    Args:
        chunks (List[Document]): List of document chunks.
        filename (str): The name of the source file.

    Returns:
        List[Document]: Updated list of document chunks with IDs.
    """
    try:
        last_page_id = None
        current_chunk_index = 0

        for chunk in chunks:
            page = chunk.metadata.get("page", 0)
            if not isinstance(page, int):
                logging.warning(
                    f"Non-integer page value found in {filename}: {page}. Using 0."
                )
                page = 0

            current_page_id = f"{filename}:{page}"

            if current_page_id == last_page_id:
                current_chunk_index += 1
            else:
                current_chunk_index = 0

            chunk_id = f"{current_page_id}:{current_chunk_index}"
            last_page_id = current_page_id

            chunk.metadata["id"] = chunk_id
            chunk.metadata["source"] = filename

        return chunks
    except Exception as e:
        logging.error(f"Error calculating chunk IDs for {filename}: {str(e)}")
        raise
