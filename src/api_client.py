"""API client for ReadIn AI backend."""

import json
import os
import sys
import base64
import time
import hmac
import hashlib
import uuid
import logging
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from datetime import datetime, timezone
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from functools import wraps

import httpx

logger = logging.getLogger(__name__)

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

# Encryption version for future migration support
ENCRYPTION_VERSION = 1

# Token expiration settings (in seconds)
TOKEN_EXPIRY_BUFFER = 300  # Refresh token if expiring within 5 minutes

# Retry settings
MAX_RETRIES = 3
INITIAL_BACKOFF = 1.0  # seconds
MAX_BACKOFF = 30.0  # seconds
BACKOFF_MULTIPLIER = 2.0

# Timeout settings per operation type (in seconds)
TIMEOUT_CONFIG = {
    "default": 30.0,
    "auth": 15.0,
    "upload": 120.0,
    "download": 60.0,
    "quick": 10.0,
}

# Retryable HTTP status codes
RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}


# ============== Custom Exceptions ==============

class APIClientError(Exception):
    """Base exception for API client errors."""
    pass


class AuthenticationError(APIClientError):
    """Raised when authentication fails or token is invalid."""
    pass


class TokenExpiredError(AuthenticationError):
    """Raised when the auth token has expired."""
    pass


class TokenRefreshError(AuthenticationError):
    """Raised when token refresh fails."""
    pass


class ConnectionError(APIClientError):
    """Raised when connection to the server fails."""
    pass


class TimeoutError(APIClientError):
    """Raised when a request times out."""
    pass


class RateLimitError(APIClientError):
    """Raised when rate limited by the server."""
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after


class ServerError(APIClientError):
    """Raised when the server returns a 5xx error."""
    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code


class ValidationError(APIClientError):
    """Raised when request validation fails."""
    pass


class EncryptionError(APIClientError):
    """Raised when encryption/decryption fails."""
    pass


def _set_file_permissions(file_path: Path):
    """Set secure file permissions (0o600 - owner read/write only)."""
    try:
        if sys.platform == 'win32':
            # On Windows, use icacls to set permissions
            import subprocess
            # Remove inherited permissions and set owner full control only
            subprocess.run(
                ['icacls', str(file_path), '/inheritance:r', '/grant:r', f'{os.environ.get("USERNAME", "SYSTEM")}:F'],
                capture_output=True,
                check=False
            )
        else:
            # On Unix-like systems, use chmod
            os.chmod(file_path, 0o600)
    except Exception:
        # Best effort - don't fail if permissions can't be set
        pass


def _get_machine_key() -> bytes:
    """Generate a machine-specific key for encryption fallback.

    Uses stable machine identifiers that won't change with user sessions.
    """
    import platform

    identifiers = []

    # 1. Try to get hardware UUID (most stable)
    try:
        if sys.platform == 'win32':
            import subprocess
            result = subprocess.run(
                ['wmic', 'csproduct', 'get', 'UUID'],
                capture_output=True, text=True, check=False
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    uuid_val = lines[1].strip()
                    if uuid_val and uuid_val != 'UUID':
                        identifiers.append(uuid_val)
        elif sys.platform == 'darwin':
            import subprocess
            result = subprocess.run(
                ['system_profiler', 'SPHardwareDataType'],
                capture_output=True, text=True, check=False
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'Hardware UUID' in line:
                        uuid_val = line.split(':')[1].strip()
                        identifiers.append(uuid_val)
                        break
        else:  # Linux
            machine_id_paths = ['/etc/machine-id', '/var/lib/dbus/machine-id']
            for path in machine_id_paths:
                try:
                    with open(path, 'r') as f:
                        identifiers.append(f.read().strip())
                    break
                except FileNotFoundError:
                    continue
    except Exception:
        pass

    # 2. Fallback to platform node (hostname-based, less stable but available)
    identifiers.append(platform.node())

    # 3. Add a constant app identifier
    identifiers.append("readin-ai-desktop-v1")

    # Combine all identifiers
    machine_id = "-".join(filter(None, identifiers))
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
        _set_file_permissions(SALT_FILE)

    # Derive key from machine-specific data
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(_get_machine_key()))
    return Fernet(key)


def _parse_jwt_payload(token: str) -> Optional[Dict]:
    """Parse JWT token payload without verification (for expiry check)."""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None

        # Decode payload (middle part)
        payload_b64 = parts[1]
        # Add padding if needed
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += '=' * padding

        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        return json.loads(payload_bytes.decode('utf-8'))
    except Exception:
        return None


def _is_token_expired(token: str, buffer_seconds: int = 0) -> bool:
    """Check if a JWT token is expired or will expire within buffer_seconds."""
    payload = _parse_jwt_payload(token)
    if not payload:
        return True

    exp = payload.get('exp')
    if not exp:
        return False  # No expiry means it doesn't expire

    current_time = datetime.now(timezone.utc).timestamp()
    return current_time >= (exp - buffer_seconds)


def _get_token_expiry(token: str) -> Optional[datetime]:
    """Get the expiry datetime of a JWT token."""
    payload = _parse_jwt_payload(token)
    if not payload:
        return None

    exp = payload.get('exp')
    if not exp:
        return None

    return datetime.fromtimestamp(exp, tz=timezone.utc)


class APIClient:
    """Client for ReadIn AI backend API."""

    def __init__(self):
        self._token: Optional[str] = None
        self._user_status: Optional[Dict] = None
        self._request_signing_key: Optional[bytes] = None
        self._load_token()

    def _load_token(self):
        """Load saved token from secure storage."""
        try:
            # Try keyring first (most secure)
            if KEYRING_AVAILABLE:
                try:
                    token = keyring.get_password(SERVICE_NAME, KEY_NAME)
                    if token:
                        # Validate token before using
                        if not _is_token_expired(token):
                            self._token = token
                            return
                        elif not _is_token_expired(token, buffer_seconds=86400):
                            # Token expired but within 24 hours - try to use it
                            # Server will return 401 if truly invalid
                            self._token = token
                            return
                        # Token is too old, clear it
                        self._clear_token()
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

                    # Check version for future migration
                    version = data.get("version", 0)
                    if version > ENCRYPTION_VERSION:
                        # Future version - can't read, clear it
                        self._clear_token()
                        return

                    token = data.get("access_token")
                    if token:
                        # Validate token before using
                        if not _is_token_expired(token):
                            self._token = token
                        elif not _is_token_expired(token, buffer_seconds=86400):
                            # Token expired but within 24 hours - try to use it
                            self._token = token
                        else:
                            # Token is too old, clear it
                            self._clear_token()
                except InvalidToken:
                    # Encryption key changed or data corrupted
                    self._clear_token()
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
            data = json.dumps({
                "version": ENCRYPTION_VERSION,
                "access_token": token,
                "saved_at": datetime.now(timezone.utc).isoformat()
            }).encode('utf-8')
            encrypted_data = fernet.encrypt(data)
            with open(TOKEN_FILE, "wb") as f:
                f.write(encrypted_data)
            _set_file_permissions(TOKEN_FILE)
            self._token = token
        except Exception as e:
            logger.error(f"Failed to save token: {e}")

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

    def _validate_token(self) -> Tuple[bool, Optional[str]]:
        """Validate current token and determine if refresh is needed.

        Returns:
            Tuple of (is_valid, action_needed)
            action_needed can be: None, "refresh", "reauth"
        """
        if not self._token:
            return False, "reauth"

        if _is_token_expired(self._token):
            return False, "reauth"

        if _is_token_expired(self._token, buffer_seconds=TOKEN_EXPIRY_BUFFER):
            return True, "refresh"

        return True, None

    def _try_refresh_token(self) -> bool:
        """Attempt to refresh the current token.

        Returns True if refresh was successful, False otherwise.
        """
        if not self._token:
            return False

        try:
            # Try to refresh using the current token
            result = self._request_internal(
                "POST", "/api/v1/auth/refresh",
                timeout_type="auth",
                skip_token_validation=True
            )
            if "access_token" in result:
                self._save_token(result["access_token"])
                return True
        except Exception:
            pass

        return False

    def _headers(self) -> Dict[str, str]:
        """Get request headers with auth token."""
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def _sign_request(self, method: str, endpoint: str, timestamp: str, body: Optional[str] = None) -> str:
        """Generate HMAC signature for request.

        Args:
            method: HTTP method
            endpoint: API endpoint
            timestamp: ISO format timestamp
            body: Request body as string (or None)

        Returns:
            Base64 encoded HMAC-SHA256 signature
        """
        # Derive a signing key using PBKDF2 for security
        # Never use raw token as signing key
        if self._token:
            # Use a consistent salt derived from the token itself
            token_bytes = self._token.encode('utf-8')
            salt = hashlib.sha256(token_bytes[:32] if len(token_bytes) > 32 else token_bytes).digest()[:16]
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            signing_key = kdf.derive(token_bytes)
        else:
            signing_key = _get_machine_key()

        # Create message to sign
        body_hash = hashlib.sha256((body or "").encode('utf-8')).hexdigest()
        message = f"{method}:{endpoint}:{timestamp}:{body_hash}"

        # Generate HMAC
        signature = hmac.new(
            signing_key,
            message.encode('utf-8'),
            hashlib.sha256
        ).digest()

        return base64.b64encode(signature).decode('utf-8')

    def _add_request_signature(self, headers: Dict[str, str], method: str,
                                endpoint: str, body: Optional[str] = None) -> Dict[str, str]:
        """Add request signature headers."""
        timestamp = datetime.now(timezone.utc).isoformat()
        signature = self._sign_request(method, endpoint, timestamp, body)

        headers["X-Request-Timestamp"] = timestamp
        headers["X-Request-Signature"] = signature
        headers["X-Request-Id"] = str(uuid.uuid4())

        return headers

    def _request_internal(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        timeout_type: str = "default",
        skip_token_validation: bool = False
    ) -> Dict[str, Any]:
        """Internal request method without retry logic."""
        url = f"{API_BASE_URL}{endpoint}"
        timeout = TIMEOUT_CONFIG.get(timeout_type, TIMEOUT_CONFIG["default"])

        headers = self._headers()
        body_str = json.dumps(data) if data else None

        # Add request signature
        headers = self._add_request_signature(headers, method, endpoint, body_str)

        try:
            with httpx.Client(timeout=timeout) as client:
                if method == "GET":
                    response = client.get(url, headers=headers, params=params)
                elif method == "POST":
                    response = client.post(url, headers=headers, json=data)
                elif method == "PATCH":
                    response = client.patch(url, headers=headers, json=data)
                elif method == "DELETE":
                    response = client.delete(url, headers=headers)
                else:
                    raise ValueError(f"Unknown method: {method}")

                # Handle specific status codes
                if response.status_code == 401:
                    # For auth endpoints, 401 means invalid credentials - don't clear token
                    if endpoint.startswith("/api/v1/auth/"):
                        try:
                            error_data = response.json()
                            error_msg = error_data.get("detail", "Invalid credentials")
                        except Exception:
                            error_msg = "Invalid credentials"
                        raise ValidationError(error_msg)
                    else:
                        # For other endpoints, clear token and re-auth
                        self._clear_token()
                        raise AuthenticationError("Authentication failed. Please log in again.")

                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    retry_seconds = int(retry_after) if retry_after else None
                    raise RateLimitError("Rate limit exceeded", retry_after=retry_seconds)

                if response.status_code >= 500:
                    raise ServerError(
                        f"Server error: {response.status_code}",
                        status_code=response.status_code
                    )

                if response.status_code >= 400:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("detail", "Request failed")
                    except Exception:
                        error_msg = f"Request failed: {response.status_code}"
                    raise ValidationError(error_msg)

                return response.json()

        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to server: {e}")
        except httpx.TimeoutException as e:
            raise TimeoutError(f"Request timed out: {e}")
        except APIClientError:
            raise
        except Exception as e:
            raise APIClientError(f"Request failed: {e}")

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        timeout_type: str = "default"
    ) -> Dict[str, Any]:
        """Make API request with retry logic and token validation."""

        # Check token validity before making request (for authenticated endpoints)
        if self._token and not endpoint.startswith("/api/v1/auth/"):
            is_valid, action = self._validate_token()

            if action == "reauth":
                self._clear_token()
                return {"error": "unauthorized", "message": "Session expired. Please log in again."}

            if action == "refresh":
                # Try to refresh token in background
                self._try_refresh_token()

        last_error = None
        backoff = INITIAL_BACKOFF

        for attempt in range(MAX_RETRIES):
            try:
                return self._request_internal(method, endpoint, data, params, timeout_type)

            except RateLimitError as e:
                # Use server-specified retry time or exponential backoff
                wait_time = e.retry_after if e.retry_after else backoff
                if attempt < MAX_RETRIES - 1:
                    time.sleep(wait_time)
                    backoff = min(backoff * BACKOFF_MULTIPLIER, MAX_BACKOFF)
                last_error = e

            except ServerError as e:
                # Retry on server errors
                if e.status_code in RETRYABLE_STATUS_CODES and attempt < MAX_RETRIES - 1:
                    time.sleep(backoff)
                    backoff = min(backoff * BACKOFF_MULTIPLIER, MAX_BACKOFF)
                    last_error = e
                else:
                    return {"error": "server", "message": str(e)}

            except (ConnectionError, TimeoutError) as e:
                # Retry on connection/timeout errors
                if attempt < MAX_RETRIES - 1:
                    time.sleep(backoff)
                    backoff = min(backoff * BACKOFF_MULTIPLIER, MAX_BACKOFF)
                    last_error = e
                else:
                    error_type = "connection" if isinstance(e, ConnectionError) else "timeout"
                    return {"error": error_type, "message": str(e)}

            except AuthenticationError:
                return {"error": "unauthorized", "message": "Please log in again"}

            except ValidationError as e:
                return {"error": True, "message": str(e)}

            except APIClientError as e:
                return {"error": "unknown", "message": str(e)}

        # All retries exhausted
        if last_error:
            return {"error": "unknown", "message": f"Request failed after {MAX_RETRIES} attempts: {last_error}"}
        return {"error": "unknown", "message": "Request failed"}

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

        result = self._request("POST", "/api/v1/auth/register", data, timeout_type="auth")
        if "access_token" in result:
            self._save_token(result["access_token"])
        return result

    def login(self, email: str, password: str) -> Dict:
        """Login and get token."""
        result = self._request("POST", "/api/v1/auth/login", {
            "email": email,
            "password": password
        }, timeout_type="auth")
        if "access_token" in result:
            self._save_token(result["access_token"])
        return result

    def logout(self):
        """Logout - clear local token."""
        self._clear_token()
        self._user_status = None

    def is_logged_in(self) -> bool:
        """Check if user has a valid (non-expired) token."""
        if not self._token:
            return False
        return not _is_token_expired(self._token)

    def get_token_expiry(self) -> Optional[datetime]:
        """Get the expiry time of the current token."""
        if not self._token:
            return None
        return _get_token_expiry(self._token)

    def refresh_token(self) -> bool:
        """Manually refresh the auth token.

        Returns True if successful, False otherwise.
        """
        return self._try_refresh_token()

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
