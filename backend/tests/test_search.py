"""Tests for search API endpoints."""

import pytest


class TestSearch:
    """Test search functionality."""

    def test_search_unauthenticated(self, client):
        """Test that search requires authentication."""
        response = client.get("/api/v1/search?q=test")
        assert response.status_code == 401

    def test_search_short_query(self, client, auth_headers):
        """Test that very short queries are rejected."""
        response = client.get("/api/v1/search?q=a", headers=auth_headers)
        assert response.status_code == 422  # Validation error

    def test_search_empty_results(self, client, auth_headers):
        """Test search with no matching results."""
        response = client.get("/api/v1/search?q=nonexistent", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["query"] == "nonexistent"
        assert data["total_results"] == 0
        assert data["meetings"] == []
        assert data["conversations"] == []
        assert data["tasks"] == []

    def test_search_meetings(self, client, auth_headers, completed_meeting):
        """Test searching for meetings."""
        response = client.get(
            "/api/v1/search?q=Completed&scope=meetings",
            headers=auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["total_results"] >= 1
        assert len(data["meetings"]) >= 1

    def test_search_with_date_filter(self, client, auth_headers, completed_meeting):
        """Test search with date filtering."""
        from datetime import date

        today = date.today().isoformat()
        response = client.get(
            f"/api/v1/search?q=Completed&date_from={today}",
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_search_suggestions(self, client, auth_headers, completed_meeting):
        """Test search suggestions endpoint."""
        response = client.get(
            "/api/v1/search/suggestions?q=Comp",
            headers=auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert "suggestions" in data
        assert "query" in data

    def test_search_meetings_paginated(self, client, auth_headers):
        """Test paginated meeting search."""
        response = client.get(
            "/api/v1/search/meetings?q=test&page=1&page_size=10",
            headers=auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert "items" in data
        assert "meta" in data
        assert "page" in data["meta"]
        assert "total_pages" in data["meta"]
