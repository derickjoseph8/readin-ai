"""
Tests for AI-Powered Meeting Recommendations.

Tests the RecommendationService and recommendation routes.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from main import app
from services.recommendation_service import RecommendationService


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return MagicMock()


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = MagicMock()
    user.id = 1
    user.email = "test@example.com"
    user.preferred_language = "en"
    return user


@pytest.fixture
def mock_meeting():
    """Create a mock meeting."""
    meeting = MagicMock()
    meeting.id = 1
    meeting.user_id = 1
    meeting.meeting_type = "general"
    meeting.title = "Test Meeting"
    meeting.started_at = datetime.utcnow() - timedelta(hours=1)
    meeting.ended_at = datetime.utcnow()
    meeting.duration_seconds = 3600
    meeting.participant_count = 2
    meeting.status = "ended"
    meeting.notes = "Test meeting notes"
    return meeting


@pytest.fixture
def mock_conversation():
    """Create a mock conversation."""
    conv = MagicMock()
    conv.id = 1
    conv.meeting_id = 1
    conv.speaker = "user"
    conv.heard_text = "Let's discuss the project timeline"
    conv.response_text = "Sure, let's review the milestones"
    conv.timestamp = datetime.utcnow()
    return conv


@pytest.fixture
def mock_summary():
    """Create a mock meeting summary."""
    summary = MagicMock()
    summary.id = 1
    summary.meeting_id = 1
    summary.summary_text = "Discussion about project timeline"
    summary.key_points = ["Review milestones", "Set deadlines"]
    summary.sentiment = "positive"
    summary.topics_discussed = ["timeline", "milestones"]
    summary.decisions_made = ["Set Q2 deadline"]
    return summary


@pytest.fixture
def mock_participant():
    """Create a mock participant memory."""
    participant = MagicMock()
    participant.id = 1
    participant.user_id = 1
    participant.participant_name = "John Doe"
    participant.participant_role = "Project Manager"
    participant.company = "Acme Corp"
    participant.key_points = ["Focuses on deadlines"]
    participant.topics_discussed = ["project management"]
    participant.communication_style = "Direct and professional"
    participant.relationship_notes = "Good working relationship"
    participant.meeting_count = 5
    participant.last_interaction = datetime.utcnow()
    participant.first_interaction = datetime.utcnow() - timedelta(days=30)
    return participant


# =============================================================================
# SERVICE TESTS
# =============================================================================

class TestRecommendationService:
    """Tests for RecommendationService."""

    def test_service_initialization(self, mock_db):
        """Test service initializes correctly."""
        service = RecommendationService(mock_db)
        assert service.db == mock_db
        assert service.client is not None
        assert service.model is not None

    def test_get_cache_key(self, mock_db):
        """Test cache key generation."""
        service = RecommendationService(mock_db)
        key = service._get_cache_key("next_steps", 1, 5)
        assert key == "recommendation:next_steps:1:5"

    def test_get_user_language_with_preference(self, mock_db, mock_user):
        """Test getting user language preference."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        service = RecommendationService(mock_db)
        language = service._get_user_language(1)
        assert language == "en"

    def test_get_user_language_default(self, mock_db):
        """Test default language when user not found."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        service = RecommendationService(mock_db)
        language = service._get_user_language(1)
        assert language == "en"

    def test_get_meeting_transcript_empty(self, mock_db):
        """Test transcript generation with no conversations."""
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        service = RecommendationService(mock_db)
        transcript = service._get_meeting_transcript(1)
        assert transcript == ""

    def test_get_meeting_transcript_with_conversations(self, mock_db, mock_conversation):
        """Test transcript generation with conversations."""
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_conversation]
        service = RecommendationService(mock_db)
        transcript = service._get_meeting_transcript(1)
        assert "Let's discuss the project timeline" in transcript

    def test_get_meeting_context_not_found(self, mock_db):
        """Test meeting context when meeting not found."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        service = RecommendationService(mock_db)
        context = service._get_meeting_context(1)
        assert context == {}

    def test_get_meeting_context_with_data(self, mock_db, mock_meeting, mock_summary):
        """Test meeting context with data."""
        # Setup mocks
        def mock_query(model):
            mock = MagicMock()
            if model.__name__ == "Meeting":
                mock.filter.return_value.first.return_value = mock_meeting
            elif model.__name__ == "MeetingSummary":
                mock.filter.return_value.first.return_value = mock_summary
            else:
                mock.filter.return_value.all.return_value = []
            return mock
        mock_db.query.side_effect = mock_query

        service = RecommendationService(mock_db)
        context = service._get_meeting_context(1)

        assert context["meeting_id"] == 1
        assert context["meeting_type"] == "general"
        assert context["title"] == "Test Meeting"

    @pytest.mark.asyncio
    async def test_get_next_steps_no_meeting(self, mock_db):
        """Test next steps when meeting not found."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        service = RecommendationService(mock_db)
        steps = await service.get_next_steps(999)
        assert steps == []

    @pytest.mark.asyncio
    @patch('services.recommendation_service.cache')
    async def test_get_next_steps_cached(self, mock_cache, mock_db):
        """Test next steps returns cached value."""
        mock_cache.get.return_value = ["Step 1", "Step 2"]
        service = RecommendationService(mock_db)
        steps = await service.get_next_steps(1)
        assert steps == ["Step 1", "Step 2"]

    @pytest.mark.asyncio
    async def test_get_meeting_prep_no_meeting(self, mock_db):
        """Test meeting prep when meeting not found."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        service = RecommendationService(mock_db)
        prep = await service.get_meeting_prep(999)
        assert prep == {}

    @pytest.mark.asyncio
    async def test_get_participant_insights_not_found(self, mock_db):
        """Test participant insights when participant not found."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        service = RecommendationService(mock_db)
        insights = await service.get_participant_insights(999, 1)
        assert insights.get("error") == "Participant not found"

    @pytest.mark.asyncio
    @patch('services.recommendation_service.cache')
    async def test_get_topic_suggestions_cached(self, mock_cache, mock_db, mock_user):
        """Test topic suggestions returns cached value."""
        mock_cache.get.return_value = ["Topic 1", "Topic 2"]
        service = RecommendationService(mock_db)
        topics = await service.get_topic_suggestions(1)
        assert topics == ["Topic 1", "Topic 2"]

    @pytest.mark.asyncio
    async def test_detect_risks_no_meeting(self, mock_db):
        """Test risk detection when meeting not found."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        service = RecommendationService(mock_db)
        risks = await service.detect_risks(999)
        assert risks == []


# =============================================================================
# ROUTE TESTS (Mocked)
# =============================================================================

class TestRecommendationRoutes:
    """Tests for recommendation API routes."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_routes_exist(self, client):
        """Test that recommendation routes are registered."""
        # These should return 401 without auth, not 404
        response = client.get("/api/v1/recommendations/topics")
        assert response.status_code in [401, 403]  # Unauthorized, not Not Found

        response = client.get("/api/v1/recommendations/meetings/1")
        assert response.status_code in [401, 403]

        response = client.get("/api/v1/recommendations/meetings/1/next-steps")
        assert response.status_code in [401, 403]

        response = client.get("/api/v1/recommendations/meetings/1/risks")
        assert response.status_code in [401, 403]

        response = client.get("/api/v1/recommendations/meetings/1/prep")
        assert response.status_code in [401, 403]

        response = client.get("/api/v1/recommendations/participants/1/insights")
        assert response.status_code in [401, 403]


# =============================================================================
# INTEGRATION TESTS (Require actual Claude API)
# =============================================================================

@pytest.mark.integration
@pytest.mark.skipif(True, reason="Requires actual Claude API and database")
class TestRecommendationIntegration:
    """Integration tests for recommendations (requires Claude API)."""

    @pytest.mark.asyncio
    async def test_full_recommendation_workflow(self):
        """Test complete recommendation workflow with real API."""
        # This would test actual Claude API calls
        pass

    @pytest.mark.asyncio
    async def test_next_steps_generation(self):
        """Test next steps generation with real API."""
        pass

    @pytest.mark.asyncio
    async def test_risk_detection(self):
        """Test risk detection with real API."""
        pass


# =============================================================================
# CACHE TESTS
# =============================================================================

class TestRecommendationCaching:
    """Tests for recommendation caching behavior."""

    @patch('services.recommendation_service.cache')
    def test_invalidate_meeting_cache(self, mock_cache, mock_db):
        """Test cache invalidation for a meeting."""
        service = RecommendationService(mock_db)
        service.invalidate_meeting_cache(1)

        # Verify delete_pattern was called for each pattern
        assert mock_cache.delete_pattern.call_count >= 4

    @patch('services.recommendation_service.cache')
    def test_invalidate_user_cache(self, mock_cache, mock_db):
        """Test cache invalidation for a user."""
        service = RecommendationService(mock_db)
        service.invalidate_user_cache(1)

        # Verify delete_pattern was called
        assert mock_cache.delete_pattern.call_count >= 2
