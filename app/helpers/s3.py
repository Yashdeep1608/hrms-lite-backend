from datetime import datetime, timezone
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

def determine_file_category(content_type: str) -> str:
    if content_type.startswith("image/"):
        return "image"
    elif content_type.startswith("video/"):
        return "video"
    elif content_type == "application/pdf":
        return "pdf"
    elif content_type in ["text/csv"]:
        return "csv"
    elif content_type.startswith("application/"):
        return "document"
    else:
        return "others"

def upload_file_to_s3(upload_file: UploadFile, filename: str = None, folder: str = "uploads"):
    content_type = upload_file.content_type
    file_category = determine_file_category(content_type)

    # Get the file extension safely
    extension = os.path.splitext(upload_file.filename)[1] or ""

    # Generate filename using timestamp
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    generated_filename = f"{timestamp}{extension}"

    # Final path in S3: category/timestamp.ext
    s3_key = f"{file_category}/{generated_filename}"

    s3_client.upload_fileobj(
        Fileobj=upload_file.file,
        Bucket=AWS_BUCKET_NAME,
        Key=s3_key,
        ExtraArgs={
            "ContentType": content_type
        }
    )

    return f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"

