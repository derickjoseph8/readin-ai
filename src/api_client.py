"""API client for ReadIn AI backend."""

import json
import os
import base64
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

import httpx

# Try to import keyring for secure credential storage
try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

# API base URL - check both env var names for compatibility
API_BASE_URL = os.getenv("API_BASE_URL") or os.getenv("READIN_API_URL", "https://www.getreadin.us")

# Credential storage constants
SERVICE_NAME = "readin-ai"
KEY_NAME = "auth_token"

# Fallback encrypted file storage
TOKEN_FILE = Path.home() / ".readin" / "auth.enc"
SALT_FILE = Path.home() / ".readin" / ".salt"


def _get_machine_key() -> bytes:
    """Generate a machine-specific key for encryption fallback."""
    import platform
    import getpass
    # Combine machine identifiers for a unique key
    machine_id = f"{platform.node()}-{getpass.getuser()}-readin-ai"
    return machine_id.encode('utf-8')


def _get_fernet_key() -> Fernet:
    """Get or create Fernet encryption key for fallback storage."""
    SALT_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Load or create salt
    if SALT_FILE.exists():
        with open(SALT_FILE, 'rb') as f:
            salt = f.read()
    else:
        salt = os.urandom(16)
        with open(SALT_FILE, 'wb') as f:
            f.write(salt)

    # Derive key from machine-specific data
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(_get_machine_key()))
    return Fernet(key)


class APIClient:
    """Client for ReadIn AI backend API."""

    def __init__(self):
        self._token: Optional[str] = None
        self._user_status: Optional[Dict] = None
        self._load_token()

    def _load_token(self):
        """Load saved token from secure storage."""
        try:
            # Try keyring first (most secure)
            if KEYRING_AVAILABLE:
                try:
                    token = keyring.get_password(SERVICE_NAME, KEY_NAME)
                    if token:
                        self._token = token
                        return
                except Exception:
                    pass  # Fall through to encrypted file

            # Fallback to encrypted file storage
            if TOKEN_FILE.exists():
                try:
                    fernet = _get_fernet_key()
                    with open(TOKEN_FILE, "rb") as f:
                        encrypted_data = f.read()
                    decrypted_data = fernet.decrypt(encrypted_data)
                    data = json.loads(decrypted_data.decode('utf-8'))
                    self._token = data.get("access_token")
                except Exception:
                    # If decryption fails, token is invalid
                    self._token = None
        except Exception:
            self._token = None

    def _save_token(self, token: str):
        """Save token to secure storage."""
        try:
            # Try keyring first (most secure)
            if KEYRING_AVAILABLE:
                try:
                    keyring.set_password(SERVICE_NAME, KEY_NAME, token)
                    self._token = token
                    # Clean up any old encrypted file
                    if TOKEN_FILE.exists():
                        try:
                            TOKEN_FILE.unlink()
                        except Exception:
                            pass
                    return
                except Exception:
                    pass  # Fall through to encrypted file

            # Fallback to encrypted file storage
            TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
            fernet = _get_fernet_key()
            data = json.dumps({"access_token": token}).encode('utf-8')
            encrypted_data = fernet.encrypt(data)
            with open(TOKEN_FILE, "wb") as f:
                f.write(encrypted_data)
            self._token = token
        except Exception as e:
            print(f"Failed to save token: {e}")

    def _clear_token(self):
        """Clear saved token from all storage locations."""
        # Clear from keyring
        if KEYRING_AVAILABLE:
            try:
                keyring.delete_password(SERVICE_NAME, KEY_NAME)
            except Exception:
                pass

        # Clear encrypted file
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

    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make API request."""
        url = f"{API_BASE_URL}{endpoint}"
        try:
            with httpx.Client(timeout=30.0) as client:
                if method == "GET":
                    response = client.get(url, headers=self._headers(), params=params)
                elif method == "POST":
                    response = client.post(url, headers=self._headers(), json=data)
                elif method == "PATCH":
                    response = client.patch(url, headers=self._headers(), json=data)
                elif method == "DELETE":
                    response = client.delete(url, headers=self._headers())
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

    def register(
        self,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        account_type: str = "individual",
        company_name: Optional[str] = None
    ) -> Dict:
        """Register a new account."""
        data = {
            "email": email,
            "password": password,
            "full_name": full_name,
            "account_type": account_type
        }
        if account_type == "business" and company_name:
            data["company_name"] = company_name

        result = self._request("POST", "/auth/register", data)
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

    # ============== Profession & Context ==============

    def get_professions(self, category: Optional[str] = None) -> List[Dict]:
        """Get list of professions, optionally filtered by category."""
        params = {"category": category} if category else None
        result = self._request("GET", "/professions", params=params)
        if "error" in result:
            return []
        return result.get("professions", [])

    def get_profession_categories(self) -> List[str]:
        """Get list of profession categories."""
        result = self._request("GET", "/professions/categories")
        if isinstance(result, list):
            return result
        return []

    def get_user_profession_context(self) -> Dict:
        """Get current user's profession context for AI customization."""
        return self._request("GET", "/professions/user/current")

    def update_user_profession(self, profession_id: int, specialization: Optional[str] = None) -> Dict:
        """Update user's profession."""
        data = {"profession_id": profession_id}
        if specialization:
            data["specialization"] = specialization
        return self._request("PATCH", "/professions/user/update", data)

    def get_ai_context(self) -> Dict:
        """Get full AI context including profession and learning profile."""
        return self._request("GET", "/conversations/context")

    # ============== Meetings ==============

    def start_meeting(self, meeting_type: str = "general", title: Optional[str] = None,
                      meeting_app: Optional[str] = None) -> Dict:
        """Start a new meeting session."""
        data = {
            "meeting_type": meeting_type,
            "title": title,
            "meeting_app": meeting_app
        }
        return self._request("POST", "/meetings", data)

    def end_meeting(self, meeting_id: int) -> Dict:
        """End a meeting session and trigger summary generation."""
        return self._request("POST", f"/meetings/{meeting_id}/end")

    def get_active_meeting(self) -> Optional[Dict]:
        """Get user's currently active meeting."""
        result = self._request("GET", "/meetings/active")
        if result is None or (isinstance(result, dict) and "error" in result):
            return None
        return result

    def get_meeting(self, meeting_id: int) -> Dict:
        """Get meeting details with conversations."""
        return self._request("GET", f"/meetings/{meeting_id}")

    def get_meeting_summary(self, meeting_id: int) -> Dict:
        """Get or generate meeting summary."""
        return self._request("GET", f"/meetings/{meeting_id}/summary")

    def generate_meeting_summary(self, meeting_id: int) -> Dict:
        """Explicitly trigger summary generation."""
        return self._request("POST", f"/meetings/{meeting_id}/summary")

    def list_meetings(self, limit: int = 20, meeting_type: Optional[str] = None) -> List[Dict]:
        """List user's meetings."""
        params = {"limit": limit}
        if meeting_type:
            params["meeting_type"] = meeting_type
        result = self._request("GET", "/meetings", params=params)
        if "error" in result:
            return []
        return result.get("meetings", [])

    # ============== Conversations ==============

    def save_conversation(self, meeting_id: int, heard_text: str, response_text: str,
                          speaker: Optional[str] = None) -> Dict:
        """Save a conversation exchange for ML learning."""
        data = {
            "meeting_id": meeting_id,
            "heard_text": heard_text,
            "response_text": response_text,
            "speaker": speaker
        }
        return self._request("POST", "/conversations", data)

    def get_learning_profile(self) -> Dict:
        """Get user's ML learning profile."""
        return self._request("GET", "/conversations/learning-profile")

    def get_topic_analytics(self) -> Dict:
        """Get user's topic frequency analytics."""
        return self._request("GET", "/conversations/topics")

    # ============== Briefings ==============

    def generate_briefing(self, participant_names: List[str] = None,
                          meeting_context: Optional[str] = None,
                          meeting_type: Optional[str] = None) -> Dict:
        """Generate pre-meeting briefing."""
        data = {
            "participant_names": participant_names or [],
            "meeting_context": meeting_context,
            "meeting_type": meeting_type
        }
        return self._request("POST", "/briefings/generate", data)

    def get_participant(self, name: str) -> Optional[Dict]:
        """Get participant memory by name."""
        result = self._request("GET", f"/briefings/participants/by-name/{name}")
        if "error" in result:
            return None
        return result

    def list_participants(self) -> List[Dict]:
        """List all remembered participants."""
        result = self._request("GET", "/briefings/participants")
        if "error" in result:
            return []
        return result.get("participants", result) if isinstance(result, dict) else result

    # ============== Tasks & Commitments ==============

    def get_task_dashboard(self) -> Dict:
        """Get combined action items and commitments dashboard."""
        return self._request("GET", "/tasks/dashboard")

    def get_upcoming_commitments(self) -> List[Dict]:
        """Get upcoming commitment reminders."""
        result = self._request("GET", "/tasks/commitments/upcoming")
        if "error" in result:
            return []
        return result.get("commitments", result) if isinstance(result, dict) else result

    def complete_action_item(self, action_id: int) -> Dict:
        """Mark an action item as complete."""
        return self._request("POST", f"/tasks/action-items/{action_id}/complete")

    def complete_commitment(self, commitment_id: int) -> Dict:
        """Mark a commitment as complete."""
        return self._request("POST", f"/tasks/commitments/{commitment_id}/complete")

    # ============== Job Applications & Interviews ==============

    def list_job_applications(self, status: Optional[str] = None) -> List[Dict]:
        """List job applications."""
        params = {"status": status} if status else None
        result = self._request("GET", "/interviews/applications", params=params)
        if "error" in result:
            return []
        return result.get("applications", result) if isinstance(result, dict) else result

    def create_job_application(self, company: str, position: str, notes: Optional[str] = None) -> Dict:
        """Create a new job application."""
        data = {
            "company": company,
            "position": position,
            "notes": notes
        }
        return self._request("POST", "/interviews/applications", data)

    def get_interview_improvement(self, interview_id: int) -> Dict:
        """Get ML improvement suggestions for an interview."""
        return self._request("GET", f"/interviews/interviews/{interview_id}/improvement")

    def get_interview_analytics(self) -> Dict:
        """Get overall interview performance analytics."""
        return self._request("GET", "/interviews/analytics")


# Global instance
api = APIClient()
