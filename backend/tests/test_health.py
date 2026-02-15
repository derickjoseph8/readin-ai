"""Tests for health check endpoints."""

import pytest


class TestHealthCheck:
    """Test health check endpoints."""

    def test_health_basic(self, client):
        """Test basic health endpoint returns OK."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "checks" in data

    def test_health_detailed(self, client):
        """Test detailed health check."""
        response = client.get("/health?detailed=true")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
        assert "checks" in data
        assert "database" in data["checks"]

    def test_health_minimal(self, client):
        """Test minimal health check (for load balancers)."""
        response = client.get("/health?detailed=false")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "version" in data

    def test_liveness_probe(self, client):
        """Test Kubernetes liveness probe."""
        response = client.get("/health/live")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "alive"

    def test_readiness_probe(self, client):
        """Test Kubernetes readiness probe."""
        response = client.get("/health/ready")
        # May be 200 or 503 depending on database state
        assert response.status_code in [200, 503]

        data = response.json()
        assert "status" in data

    def test_health_includes_request_id(self, client):
        """Test that health check includes request ID."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "request_id" in data
