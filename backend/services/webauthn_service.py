"""
WebAuthn/FIDO2 Service for hardware key authentication.

Supports:
- YubiKey
- Windows Hello
- Touch ID
- Other FIDO2 compliant authenticators
"""

import secrets
import base64
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any

try:
    from webauthn import (
        generate_registration_options,
        verify_registration_response,
        generate_authentication_options,
        verify_authentication_response,
        options_to_json,
    )
    from webauthn.helpers.base64url import (
        bytes_to_base64url,
        base64url_to_bytes,
    )
    from webauthn.helpers.structs import (
        AuthenticatorSelectionCriteria,
        UserVerificationRequirement,
        ResidentKeyRequirement,
        PublicKeyCredentialDescriptor,
        AuthenticatorTransport,
        RegistrationCredential,
        AuthenticationCredential,
    )
    WEBAUTHN_AVAILABLE = True
except ImportError:
    # WebAuthn not available - provide stub
    WEBAUTHN_AVAILABLE = False
    def bytes_to_base64url(val: bytes) -> str:
        import base64
        return base64.urlsafe_b64encode(val).rstrip(b'=').decode('utf-8')
    def base64url_to_bytes(val: str) -> bytes:
        import base64
        padding = 4 - len(val) % 4
        if padding != 4:
            val += '=' * padding
        return base64.urlsafe_b64decode(val)
from sqlalchemy.orm import Session

from config import APP_NAME, APP_URL


# =============================================================================
# CONFIGURATION
# =============================================================================

# Relying Party (RP) configuration
RP_ID = APP_URL.replace("https://", "").replace("http://", "").split(":")[0]
RP_NAME = APP_NAME
RP_ORIGIN = APP_URL

# For development, allow localhost
import os
if os.getenv("ENVIRONMENT", "development") == "development":
    RP_ID = "localhost"
    RP_ORIGIN = "http://localhost:3000"


# =============================================================================
# WEBAUTHN SERVICE CLASS
# =============================================================================

class WebAuthnService:
    """Service for handling WebAuthn/FIDO2 registration and authentication."""

    def __init__(self, db: Session):
        self.db = db

    # =========================================================================
    # REGISTRATION CEREMONY
    # =========================================================================

    def generate_registration_challenge(
        self,
        user_id: int,
        user_email: str,
        user_name: str,
        exclude_credentials: List[bytes] = None
    ) -> Tuple[Dict[str, Any], bytes]:
        """
        Generate registration options for WebAuthn credential creation.

        Args:
            user_id: The internal user ID
            user_email: User's email address
            user_name: User's display name
            exclude_credentials: List of existing credential IDs to exclude

        Returns:
            Tuple of (registration_options_dict, challenge_bytes)
        """
        # Generate a random challenge
        challenge = secrets.token_bytes(32)

        # Build list of credentials to exclude (prevent duplicate registrations)
        exclude_descriptors = []
        if exclude_credentials:
            for cred_id in exclude_credentials:
                exclude_descriptors.append(
                    PublicKeyCredentialDescriptor(
                        id=cred_id,
                        transports=[
                            AuthenticatorTransport.USB,
                            AuthenticatorTransport.NFC,
                            AuthenticatorTransport.BLE,
                            AuthenticatorTransport.INTERNAL,
                        ]
                    )
                )

        # Generate registration options
        options = generate_registration_options(
            rp_id=RP_ID,
            rp_name=RP_NAME,
            user_id=str(user_id).encode('utf-8'),
            user_name=user_email,
            user_display_name=user_name or user_email,
            challenge=challenge,
            exclude_credentials=exclude_descriptors if exclude_descriptors else None,
            authenticator_selection=AuthenticatorSelectionCriteria(
                user_verification=UserVerificationRequirement.PREFERRED,
                resident_key=ResidentKeyRequirement.DISCOURAGED,
            ),
            timeout=60000,  # 60 seconds
        )

        # Convert to JSON-serializable dict
        options_json = options_to_json(options)

        return options_json, challenge

    def verify_registration_credential(
        self,
        credential_response: Dict[str, Any],
        expected_challenge: bytes,
        user_id: int
    ) -> Tuple[bytes, bytes, int]:
        """
        Verify the registration response from the authenticator.

        Args:
            credential_response: The credential response from the client
            expected_challenge: The challenge that was sent to the client
            user_id: The user ID for verification

        Returns:
            Tuple of (credential_id, public_key, sign_count)

        Raises:
            Exception if verification fails
        """
        # Build the registration credential object
        credential = RegistrationCredential(
            id=credential_response['id'],
            raw_id=base64url_to_bytes(credential_response['rawId']),
            response={
                'client_data_json': base64url_to_bytes(
                    credential_response['response']['clientDataJSON']
                ),
                'attestation_object': base64url_to_bytes(
                    credential_response['response']['attestationObject']
                ),
            },
            type=credential_response.get('type', 'public-key'),
        )

        # Verify the registration
        verification = verify_registration_response(
            credential=credential,
            expected_challenge=expected_challenge,
            expected_rp_id=RP_ID,
            expected_origin=RP_ORIGIN,
            require_user_verification=False,  # Allow authenticators without UV
        )

        # Extract credential data
        credential_id = verification.credential_id
        public_key = verification.credential_public_key
        sign_count = verification.sign_count

        return credential_id, public_key, sign_count

    # =========================================================================
    # AUTHENTICATION CEREMONY
    # =========================================================================

    def generate_authentication_challenge(
        self,
        allowed_credentials: List[bytes] = None
    ) -> Tuple[Dict[str, Any], bytes]:
        """
        Generate authentication options for WebAuthn assertion.

        Args:
            allowed_credentials: List of credential IDs that can be used for auth

        Returns:
            Tuple of (authentication_options_dict, challenge_bytes)
        """
        # Generate a random challenge
        challenge = secrets.token_bytes(32)

        # Build list of allowed credentials
        allow_descriptors = []
        if allowed_credentials:
            for cred_id in allowed_credentials:
                allow_descriptors.append(
                    PublicKeyCredentialDescriptor(
                        id=cred_id,
                        transports=[
                            AuthenticatorTransport.USB,
                            AuthenticatorTransport.NFC,
                            AuthenticatorTransport.BLE,
                            AuthenticatorTransport.INTERNAL,
                        ]
                    )
                )

        # Generate authentication options
        options = generate_authentication_options(
            rp_id=RP_ID,
            challenge=challenge,
            allow_credentials=allow_descriptors if allow_descriptors else None,
            user_verification=UserVerificationRequirement.PREFERRED,
            timeout=60000,  # 60 seconds
        )

        # Convert to JSON-serializable dict
        options_json = options_to_json(options)

        return options_json, challenge

    def verify_authentication_credential(
        self,
        credential_response: Dict[str, Any],
        expected_challenge: bytes,
        credential_public_key: bytes,
        credential_current_sign_count: int,
        credential_id: bytes
    ) -> int:
        """
        Verify the authentication response from the authenticator.

        Args:
            credential_response: The credential response from the client
            expected_challenge: The challenge that was sent to the client
            credential_public_key: The stored public key for this credential
            credential_current_sign_count: The stored sign count for this credential
            credential_id: The credential ID being authenticated

        Returns:
            New sign count to store

        Raises:
            Exception if verification fails
        """
        # Build the authentication credential object
        credential = AuthenticationCredential(
            id=credential_response['id'],
            raw_id=base64url_to_bytes(credential_response['rawId']),
            response={
                'client_data_json': base64url_to_bytes(
                    credential_response['response']['clientDataJSON']
                ),
                'authenticator_data': base64url_to_bytes(
                    credential_response['response']['authenticatorData']
                ),
                'signature': base64url_to_bytes(
                    credential_response['response']['signature']
                ),
                'user_handle': base64url_to_bytes(
                    credential_response['response']['userHandle']
                ) if credential_response['response'].get('userHandle') else None,
            },
            type=credential_response.get('type', 'public-key'),
        )

        # Verify the authentication
        verification = verify_authentication_response(
            credential=credential,
            expected_challenge=expected_challenge,
            expected_rp_id=RP_ID,
            expected_origin=RP_ORIGIN,
            credential_public_key=credential_public_key,
            credential_current_sign_count=credential_current_sign_count,
            require_user_verification=False,
        )

        return verification.new_sign_count

    # =========================================================================
    # CREDENTIAL MANAGEMENT
    # =========================================================================

    def get_user_credentials(self, user_id: int) -> List['WebAuthnCredential']:
        """Get all WebAuthn credentials for a user."""
        from models import WebAuthnCredential
        return self.db.query(WebAuthnCredential).filter(
            WebAuthnCredential.user_id == user_id,
            WebAuthnCredential.is_active == True
        ).all()

    def get_credential_by_id(self, credential_id: bytes) -> Optional['WebAuthnCredential']:
        """Get a specific WebAuthn credential by its ID."""
        from models import WebAuthnCredential
        credential_id_b64 = bytes_to_base64url(credential_id)
        return self.db.query(WebAuthnCredential).filter(
            WebAuthnCredential.credential_id == credential_id_b64,
            WebAuthnCredential.is_active == True
        ).first()

    def save_credential(
        self,
        user_id: int,
        credential_id: bytes,
        public_key: bytes,
        sign_count: int,
        device_name: Optional[str] = None
    ) -> 'WebAuthnCredential':
        """Save a new WebAuthn credential."""
        from models import WebAuthnCredential

        credential = WebAuthnCredential(
            user_id=user_id,
            credential_id=bytes_to_base64url(credential_id),
            public_key=bytes_to_base64url(public_key),
            sign_count=sign_count,
            device_name=device_name or "Security Key",
            is_active=True,
        )
        self.db.add(credential)
        self.db.commit()
        self.db.refresh(credential)

        return credential

    def update_sign_count(self, credential_id: bytes, new_sign_count: int) -> None:
        """Update the sign count for a credential after successful authentication."""
        from models import WebAuthnCredential
        credential_id_b64 = bytes_to_base64url(credential_id)
        credential = self.db.query(WebAuthnCredential).filter(
            WebAuthnCredential.credential_id == credential_id_b64
        ).first()

        if credential:
            credential.sign_count = new_sign_count
            credential.last_used_at = datetime.utcnow()
            self.db.commit()

    def delete_credential(self, credential_id: int, user_id: int) -> bool:
        """Soft delete a WebAuthn credential."""
        from models import WebAuthnCredential
        credential = self.db.query(WebAuthnCredential).filter(
            WebAuthnCredential.id == credential_id,
            WebAuthnCredential.user_id == user_id
        ).first()

        if credential:
            credential.is_active = False
            self.db.commit()
            return True
        return False

    def rename_credential(self, credential_id: int, user_id: int, new_name: str) -> bool:
        """Rename a WebAuthn credential."""
        from models import WebAuthnCredential
        credential = self.db.query(WebAuthnCredential).filter(
            WebAuthnCredential.id == credential_id,
            WebAuthnCredential.user_id == user_id,
            WebAuthnCredential.is_active == True
        ).first()

        if credential:
            credential.device_name = new_name
            self.db.commit()
            return True
        return False


# =============================================================================
# CHALLENGE STORE
# =============================================================================

class ChallengeStore:
    """
    In-memory store for WebAuthn challenges.

    In production, this should use Redis or a similar distributed cache
    with automatic expiration.
    """

    _challenges: Dict[str, Tuple[bytes, datetime]] = {}
    _challenge_ttl_seconds = 300  # 5 minutes

    @classmethod
    def store_challenge(cls, key: str, challenge: bytes) -> None:
        """Store a challenge with the given key."""
        cls._cleanup_expired()
        cls._challenges[key] = (challenge, datetime.utcnow())

    @classmethod
    def get_challenge(cls, key: str) -> Optional[bytes]:
        """Get and remove a challenge by its key."""
        cls._cleanup_expired()
        data = cls._challenges.pop(key, None)
        if data:
            challenge, created_at = data
            # Check if expired
            age = (datetime.utcnow() - created_at).total_seconds()
            if age < cls._challenge_ttl_seconds:
                return challenge
        return None

    @classmethod
    def _cleanup_expired(cls) -> None:
        """Remove expired challenges."""
        now = datetime.utcnow()
        expired_keys = [
            key for key, (_, created_at) in cls._challenges.items()
            if (now - created_at).total_seconds() > cls._challenge_ttl_seconds
        ]
        for key in expired_keys:
            cls._challenges.pop(key, None)
