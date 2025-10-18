"""Test API endpoints."""

from fastapi.testclient import TestClient

from football_rag.api.app import app


def test_health_endpoint():
    """Test /health endpoint returns 200."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "football-rag-intelligence"


def test_metrics_endpoint():
    """Test /metrics endpoint returns metrics."""
    client = TestClient(app)
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "total_requests" in data
    assert "total_errors" in data
    assert "p50_ms" in data
    assert "p95_ms" in data


def test_health_has_request_id():
    """Test that responses include X-Request-ID header."""
    client = TestClient(app)
    response = client.get("/health")
    assert "x-request-id" in response.headers
