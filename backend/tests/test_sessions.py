"""Tests for session management endpoints."""

import pytest
from datetime import datetime, timedelta


class TestSessions:
    """Test session management endpoints."""

    def test_get_sessions_unauthenticated(self, client):
        """Test that unauthenticated requests are rejected."""
        response = client.get("/api/v1/sessions")
        assert response.status_code == 401

    def test_get_sessions_empty(self, client, auth_headers):
        """Test getting sessions when none exist."""
        response = client.get("/api/v1/sessions", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert "sessions" in data
        assert "total_active" in data

    def test_get_current_session(self, client, auth_headers):
        """Test getting current session info."""
        response = client.get("/api/v1/sessions/current", headers=auth_headers)
        assert response.status_code == 200

    def test_revoke_nonexistent_session(self, client, auth_headers):
        """Test revoking a session that doesn't exist."""
        response = client.post("/api/v1/sessions/99999/revoke", headers=auth_headers)
        assert response.status_code == 404

    def test_revoke_all_sessions(self, client, auth_headers):
        """Test revoking all sessions."""
        response = client.post(
            "/api/v1/sessions/revoke-all",
            params={"keep_current": True},
            headers=auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert "revoked_count" in data
        assert "message" in data
