import boto3
import os
from io import BytesIO

S3_BUCKET = os.environ.get("S3_BUCKET", "teaching-assistant-tavily")
PDF_PREFIX = "data/pdfs/"

s3 = boto3.client("s3")


def get_s3_buckets():
    response = s3.list_buckets()
    return response


def get_pdf_from_s3(pdf_key):
    response = s3.get_object(Bucket=S3_BUCKET, Key=f"{PDF_PREFIX}{pdf_key}")
    pdf_content = response["Body"].read()
    return BytesIO(pdf_content)


def list_pdfs_in_s3():
    response = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=PDF_PREFIX)
    return [
        obj["Key"]
        for obj in response.get("Contents", [])
        if obj["Key"].lower().endswith(".pdf")
    ]
