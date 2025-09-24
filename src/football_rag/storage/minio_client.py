"""
MinIO S3-compatible storage client.
"""

import json
import io
from minio import Minio
from typing import BinaryIO, List, Set, Dict, Any


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

    def upload_json(self, object_name: str, data: Dict[str, Any]) -> None:
        """Upload JSON data to MinIO.

        Args:
            object_name: Path in MinIO (e.g., 'whoscored/eredivisie/2025-2026/match_123.json')
            data: Dictionary to upload as JSON
        """
        json_bytes = json.dumps(data, indent=2).encode('utf-8')
        json_stream = io.BytesIO(json_bytes)

        self.client.put_object(
            self.bucket_name,
            object_name,
            json_stream,
            length=len(json_bytes),
            content_type='application/json'
        )

    def list_objects(self, prefix: str) -> List[str]:
        """List all objects with given prefix.

        Args:
            prefix: Path prefix (e.g., 'whoscored/eredivisie/2025-2026/')

        Returns:
            List of object names
        """
        objects = self.client.list_objects(self.bucket_name, prefix=prefix, recursive=True)
        return [obj.object_name for obj in objects]

    def get_scraped_match_ids(self, prefix: str) -> Set[str]:
        """Extract match IDs from filenames in MinIO.

        Args:
            prefix: Path prefix (e.g., 'whoscored/eredivisie/2025-2026/')

        Returns:
            Set of match IDs already scraped
        """
        files = self.list_objects(prefix)
        match_ids = set()

        for filename in files:
            if 'match_' in filename:
                match_id = filename.split('match_')[1].split('.json')[0]
                match_ids.add(match_id)

        return match_ids

    def match_exists(self, prefix: str, match_id: str) -> bool:
        """Check if a match has already been scraped.

        Args:
            prefix: Path prefix (e.g., 'whoscored/eredivisie/2025-2026/')
            match_id: Match ID to check

        Returns:
            True if match exists in MinIO
        """
        object_name = f"{prefix}match_{match_id}.json"
        try:
            self.client.stat_object(self.bucket_name, object_name)
            return True
        except Exception:
            return False