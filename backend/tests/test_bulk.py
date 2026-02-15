"""Tests for bulk operation endpoints."""

import pytest
from datetime import datetime


class TestBulkOperations:
    """Test bulk operation endpoints."""

    def test_bulk_delete_unauthenticated(self, client):
        """Test that bulk operations require authentication."""
        response = client.post(
            "/api/v1/bulk/meetings/delete",
            json={"ids": [1, 2, 3]},
        )
        assert response.status_code == 401

    def test_bulk_delete_meetings_empty(self, client, auth_headers):
        """Test bulk delete with non-existent IDs."""
        response = client.post(
            "/api/v1/bulk/meetings/delete",
            json={"ids": [99999, 99998]},
            headers=auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["success_count"] == 0
        assert data["failure_count"] == 2
        assert len(data["errors"]) == 2

    def test_bulk_delete_meetings_valid(self, client, auth_headers, test_meeting, test_db):
        """Test bulk delete with valid meeting ID."""
        meeting_id = test_meeting.id

        response = client.post(
            "/api/v1/bulk/meetings/delete",
            json={"ids": [meeting_id]},
            headers=auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["success_count"] == 1
        assert data["failure_count"] == 0

    def test_bulk_export_meetings(self, client, auth_headers, completed_meeting):
        """Test bulk export meetings."""
        response = client.post(
            "/api/v1/bulk/meetings/export",
            json={
                "format": "json",
                "include_conversations": True,
                "include_action_items": True,
            },
            headers=auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert "meetings" in data
        assert "count" in data
        assert "exported_at" in data

    def test_bulk_export_csv(self, client, auth_headers, completed_meeting):
        """Test bulk export in CSV format."""
        response = client.post(
            "/api/v1/bulk/meetings/export",
            json={"format": "csv"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")

    def test_bulk_update_task_status_invalid(self, client, auth_headers):
        """Test bulk update with invalid status."""
        response = client.post(
            "/api/v1/bulk/tasks/update-status",
            json={"ids": [1], "status": "invalid_status"},
            headers=auth_headers,
        )
        assert response.status_code == 400

    def test_bulk_delete_tasks_empty(self, client, auth_headers):
        """Test bulk delete tasks with no valid IDs."""
        response = client.post(
            "/api/v1/bulk/tasks/delete",
            json={"ids": [99999]},
            headers=auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["success_count"] == 0
        assert data["failure_count"] == 1

    def test_bulk_request_too_many_ids(self, client, auth_headers):
        """Test that bulk requests are limited to 100 items."""
        # Generate 101 IDs
        ids = list(range(1, 102))

        response = client.post(
            "/api/v1/bulk/meetings/delete",
            json={"ids": ids},
            headers=auth_headers,
        )
        assert response.status_code == 422  # Validation error
