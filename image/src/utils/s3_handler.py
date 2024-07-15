import boto3
from io import BytesIO
from utils.config import TEACHER_CONFIG, S3_BUCKET

s3 = boto3.client("s3")


def get_s3_buckets():
    response = s3.list_buckets()
    return response


def get_pdf_from_s3(pdf_key, teacher_name):
    config = TEACHER_CONFIG.get(teacher_name)
    if not config:
        raise ValueError(f"Invalid teacher name: {teacher_name}")

    s3_prefix = config["s3_prefix"]
    response = s3.get_object(Bucket=S3_BUCKET, Key=f"{s3_prefix}{pdf_key}")
    pdf_content = response["Body"].read()
    return BytesIO(pdf_content)


def list_pdfs_in_s3(teacher_name):
    config = TEACHER_CONFIG.get(teacher_name)
    if not config:
        raise ValueError(f"Error s3_handler, Invalid teacher name: {teacher_name}")

    s3_prefix = config["s3_prefix"]
    response = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=s3_prefix)
    return [
        obj["Key"]
        for obj in response.get("Contents", [])
        if obj["Key"].lower().endswith(".pdf")
    ]
