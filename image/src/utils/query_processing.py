# utils/query_processing.py

import uuid
import time
import logging
from langchain.prompts import ChatPromptTemplate
from langchain_aws import ChatBedrock
from utils.config import TEACHER_CONFIG, BEDROCK_MODEL_ID


def process_query(
    query_text,
    teacher_name,
    context,
    prompt_template,
    additional_params=None,
    queriesTable=None,
):
    query_id = uuid.uuid4().hex
    create_time = int(time.time())

    prompt_params = {"context": context, "question": query_text}
    if additional_params:
        prompt_params.update(additional_params)

    prompt = prompt_template.format(**prompt_params)

    model = ChatBedrock(model_id=BEDROCK_MODEL_ID)
    response = model.invoke(prompt)
    response_text = response.content

    result = {
        "query_id": query_id,
        "create_time": create_time,
        "query_text": query_text,
        "answer_text": response_text,
        "is_complete": True,
        "pinecone_index": TEACHER_CONFIG[teacher_name]["index_name"],
        "teacher": teacher_name,
        "prompt": prompt,
    }

    # Add query info to DynamoDB if table is provided
    if queriesTable:
        queriesTable.put_item(Item=result)

    logging.info(
        f"Query processed and added to DynamoDB: {query_id} for teacher {teacher_name}"
    )

    return result
