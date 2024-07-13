from typing import List
import PyPDF2
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.schema.document import Document


def process_pdf(pdf_file: bytes, filename: str) -> List[Document]:
    """
    Process a PDF file and return a list of document chunks.

    Args:
        pdf_file (bytes): The PDF file content.
        filename (str): The name of the PDF file.

    Returns:
        List[Document]: A list of document chunks.
    """
    pdf_reader = PyPDF2.PdfReader(pdf_file)

    documents = [
        Document(
            page_content=page.extract_text(),
            metadata={"page": page_num + 1, "source": filename},
        )
        for page_num, page in enumerate(pdf_reader.pages)
    ]

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=120,
        length_function=len,
        is_separator_regex=False,
    )
    chunks = text_splitter.split_documents(documents)

    return calculate_chunk_ids(chunks, filename)


def calculate_chunk_ids(chunks: List[Document], filename: str) -> List[Document]:
    """
    Calculate and assign unique IDs to document chunks.

    Args:
        chunks (List[Document]): List of document chunks.
        filename (str): The name of the source file.

    Returns:
        List[Document]: Updated list of document chunks with IDs.
    """
    last_page_id = None
    current_chunk_index = 0

    for chunk in chunks:
        page = chunk.metadata.get("page", 0)
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
