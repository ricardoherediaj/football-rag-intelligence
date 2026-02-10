"""Tests for MinIO client wrapper."""

from unittest.mock import MagicMock, patch

import pytest

from football_rag.storage.minio_client import MinIOClient


@pytest.fixture
def mock_s3():
    with patch("football_rag.storage.minio_client.boto3") as mock_boto:
        mock_client = MagicMock()
        mock_boto.client.return_value = mock_client
        yield mock_client


def test_ensure_bucket_creates_when_missing(mock_s3):
    from botocore.exceptions import ClientError

    mock_s3.head_bucket.side_effect = ClientError(
        {"Error": {"Code": "404"}}, "HeadBucket"
    )
    client = MinIOClient()
    client.ensure_bucket("test-bucket")
    mock_s3.create_bucket.assert_called_once_with(Bucket="test-bucket")


def test_ensure_bucket_skips_when_exists(mock_s3):
    client = MinIOClient()
    client.ensure_bucket("test-bucket")
    mock_s3.head_bucket.assert_called_once_with(Bucket="test-bucket")
    mock_s3.create_bucket.assert_not_called()


def test_upload_json(mock_s3):
    client = MinIOClient()
    client.upload_json("bucket", "key.json", {"id": 1})
    mock_s3.put_object.assert_called_once()
    call_kwargs = mock_s3.put_object.call_args[1]
    assert call_kwargs["Bucket"] == "bucket"
    assert call_kwargs["Key"] == "key.json"
    assert b'"id": 1' in call_kwargs["Body"]


def test_download_json(mock_s3):
    mock_body = MagicMock()
    mock_body.read.return_value = b'{"id": 42}'
    mock_s3.get_object.return_value = {"Body": mock_body}

    client = MinIOClient()
    result = client.download_json("bucket", "key.json")
    assert result == {"id": 42}


def test_list_objects(mock_s3):
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [
        {"Contents": [{"Key": "a.json"}, {"Key": "b.json"}]}
    ]
    mock_s3.get_paginator.return_value = mock_paginator

    client = MinIOClient()
    keys = client.list_objects("bucket", prefix="ws/")
    assert keys == ["a.json", "b.json"]


def test_download_raw(mock_s3):
    mock_body = MagicMock()
    mock_body.read.return_value = b'{"value": NaN}'
    mock_s3.get_object.return_value = {"Body": mock_body}

    client = MinIOClient()
    raw = client.download_raw("bucket", "key.json")
    assert raw == '{"value": NaN}'


def test_upload_raw(mock_s3):
    client = MinIOClient()
    client.upload_raw("bucket", "key.json", '{"value": NaN}')
    mock_s3.put_object.assert_called_once()
    call_kwargs = mock_s3.put_object.call_args[1]
    assert call_kwargs["Body"] == b'{"value": NaN}'
