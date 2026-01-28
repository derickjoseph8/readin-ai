"""API client for ReadIn AI backend."""

import json
import os
from typing import Optional, Dict, Any
from pathlib import Path

import httpx

# API base URL - check both env var names for compatibility
API_BASE_URL = os.getenv("API_BASE_URL") or os.getenv("READIN_API_URL", "https://api.getreadin.ai")

# Local token storage
TOKEN_FILE = Path.home() / ".readin" / "auth.json"


class APIClient:
    """Client for ReadIn AI backend API."""

    def __init__(self):
        self._token: Optional[str] = None
        self._user_status: Optional[Dict] = None
        self._load_token()

    def _load_token(self):
        """Load saved token from disk."""
        try:
            if TOKEN_FILE.exists():
                with open(TOKEN_FILE, "r") as f:
                    data = json.load(f)
                    self._token = data.get("access_token")
        except Exception:
            self._token = None

    def _save_token(self, token: str):
        """Save token to disk."""
        try:
            TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(TOKEN_FILE, "w") as f:
                json.dump({"access_token": token}, f)
            self._token = token
        except Exception as e:
            print(f"Failed to save token: {e}")

    def _clear_token(self):
        """Clear saved token."""
        try:
            if TOKEN_FILE.exists():
                TOKEN_FILE.unlink()
        except Exception:
            pass
        self._token = None

    def _headers(self) -> Dict[str, str]:
        """Get request headers with auth token."""
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make API request."""
        url = f"{API_BASE_URL}{endpoint}"
        try:
            with httpx.Client(timeout=30.0) as client:
                if method == "GET":
                    response = client.get(url, headers=self._headers())
                elif method == "POST":
                    response = client.post(url, headers=self._headers(), json=data)
                else:
                    raise ValueError(f"Unknown method: {method}")

                if response.status_code == 401:
                    self._clear_token()
                    return {"error": "unauthorized", "message": "Please log in again"}

                if response.status_code >= 400:
                    try:
                        error_data = response.json()
                        return {"error": True, "message": error_data.get("detail", "Request failed")}
                    except Exception:
                        return {"error": True, "message": f"Request failed: {response.status_code}"}

                return response.json()

        except httpx.ConnectError:
            return {"error": "connection", "message": "Cannot connect to server"}
        except httpx.TimeoutException:
            return {"error": "timeout", "message": "Request timed out"}
        except Exception as e:
            return {"error": "unknown", "message": str(e)}

    # ============== Auth ==============

    def register(self, email: str, password: str, full_name: Optional[str] = None) -> Dict:
        """Register a new account."""
        result = self._request("POST", "/auth/register", {
            "email": email,
            "password": password,
            "full_name": full_name
        })
        if "access_token" in result:
            self._save_token(result["access_token"])
        return result

    def login(self, email: str, password: str) -> Dict:
        """Login and get token."""
        result = self._request("POST", "/auth/login", {
            "email": email,
            "password": password
        })
        if "access_token" in result:
            self._save_token(result["access_token"])
        return result

    def logout(self):
        """Logout - clear local token."""
        self._clear_token()
        self._user_status = None

    def is_logged_in(self) -> bool:
        """Check if user has a saved token."""
        return self._token is not None

    # ============== User ==============

    def get_status(self) -> Dict:
        """Get user subscription and usage status."""
        result = self._request("GET", "/user/status")
        if "error" not in result:
            self._user_status = result
        return result

    def get_user(self) -> Dict:
        """Get user profile info."""
        return self._request("GET", "/user/me")

    # ============== Usage ==============

    def increment_usage(self) -> Dict:
        """Increment daily usage count. Returns updated usage info."""
        return self._request("POST", "/usage/increment")

    def can_use(self) -> bool:
        """Check if user can make another request."""
        if self._user_status:
            return self._user_status.get("can_use", False)
        # Refresh status
        status = self.get_status()
        return status.get("can_use", False)

    def get_daily_remaining(self) -> Optional[int]:
        """Get remaining daily requests (None if unlimited)."""
        if self._user_status:
            limit = self._user_status.get("daily_limit")
            if limit is None:
                return None  # Unlimited
            usage = self._user_status.get("daily_usage", 0)
            return max(0, limit - usage)
        return None

    # ============== Subscription ==============

    def get_checkout_url(self) -> Optional[str]:
        """Get Stripe checkout URL for subscription."""
        result = self._request("POST", "/subscription/create-checkout", {})
        return result.get("checkout_url")

    def get_billing_portal_url(self) -> Optional[str]:
        """Get Stripe billing portal URL."""
        result = self._request("POST", "/subscription/manage")
        return result.get("portal_url")


# Global instance
api = APIClient()
