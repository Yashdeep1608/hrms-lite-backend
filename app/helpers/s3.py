import boto3
import os
from dotenv import load_dotenv
from uuid import uuid4

from fastapi import UploadFile

load_dotenv()

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_BUCKET_NAME = os.getenv("AWS_S3_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_S3_REGION")

s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION
)

def upload_file_to_s3(upload_file: UploadFile, filename: str = None, folder: str = "uploads"):
    if not filename:
        filename = f"{uuid4().hex}.jpg"  # fallback filename

    s3_key = f"{folder}/{filename}"

    s3_client.upload_fileobj(
        Fileobj=upload_file.file,  # the actual file object
        Bucket=AWS_BUCKET_NAME,
        Key=s3_key,
        ExtraArgs={
            "ContentType": upload_file.content_type  # from UploadFile, not file object
        }
    )

    return f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"

