"""Tests for semantic search API endpoints."""

import pytest
from unittest.mock import patch, MagicMock


class TestSemanticSearch:
    """Test semantic search functionality."""

    def test_semantic_search_unauthenticated(self, client):
        """Test that semantic search requires authentication."""
        response = client.get("/api/v1/search/semantic?q=test")
        assert response.status_code == 401

    def test_semantic_search_short_query(self, client, auth_headers):
        """Test that very short queries are rejected."""
        response = client.get("/api/v1/search/semantic?q=a", headers=auth_headers)
        assert response.status_code == 422  # Validation error

    def test_semantic_search_empty_results(self, client, auth_headers):
        """Test semantic search with no matching results."""
        response = client.get(
            "/api/v1/search/semantic?q=nonexistent topic",
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert data["query"] == "nonexistent topic"
        assert "results" in data
        assert "search_mode" in data

    def test_semantic_search_status(self, client, auth_headers):
        """Test semantic search status endpoint."""
        response = client.get("/api/v1/search/semantic/status", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert "pgvector_available" in data
        assert "search_mode" in data
        assert "embedding_model" in data
        assert "total_meetings" in data
        assert "meetings_with_embeddings" in data

    def test_semantic_search_with_filters(self, client, auth_headers):
        """Test semantic search with filters."""
        response = client.get(
            "/api/v1/search/semantic?q=project discussion&meeting_type=team_meeting&limit=5",
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert data["query"] == "project discussion"
        assert len(data["results"]) <= 5

    def test_semantic_search_with_date_filter(self, client, auth_headers):
        """Test semantic search with date filtering."""
        from datetime import date

        today = date.today().isoformat()
        response = client.get(
            f"/api/v1/search/semantic?q=meeting&date_from={today}",
            headers=auth_headers
        )
        assert response.status_code == 200

    def test_semantic_search_min_similarity(self, client, auth_headers):
        """Test semantic search with custom similarity threshold."""
        response = client.get(
            "/api/v1/search/semantic?q=test&min_similarity=0.5",
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        # All results should have similarity >= 0.5
        for result in data["results"]:
            assert result["similarity_score"] >= 0.5


class TestSimilarMeetings:
    """Test similar meetings functionality."""

    def test_similar_meetings_unauthenticated(self, client):
        """Test that similar meetings requires authentication."""
        response = client.get("/api/v1/search/semantic/meetings/1/similar")
        assert response.status_code == 401

    def test_similar_meetings_not_found(self, client, auth_headers):
        """Test similar meetings for non-existent meeting."""
        response = client.get(
            "/api/v1/search/semantic/meetings/99999/similar",
            headers=auth_headers
        )
        assert response.status_code == 404


class TestConversationSearch:
    """Test conversation semantic search."""

    def test_conversation_search_unauthenticated(self, client):
        """Test that conversation search requires authentication."""
        response = client.get("/api/v1/search/semantic/conversations?q=test")
        assert response.status_code == 401

    def test_conversation_search(self, client, auth_headers):
        """Test conversation semantic search."""
        response = client.get(
            "/api/v1/search/semantic/conversations?q=project update",
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert "query" in data
        assert "results" in data


class TestEmbeddingGeneration:
    """Test embedding generation endpoints."""

    def test_generate_embeddings_unauthenticated(self, client):
        """Test that embedding generation requires authentication."""
        response = client.post("/api/v1/search/semantic/embeddings/generate")
        assert response.status_code == 401

    def test_generate_embeddings(self, client, auth_headers):
        """Test embedding generation endpoint."""
        response = client.post(
            "/api/v1/search/semantic/embeddings/generate",
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert "processed" in data
        assert "skipped" in data
        assert "failed" in data
        assert "message" in data


class TestHybridSearch:
    """Test hybrid search functionality."""

    def test_hybrid_search_unauthenticated(self, client):
        """Test that hybrid search requires authentication."""
        response = client.get("/api/v1/search/hybrid?q=test")
        assert response.status_code == 401

    def test_hybrid_search(self, client, auth_headers):
        """Test hybrid search combining full-text and semantic."""
        response = client.get(
            "/api/v1/search/hybrid?q=project meeting",
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert "query" in data
        assert "full_text_results" in data
        assert "semantic_results" in data
        assert "combined_results" in data

    def test_hybrid_search_semantic_boost(self, client, auth_headers):
        """Test hybrid search with different semantic boost values."""
        # Full-text only
        response1 = client.get(
            "/api/v1/search/hybrid?q=test&semantic_boost=0.0",
            headers=auth_headers
        )
        assert response1.status_code == 200

        # Semantic only
        response2 = client.get(
            "/api/v1/search/hybrid?q=test&semantic_boost=1.0",
            headers=auth_headers
        )
        assert response2.status_code == 200

        # Balanced
        response3 = client.get(
            "/api/v1/search/hybrid?q=test&semantic_boost=0.5",
            headers=auth_headers
        )
        assert response3.status_code == 200


class TestEmbeddingService:
    """Unit tests for embedding service."""

    def test_generate_embedding_empty_text(self):
        """Test that empty text returns empty embedding."""
        from services.embedding_service import generate_embedding

        result = generate_embedding("")
        assert result == []

        result = generate_embedding("   ")
        assert result == []

    def test_prepare_meeting_text(self):
        """Test preparing meeting text for embedding."""
        from services.embedding_service import prepare_meeting_text_for_embedding

        # Test with all fields
        text = prepare_meeting_text_for_embedding(
            title="Test Meeting",
            notes="Meeting notes here",
            transcript_texts=["Hello everyone", "Let's discuss the project"]
        )
        assert "Title: Test Meeting" in text
        assert "Notes: Meeting notes here" in text
        assert "Transcript:" in text

        # Test with only title
        text = prepare_meeting_text_for_embedding(title="Just a Title")
        assert "Title: Just a Title" in text

        # Test with no content
        text = prepare_meeting_text_for_embedding()
        assert text == ""

    def test_compute_similarity(self):
        """Test similarity computation."""
        from services.embedding_service import compute_similarity

        # Identical vectors
        v1 = [1.0, 0.0, 0.0]
        assert compute_similarity(v1, v1) == pytest.approx(1.0)

        # Orthogonal vectors
        v2 = [0.0, 1.0, 0.0]
        assert compute_similarity(v1, v2) == pytest.approx(0.0)

        # Empty vectors
        assert compute_similarity([], []) == 0.0
        assert compute_similarity(v1, []) == 0.0
