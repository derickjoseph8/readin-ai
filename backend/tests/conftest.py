"""
Pytest fixtures for ReadIn AI backend tests.

Provides:
- Test database with SQLite (in-memory)
- Test client for API requests
- Factory fixtures for creating test data
- Authentication helpers
"""

import os
import pytest
from datetime import datetime, timedelta
from typing import Generator, Dict, Any

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Set test environment before importing app
os.environ["ENVIRONMENT"] = "development"
os.environ["JWT_SECRET"] = "test-secret-key-for-testing-only-32chars"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from database import Base, get_db
from main import app
from models import User, Profession, Organization, Meeting, Conversation, UserLearningProfile
from auth import hash_password, create_access_token


# =============================================================================
# DATABASE FIXTURES
# =============================================================================

@pytest.fixture(scope="function")
def test_engine():
    """Create a test database engine with SQLite in-memory."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_db(test_engine) -> Generator[Session, None, None]:
    """Create a test database session."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def client(test_db) -> Generator[TestClient, None, None]:
    """Create a test client with database override."""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# =============================================================================
# USER FIXTURES
# =============================================================================

@pytest.fixture
def test_profession(test_db) -> Profession:
    """Create a test profession."""
    profession = Profession(
        name="Software Engineer",
        category="Technology",
        description="Develops software applications",
        terminology=["API", "microservices", "CI/CD"],
        common_topics=["architecture", "performance", "testing"],
        communication_style="technical",
        is_active=True,
    )
    test_db.add(profession)
    test_db.commit()
    test_db.refresh(profession)
    return profession


@pytest.fixture
def test_user(test_db, test_profession) -> User:
    """Create a test user with trial subscription."""
    user = User(
        email="test@example.com",
        hashed_password=hash_password("TestPassword123!"),
        full_name="Test User",
        profession_id=test_profession.id,
        subscription_status="trial",
        trial_start_date=datetime.utcnow(),
        trial_end_date=datetime.utcnow() + timedelta(days=14),
        email_verified=True,  # Required for login
    )
    test_db.add(user)
    test_db.flush()

    # Create learning profile
    learning_profile = UserLearningProfile(user_id=user.id)
    test_db.add(learning_profile)

    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def premium_user(test_db, test_profession) -> User:
    """Create a test user with active premium subscription."""
    user = User(
        email="premium@example.com",
        hashed_password=hash_password("PremiumPassword123!"),
        full_name="Premium User",
        profession_id=test_profession.id,
        subscription_status="active",
        subscription_id="sub_test123",
        subscription_end_date=datetime.utcnow() + timedelta(days=30),
        email_verified=True,  # Required for login
    )
    test_db.add(user)
    test_db.flush()

    learning_profile = UserLearningProfile(user_id=user.id)
    test_db.add(learning_profile)

    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def expired_trial_user(test_db, test_profession) -> User:
    """Create a test user with expired trial."""
    user = User(
        email="expired@example.com",
        hashed_password=hash_password("ExpiredPassword123!"),
        full_name="Expired User",
        profession_id=test_profession.id,
        subscription_status="expired",  # Mark as expired
        trial_start_date=datetime.utcnow() - timedelta(days=20),
        trial_end_date=datetime.utcnow() - timedelta(days=6),
        email_verified=True,  # Required for login
    )
    test_db.add(user)
    test_db.flush()

    learning_profile = UserLearningProfile(user_id=user.id)
    test_db.add(learning_profile)

    test_db.commit()
    test_db.refresh(user)
    return user


# =============================================================================
# AUTHENTICATION FIXTURES
# =============================================================================

@pytest.fixture
def auth_headers(test_user) -> Dict[str, str]:
    """Get authorization headers for test user."""
    token = create_access_token(test_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def premium_auth_headers(premium_user) -> Dict[str, str]:
    """Get authorization headers for premium user."""
    token = create_access_token(premium_user.id)
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# ORGANIZATION FIXTURES
# =============================================================================

@pytest.fixture
def test_organization(test_db, test_user) -> Organization:
    """Create a test organization."""
    org = Organization(
        name="Test Company",
        plan_type="team",
        max_users=10,
        admin_user_id=test_user.id,
        subscription_status="active",
    )
    test_db.add(org)
    test_db.commit()
    test_db.refresh(org)

    # Update user to be part of org
    test_user.organization_id = org.id
    test_user.role_in_org = "admin"
    test_db.commit()

    return org


# =============================================================================
# MEETING FIXTURES
# =============================================================================

@pytest.fixture
def test_meeting(test_db, test_user) -> Meeting:
    """Create a test meeting."""
    meeting = Meeting(
        user_id=test_user.id,
        meeting_type="general",
        title="Test Meeting",
        meeting_app="Zoom",
        status="active",
        started_at=datetime.utcnow(),
    )
    test_db.add(meeting)
    test_db.commit()
    test_db.refresh(meeting)
    return meeting


@pytest.fixture
def completed_meeting(test_db, test_user) -> Meeting:
    """Create a completed test meeting with conversations."""
    meeting = Meeting(
        user_id=test_user.id,
        meeting_type="interview",
        title="Completed Interview",
        meeting_app="Teams",
        status="ended",
        started_at=datetime.utcnow() - timedelta(hours=1),
        ended_at=datetime.utcnow(),
        duration_seconds=3600,
    )
    test_db.add(meeting)
    test_db.flush()

    # Add some conversations
    for i in range(3):
        conv = Conversation(
            meeting_id=meeting.id,
            speaker="other" if i % 2 == 0 else "user",
            heard_text=f"Test question {i + 1}",
            response_text=f"Test response {i + 1}",
            timestamp=datetime.utcnow() - timedelta(minutes=30 - i * 10),
        )
        test_db.add(conv)

    test_db.commit()
    test_db.refresh(meeting)
    return meeting


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_test_user(
    db: Session,
    email: str = "user@example.com",
    password: str = "Password123!",
    subscription_status: str = "trial",
) -> User:
    """Helper to create a user with specified attributes."""
    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name="Test User",
        subscription_status=subscription_status,
        trial_start_date=datetime.utcnow(),
        trial_end_date=datetime.utcnow() + timedelta(days=14),
    )
    db.add(user)
    db.flush()

    learning_profile = UserLearningProfile(user_id=user.id)
    db.add(learning_profile)

    db.commit()
    db.refresh(user)
    return user
