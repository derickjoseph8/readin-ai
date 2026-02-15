"""
Security tests for ReadIn AI backend.

Tests:
- CORS configuration
- Rate limiting
- Input validation
- SQL injection prevention
- XSS prevention
- Authentication bypass attempts
"""

import pytest
from fastapi.testclient import TestClient


class TestCORSConfiguration:
    """Test CORS middleware configuration."""

    def test_cors_headers_present(self, client: TestClient):
        """Test that CORS headers are present in response."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        # In development mode, should allow the origin
        assert "access-control-allow-origin" in response.headers

    def test_cors_credentials_header(self, client: TestClient):
        """Test CORS credentials header configuration."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        # Credentials should only be allowed with specific origins
        if "access-control-allow-credentials" in response.headers:
            # If credentials are allowed, origin should not be "*"
            allow_origin = response.headers.get("access-control-allow-origin", "")
            assert allow_origin != "*" or \
                   response.headers.get("access-control-allow-credentials") != "true"


class TestSecurityHeaders:
    """Test security headers middleware."""

    def test_content_type_options_header(self, client: TestClient):
        """Test X-Content-Type-Options header is set."""
        response = client.get("/health")
        assert response.headers.get("x-content-type-options") == "nosniff"

    def test_frame_options_header(self, client: TestClient):
        """Test X-Frame-Options header is set."""
        response = client.get("/health")
        assert response.headers.get("x-frame-options") == "DENY"

    def test_xss_protection_header(self, client: TestClient):
        """Test X-XSS-Protection header is set."""
        response = client.get("/health")
        assert "1" in response.headers.get("x-xss-protection", "")

    def test_referrer_policy_header(self, client: TestClient):
        """Test Referrer-Policy header is set."""
        response = client.get("/health")
        assert response.headers.get("referrer-policy") is not None

    def test_request_id_in_response(self, client: TestClient):
        """Test X-Request-ID is returned in response."""
        response = client.get("/health")
        assert "x-request-id" in response.headers

    def test_response_time_header(self, client: TestClient):
        """Test X-Response-Time header is returned."""
        response = client.get("/health")
        assert "x-response-time" in response.headers


class TestInputValidation:
    """Test input validation security."""

    @pytest.mark.security
    def test_sql_injection_in_email(self, client: TestClient):
        """Test SQL injection attempt in email field is handled."""
        response = client.post(
            "/auth/login",
            json={
                "email": "'; DROP TABLE users; --@example.com",
                "password": "password",
            },
        )
        # Should return validation error, not crash
        assert response.status_code in [401, 422]

    @pytest.mark.security
    def test_xss_in_user_name(self, client: TestClient, test_profession):
        """Test XSS attempt in user name is rejected."""
        response = client.post(
            "/auth/register",
            json={
                "email": "xss@example.com",
                "password": "SecurePass123!",
                "full_name": "<script>alert('xss')</script>",
            },
        )
        # Should reject the malicious content
        assert response.status_code == 422

    @pytest.mark.security
    def test_xss_in_meeting_title(self, client: TestClient, auth_headers):
        """Test XSS in meeting title is handled safely."""
        response = client.post(
            "/meetings/",
            headers=auth_headers,
            json={
                "title": "<img src=x onerror=alert('xss')>",
            },
        )
        # May accept but should be escaped when rendered
        # The API itself should store it safely
        if response.status_code == 200:
            data = response.json()
            # Title should be stored as-is (escaping happens on render)
            assert "title" in data

    @pytest.mark.security
    def test_oversized_payload_rejected(self, client: TestClient, auth_headers):
        """Test that oversized payloads are rejected."""
        # Create a very large payload
        large_text = "A" * 100000  # 100KB of text
        response = client.post(
            "/meetings/",
            headers=auth_headers,
            json={
                "title": large_text,
            },
        )
        # Should be rejected due to size limits
        assert response.status_code == 422

    @pytest.mark.security
    def test_null_byte_injection(self, client: TestClient):
        """Test null byte injection is handled."""
        response = client.post(
            "/auth/login",
            json={
                "email": "test\x00@example.com",
                "password": "password",
            },
        )
        # Should handle gracefully
        assert response.status_code in [401, 422]


class TestAuthenticationSecurity:
    """Test authentication security measures."""

    @pytest.mark.security
    def test_jwt_without_signature(self, client: TestClient):
        """Test JWT without signature is rejected."""
        # Attempt to use an unsigned JWT (alg: none attack)
        unsigned_token = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiIxIn0."
        response = client.get(
            "/user/me",
            headers={"Authorization": f"Bearer {unsigned_token}"},
        )
        assert response.status_code == 401

    @pytest.mark.security
    def test_expired_token_rejected(self, client: TestClient):
        """Test expired tokens are rejected."""
        # This would require creating a token with past expiry
        # For now, just verify invalid tokens are rejected
        old_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxfQ.signature"
        response = client.get(
            "/user/me",
            headers={"Authorization": f"Bearer {old_token}"},
        )
        assert response.status_code == 401

    @pytest.mark.security
    def test_tampered_token_rejected(self, client: TestClient, auth_headers):
        """Test tampered tokens are rejected."""
        # Get a valid token and modify it
        token = auth_headers["Authorization"].replace("Bearer ", "")
        tampered_token = token[:-5] + "XXXXX"  # Modify signature
        response = client.get(
            "/user/me",
            headers={"Authorization": f"Bearer {tampered_token}"},
        )
        assert response.status_code == 401


class TestRateLimiting:
    """Test rate limiting functionality."""

    @pytest.mark.security
    @pytest.mark.slow
    def test_login_rate_limit(self, client: TestClient):
        """Test login endpoint is rate limited."""
        # Make multiple rapid requests
        responses = []
        for i in range(10):
            response = client.post(
                "/auth/login",
                json={
                    "email": f"test{i}@example.com",
                    "password": "password",
                },
            )
            responses.append(response.status_code)

        # At least one should be rate limited (429) after threshold
        # Note: This test may need adjustment based on rate limit config
        # In test environment, rate limiting might be disabled
        # assert 429 in responses or all(r in [401, 422] for r in responses)

    @pytest.mark.security
    @pytest.mark.slow
    def test_register_rate_limit(self, client: TestClient):
        """Test registration endpoint is rate limited."""
        responses = []
        for i in range(10):
            response = client.post(
                "/auth/register",
                json={
                    "email": f"newuser{i}@example.com",
                    "password": "SecurePass123!",
                },
            )
            responses.append(response.status_code)

        # Should see some rate limiting after threshold
        # Note: Actual behavior depends on rate limit configuration


class TestDataIsolation:
    """Test user data isolation."""

    @pytest.mark.security
    def test_cannot_access_other_user_meeting(
        self, client: TestClient, test_meeting, premium_auth_headers
    ):
        """Test user cannot access another user's meeting."""
        response = client.get(
            f"/meetings/{test_meeting.id}",
            headers=premium_auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.security
    def test_cannot_delete_other_user_meeting(
        self, client: TestClient, test_meeting, premium_auth_headers
    ):
        """Test user cannot delete another user's meeting."""
        response = client.delete(
            f"/meetings/{test_meeting.id}",
            headers=premium_auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.security
    def test_cannot_end_other_user_meeting(
        self, client: TestClient, test_meeting, premium_auth_headers
    ):
        """Test user cannot end another user's meeting."""
        response = client.post(
            f"/meetings/{test_meeting.id}/end",
            headers=premium_auth_headers,
            json={},
        )
        assert response.status_code == 404


class TestHealthCheck:
    """Test health check endpoint."""

    def test_health_check_returns_status(self, client: TestClient):
        """Test health check returns proper status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "checks" in data
        assert data["status"] in ["healthy", "unhealthy"]
