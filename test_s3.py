
import boto3

s3 = boto3.client(
    "s3",
    endpoint_url="http://host.docker.internal:4566",
    aws_access_key_id="floci",
    aws_secret_access_key="floci",
    region_name="us-east-1",
)

bucket = "talentmatch-resumes-local"
key = "tests/connection-test.txt"

s3.put_object(
    Bucket=bucket,
    Key=key,
    Body=b"TalentMatch S3 connection successful!",
    ContentType="text/plain",
)

response = s3.get_object(Bucket=bucket, Key=key)
print(response["Body"].read().decode("utf-8"))
