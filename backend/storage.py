import os
import boto3

s3 = boto3.client("s3", endpoint_url=os.getenv("AWS_ENDPOINT_URL") or None,
                  region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
BUCKET = os.getenv("S3_BUCKET_NAME", "talentmatch-resumes-local")

def upload_resume(pdf_bytes: bytes, object_key: str) -> None:
    s3.put_object(Bucket=BUCKET, Key=object_key, Body=pdf_bytes, ContentType="application/pdf")

def download_resume(object_key: str) -> bytes:
    response = s3.get_object(Bucket=BUCKET, Key=object_key)
    body = response["Body"]
    try:
        return body.read()
    finally:
        body.close()
