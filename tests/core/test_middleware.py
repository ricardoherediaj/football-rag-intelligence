"""Tests for observability middleware."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from football_rag.core.middleware import ObservabilityMiddleware
from football_rag.core.metrics import metrics


@pytest.fixture
def app():
    """Create a test FastAPI app with middleware."""
    test_app = FastAPI()
    test_app.add_middleware(ObservabilityMiddleware)

    @test_app.get("/test")
    async def test_endpoint():
        return {"message": "ok"}

    @test_app.get("/error")
    async def error_endpoint():
        raise ValueError("Test error")

    return test_app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app, raise_server_exceptions=False)


def test_middleware_adds_request_id(client):
    """Test that middleware adds X-Request-ID to response."""
    response = client.get("/test")
    assert "x-request-id" in response.headers
    assert len(response.headers["x-request-id"]) > 0


def test_middleware_preserves_provided_request_id(client):
    """Test that middleware preserves X-Request-ID from request."""
    request_id = "test-123-456"
    response = client.get("/test", headers={"X-Request-ID": request_id})
    assert response.headers["x-request-id"] == request_id


def test_middleware_increments_request_count(client):
    """Test that middleware increments request counter."""
    initial_count = metrics.total_requests
    client.get("/test")
    assert metrics.total_requests == initial_count + 1


def test_middleware_records_latency(client):
    """Test that middleware records request latency."""
    initial_latencies = len(metrics._latencies)
    client.get("/test")
    assert len(metrics._latencies) == initial_latencies + 1
    assert metrics._latencies[-1] >= 0


def test_middleware_handles_errors_gracefully(client):
    """Test that middleware doesn't crash on errors."""
    initial_count = metrics.total_requests
    response = client.get("/error")
    assert response.status_code == 500
    assert metrics.total_requests == initial_count + 1
