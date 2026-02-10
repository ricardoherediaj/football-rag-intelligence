"""MinIO client wrapper using boto3 for S3-compatible object storage."""

import json
import logging

import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

DEFAULT_ENDPOINT = "http://localhost:9000"
DEFAULT_ACCESS_KEY = "admin"
DEFAULT_SECRET_KEY = "password123"
DEFAULT_BUCKET = "football-raw"


class MinIOClient:
    """Thin wrapper around boto3 S3 client for MinIO operations."""

    def __init__(
        self,
        endpoint: str = DEFAULT_ENDPOINT,
        access_key: str = DEFAULT_ACCESS_KEY,
        secret_key: str = DEFAULT_SECRET_KEY,
    ):
        self.s3 = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=BotoConfig(signature_version="s3v4"),
        )

    def ensure_bucket(self, bucket: str) -> None:
        """Create bucket if it doesn't exist."""
        try:
            self.s3.head_bucket(Bucket=bucket)
        except ClientError:
            self.s3.create_bucket(Bucket=bucket)
            logger.info(f"Created bucket: {bucket}")

    def upload_json(self, bucket: str, key: str, data: dict) -> None:
        """Upload a dict as a JSON object."""
        body = json.dumps(data).encode("utf-8")
        self.s3.put_object(
            Bucket=bucket, Key=key, Body=body,
            ContentLength=len(body), ContentType="application/json",
        )

    def upload_raw(self, bucket: str, key: str, raw: str) -> None:
        """Upload a raw string (preserves original formatting)."""
        body = raw.encode("utf-8")
        self.s3.put_object(
            Bucket=bucket, Key=key, Body=body,
            ContentLength=len(body), ContentType="application/json",
        )

    def download_json(self, bucket: str, key: str) -> dict:
        """Download a JSON object and return as dict."""
        response = self.s3.get_object(Bucket=bucket, Key=key)
        return json.loads(response["Body"].read().decode("utf-8"))

    def list_objects(self, bucket: str, prefix: str = "") -> list[str]:
        """List all object keys under a prefix."""
        keys: list[str] = []
        paginator = self.s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                keys.append(obj["Key"])
        return keys

    def download_raw(self, bucket: str, key: str) -> str:
        """Download an object and return raw string (for NaN sanitization)."""
        response = self.s3.get_object(Bucket=bucket, Key=key)
        return response["Body"].read().decode("utf-8")
