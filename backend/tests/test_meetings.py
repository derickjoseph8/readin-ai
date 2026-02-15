"""
Meeting API tests for ReadIn AI backend.

Tests:
- Meeting creation
- Meeting retrieval
- Meeting updates
- Meeting list and filtering
- Authorization checks
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient


class TestMeetingCreation:
    """Test meeting creation endpoint."""

    def test_create_meeting_success(self, client: TestClient, auth_headers):
        """Test successful meeting creation."""
        response = client.post(
            "/meetings/",
            headers=auth_headers,
            json={
                "meeting_type": "interview",
                "title": "Product Manager Interview",
                "meeting_app": "Zoom",
                "participant_count": 3,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["meeting_type"] == "interview"
        assert data["title"] == "Product Manager Interview"
        assert data["status"] == "active"
        assert "id" in data

    def test_create_meeting_minimal(self, client: TestClient, auth_headers):
        """Test meeting creation with minimal data."""
        response = client.post(
            "/meetings/",
            headers=auth_headers,
            json={},  # All fields are optional
        )
        assert response.status_code == 200
        data = response.json()
        assert data["meeting_type"] == "general"  # Default value
        assert data["status"] == "active"

    def test_create_meeting_invalid_type(self, client: TestClient, auth_headers):
        """Test meeting creation with invalid type fails."""
        response = client.post(
            "/meetings/",
            headers=auth_headers,
            json={
                "meeting_type": "invalid_type",
            },
        )
        assert response.status_code == 422  # Validation error

    def test_create_meeting_unauthorized(self, client: TestClient):
        """Test meeting creation without auth fails."""
        response = client.post(
            "/meetings/",
            json={"title": "Unauthorized Meeting"},
        )
        assert response.status_code == 401


class TestMeetingRetrieval:
    """Test meeting retrieval endpoints."""

    def test_get_meeting_by_id(
        self, client: TestClient, auth_headers, test_meeting
    ):
        """Test getting a meeting by ID."""
        response = client.get(
            f"/meetings/{test_meeting.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_meeting.id
        assert data["title"] == test_meeting.title

    def test_get_meeting_not_found(self, client: TestClient, auth_headers):
        """Test getting non-existent meeting returns 404."""
        response = client.get(
            "/meetings/99999",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_get_meeting_unauthorized_user(
        self, client: TestClient, premium_auth_headers, test_meeting
    ):
        """Test user cannot access another user's meeting."""
        response = client.get(
            f"/meetings/{test_meeting.id}",
            headers=premium_auth_headers,  # Different user
        )
        assert response.status_code == 404  # Should look like not found

    def test_get_active_meeting(
        self, client: TestClient, auth_headers, test_meeting
    ):
        """Test getting current active meeting."""
        response = client.get(
            "/meetings/active",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_meeting.id
        assert data["status"] == "active"

    def test_get_active_meeting_none_active(
        self, client: TestClient, auth_headers, completed_meeting
    ):
        """Test getting active meeting when none are active."""
        response = client.get(
            "/meetings/active",
            headers=auth_headers,
        )
        # Should return null/None when no active meeting
        assert response.status_code == 200
        assert response.json() is None


class TestMeetingList:
    """Test meeting list endpoint."""

    def test_list_meetings(
        self, client: TestClient, auth_headers, test_meeting, completed_meeting
    ):
        """Test listing all meetings."""
        response = client.get(
            "/meetings/",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "meetings" in data
        assert "total" in data
        assert data["total"] >= 2

    def test_list_meetings_pagination(
        self, client: TestClient, auth_headers, test_meeting
    ):
        """Test meeting list pagination."""
        response = client.get(
            "/meetings/?skip=0&limit=1",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["meetings"]) <= 1

    def test_list_meetings_filter_by_type(
        self, client: TestClient, auth_headers, test_meeting, completed_meeting
    ):
        """Test filtering meetings by type."""
        response = client.get(
            "/meetings/?meeting_type=interview",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        for meeting in data["meetings"]:
            assert meeting["meeting_type"] == "interview"


class TestMeetingUpdate:
    """Test meeting update endpoints."""

    def test_end_meeting(
        self, client: TestClient, auth_headers, test_meeting
    ):
        """Test ending a meeting."""
        response = client.post(
            f"/meetings/{test_meeting.id}/end",
            headers=auth_headers,
            json={
                "notes": "Meeting ended successfully",
                "generate_summary": False,
                "send_email": False,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ended"
        assert data["ended_at"] is not None
        assert data["duration_seconds"] is not None

    def test_end_already_ended_meeting(
        self, client: TestClient, auth_headers, completed_meeting
    ):
        """Test ending an already ended meeting fails."""
        response = client.post(
            f"/meetings/{completed_meeting.id}/end",
            headers=auth_headers,
            json={},
        )
        assert response.status_code == 400

    def test_delete_meeting(
        self, client: TestClient, auth_headers, test_meeting
    ):
        """Test deleting a meeting."""
        response = client.delete(
            f"/meetings/{test_meeting.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200

        # Verify it's deleted
        get_response = client.get(
            f"/meetings/{test_meeting.id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404


class TestMeetingValidation:
    """Test input validation for meetings."""

    @pytest.mark.security
    def test_meeting_title_max_length(self, client: TestClient, auth_headers):
        """Test meeting title respects max length."""
        long_title = "A" * 501  # Exceeds 500 char limit
        response = client.post(
            "/meetings/",
            headers=auth_headers,
            json={"title": long_title},
        )
        assert response.status_code == 422

    @pytest.mark.security
    def test_meeting_notes_max_length(
        self, client: TestClient, auth_headers, test_meeting
    ):
        """Test meeting notes respects max length."""
        long_notes = "A" * 10001  # Exceeds 10000 char limit
        response = client.post(
            f"/meetings/{test_meeting.id}/end",
            headers=auth_headers,
            json={"notes": long_notes},
        )
        assert response.status_code == 422

    @pytest.mark.security
    def test_meeting_participant_count_bounds(
        self, client: TestClient, auth_headers
    ):
        """Test participant count validation."""
        # Too low
        response = client.post(
            "/meetings/",
            headers=auth_headers,
            json={"participant_count": 0},
        )
        assert response.status_code == 422

        # Too high
        response = client.post(
            "/meetings/",
            headers=auth_headers,
            json={"participant_count": 1001},
        )
        assert response.status_code == 422
