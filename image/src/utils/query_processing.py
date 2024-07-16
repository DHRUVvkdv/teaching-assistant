# utils/query_processing.py

from langchain_aws import ChatBedrock
from utils.config import BEDROCK_MODEL_ID


def process_query(query_text, teacher_name, prompt_template, additional_params=None):
    prompt_params = {"question": query_text}
    if additional_params:
        prompt_params.update(additional_params)

    prompt = prompt_template.format(**prompt_params)

    model = ChatBedrock(model_id=BEDROCK_MODEL_ID)
    response = model.invoke(prompt)
    return response.content
