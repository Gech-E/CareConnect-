"""S3-compatible object storage client for document management."""

from typing import Any

import boto3
from botocore.config import Config as BotoConfig

from app.core import get_settings

settings = get_settings()


def get_s3_client() -> Any:
    """Return a configured boto3 S3 client for MinIO/S3."""
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        aws_access_key_id=settings.S3_ACCESS_KEY_ID,
        aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
        region_name=settings.S3_REGION,
        config=BotoConfig(signature_version="s3v4"),
    )


def generate_presigned_upload_url(
    key: str,
    content_type: str,
    expiry: int | None = None,
) -> str:
    """Generate a presigned URL for uploading a document."""
    client = get_s3_client()
    return client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.S3_BUCKET_NAME,
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=expiry or settings.S3_PRESIGNED_URL_EXPIRY,
    )


def generate_presigned_download_url(
    key: str,
    expiry: int | None = None,
) -> str:
    """Generate a presigned URL for downloading a document."""
    client = get_s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": settings.S3_BUCKET_NAME,
            "Key": key,
        },
        ExpiresIn=expiry or settings.S3_PRESIGNED_URL_EXPIRY,
    )


def ensure_bucket_exists() -> None:
    """Create the documents bucket if it doesn't exist (local dev)."""
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=settings.S3_BUCKET_NAME)
    except client.exceptions.ClientError:
        client.create_bucket(Bucket=settings.S3_BUCKET_NAME)
