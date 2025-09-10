"""
MinIO S3-compatible storage client.
"""

from minio import Minio
from typing import BinaryIO


class MinIOClient:
    """Simple MinIO wrapper for S3-compatible storage."""
    
    def __init__(self, endpoint: str = "localhost:9000", access_key: str = "minioadmin", secret_key: str = "minioadmin"):
        self.client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=False)
        self.bucket_name = "football-data"
        self._ensure_bucket()
    
    def _ensure_bucket(self):
        """Create bucket if it doesn't exist."""
        if not self.client.bucket_exists(self.bucket_name):
            self.client.make_bucket(self.bucket_name)
    
    def upload_file(self, object_name: str, file_data: BinaryIO, length: int):
        """Upload file to MinIO."""
        return self.client.put_object(self.bucket_name, object_name, file_data, length)
    
    def download_file(self, object_name: str):
        """Download file from MinIO."""
        return self.client.get_object(self.bucket_name, object_name)