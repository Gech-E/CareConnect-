"""S3-compatible object storage client for document management."""

import asyncio
from functools import lru_cache
from typing import Any

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

from app.core import get_settings
from app.core.exceptions import AppError

settings = get_settings()


@lru_cache
def get_s3_client() -> Any:
    """Return a configured boto3 S3 client for MinIO/S3."""
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        aws_access_key_id=settings.S3_ACCESS_KEY_ID,
        aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
        region_name=settings.S3_REGION,
        config=BotoConfig(
            signature_version="s3v4",
            connect_timeout=3,
            read_timeout=3,
            retries={"max_attempts": 1, "mode": "standard"},
        ),
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
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") not in {"404", "NoSuchBucket"}:
            raise
        kwargs: dict[str, Any] = {"Bucket": settings.S3_BUCKET_NAME}
        if settings.S3_REGION != "us-east-1":
            kwargs["CreateBucketConfiguration"] = {"LocationConstraint": settings.S3_REGION}
        client.create_bucket(**kwargs)


async def inspect_uploaded_object(key: str, expected_content_type: str) -> int:
    """Verify stored metadata; this is not a substitute for a trusted malware scan."""
    try:
        metadata = await asyncio.to_thread(
            get_s3_client().head_object, Bucket=settings.S3_BUCKET_NAME, Key=key
        )
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}:
            raise AppError(
                "UPLOAD_NOT_FOUND", "Upload the document before completing it.", 409
            ) from exc
        raise AppError(
            "STORAGE_UNAVAILABLE", "Document storage is temporarily unavailable.", 503
        ) from exc
    size = metadata.get("ContentLength", 0)
    if not isinstance(size, int) or not 0 < size <= settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise AppError(
            "INVALID_UPLOAD_SIZE", "The uploaded file exceeds the allowed size or is empty.", 422
        )
    if metadata.get("ContentType") != expected_content_type:
        raise AppError("INVALID_UPLOAD_TYPE", "The uploaded file content type does not match.", 422)
    return size
