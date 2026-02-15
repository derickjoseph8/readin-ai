"""
Authentication tests for ReadIn AI backend.

Tests:
- User registration with validation
- User login
- Password requirements
- Token validation
- Rate limiting on auth endpoints
"""

import pytest
from fastapi.testclient import TestClient


class TestRegistration:
    """Test user registration endpoint."""

    def test_register_success(self, client: TestClient, test_profession):
        """Test successful user registration."""
        response = client.post(
            "/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePass123!",
                "full_name": "New User",
                "profession_id": test_profession.id,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_register_duplicate_email(self, client: TestClient, test_user):
        """Test registration with existing email fails."""
        response = client.post(
            "/auth/register",
            json={
                "email": test_user.email,
                "password": "SecurePass123!",
                "full_name": "Duplicate User",
            },
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_register_invalid_email(self, client: TestClient):
        """Test registration with invalid email fails."""
        response = client.post(
            "/auth/register",
            json={
                "email": "notanemail",
                "password": "SecurePass123!",
            },
        )
        assert response.status_code == 422  # Validation error

    @pytest.mark.security
    def test_register_weak_password_too_short(self, client: TestClient):
        """Test registration with too short password fails."""
        response = client.post(
            "/auth/register",
            json={
                "email": "test@example.com",
                "password": "Short1!",  # Only 7 chars
            },
        )
        assert response.status_code == 422

    @pytest.mark.security
    def test_register_weak_password_no_uppercase(self, client: TestClient):
        """Test registration without uppercase letter fails."""
        response = client.post(
            "/auth/register",
            json={
                "email": "test@example.com",
                "password": "nouppercase123!",
            },
        )
        assert response.status_code == 422

    @pytest.mark.security
    def test_register_weak_password_no_digit(self, client: TestClient):
        """Test registration without digit fails."""
        response = client.post(
            "/auth/register",
            json={
                "email": "test@example.com",
                "password": "NoDigitPassword!",
            },
        )
        assert response.status_code == 422

    @pytest.mark.security
    def test_register_weak_password_no_special(self, client: TestClient):
        """Test registration without special character fails."""
        response = client.post(
            "/auth/register",
            json={
                "email": "test@example.com",
                "password": "NoSpecialChar123",
            },
        )
        assert response.status_code == 422

    def test_register_invalid_profession(self, client: TestClient):
        """Test registration with non-existent profession fails."""
        response = client.post(
            "/auth/register",
            json={
                "email": "test@example.com",
                "password": "SecurePass123!",
                "profession_id": 99999,
            },
        )
        assert response.status_code == 400
        assert "invalid profession" in response.json()["detail"].lower()


class TestLogin:
    """Test user login endpoint."""

    def test_login_success(self, client: TestClient, test_user):
        """Test successful login."""
        response = client.post(
            "/auth/login",
            json={
                "email": test_user.email,
                "password": "TestPassword123!",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client: TestClient, test_user):
        """Test login with wrong password fails."""
        response = client.post(
            "/auth/login",
            json={
                "email": test_user.email,
                "password": "WrongPassword123!",
            },
        )
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    def test_login_nonexistent_user(self, client: TestClient):
        """Test login with non-existent email fails."""
        response = client.post(
            "/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "AnyPassword123!",
            },
        )
        assert response.status_code == 401

    @pytest.mark.security
    def test_login_error_message_doesnt_leak_info(self, client: TestClient, test_user):
        """Test that login error doesn't reveal whether email exists."""
        # Wrong password for existing user
        response1 = client.post(
            "/auth/login",
            json={
                "email": test_user.email,
                "password": "WrongPassword123!",
            },
        )

        # Non-existent user
        response2 = client.post(
            "/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "AnyPassword123!",
            },
        )

        # Both should return same error message to prevent enumeration
        assert response1.json()["detail"] == response2.json()["detail"]


class TestTokenValidation:
    """Test token validation and protected endpoints."""

    def test_access_protected_endpoint_with_valid_token(
        self, client: TestClient, auth_headers
    ):
        """Test accessing protected endpoint with valid token."""
        response = client.get("/user/me", headers=auth_headers)
        assert response.status_code == 200

    def test_access_protected_endpoint_without_token(self, client: TestClient):
        """Test accessing protected endpoint without token fails."""
        response = client.get("/user/me")
        assert response.status_code == 401

    def test_access_protected_endpoint_with_invalid_token(self, client: TestClient):
        """Test accessing protected endpoint with invalid token fails."""
        response = client.get(
            "/user/me",
            headers={"Authorization": "Bearer invalid_token_here"},
        )
        assert response.status_code == 401

    def test_access_protected_endpoint_with_malformed_header(self, client: TestClient):
        """Test accessing protected endpoint with malformed auth header fails."""
        response = client.get(
            "/user/me",
            headers={"Authorization": "NotBearer token"},
        )
        assert response.status_code == 401


class TestUserStatus:
    """Test user status endpoint."""

    def test_get_user_status_trial(self, client: TestClient, auth_headers, test_user):
        """Test getting status for trial user."""
        response = client.get("/user/status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["subscription_status"] == "trial"
        assert data["trial_days_remaining"] > 0
        assert data["daily_limit"] == 10  # Trial limit
        assert data["can_use"] is True

    def test_get_user_status_premium(
        self, client: TestClient, premium_auth_headers, premium_user
    ):
        """Test getting status for premium user."""
        response = client.get("/user/status", headers=premium_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["subscription_status"] == "active"
        assert data["daily_limit"] is None  # Unlimited
        assert data["can_use"] is True

    def test_get_user_status_expired_trial(
        self, client: TestClient, test_db, expired_trial_user
    ):
        """Test getting status for expired trial user."""
        from auth import create_access_token

        token = create_access_token(expired_trial_user.id)
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/user/status", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["trial_days_remaining"] == 0
        assert data["can_use"] is False
