"""
Webhook Signing Service for ReadIn AI.

Implements HMAC-based request signing for secure webhook deliveries.
Recipients can verify that webhooks are genuinely from ReadIn AI.
"""

import hmac
import hashlib
import time
import json
from typing import Dict, Any, Optional, Tuple
from datetime import datetime


# Signature headers
SIGNATURE_HEADER = "X-ReadIn-Signature"
TIMESTAMP_HEADER = "X-ReadIn-Timestamp"
SIGNATURE_VERSION = "v1"

# Signature validity window (5 minutes)
SIGNATURE_VALIDITY_SECONDS = 300


def generate_webhook_secret() -> str:
    """Generate a secure webhook secret."""
    import secrets
    return f"whsec_{secrets.token_urlsafe(32)}"


def sign_webhook_payload(
    payload: Dict[str, Any],
    secret: str,
    timestamp: Optional[int] = None
) -> Tuple[str, int]:
    """
    Sign a webhook payload using HMAC-SHA256.

    Args:
        payload: The webhook payload to sign
        secret: The webhook secret
        timestamp: Unix timestamp (defaults to current time)

    Returns:
        Tuple of (signature, timestamp)

    Signature format: v1=<hmac_sha256_hex>
    """
    if timestamp is None:
        timestamp = int(time.time())

    # Create the signed payload string
    # Format: timestamp.json_payload
    payload_json = json.dumps(payload, separators=(',', ':'), sort_keys=True)
    signed_payload = f"{timestamp}.{payload_json}"

    # Generate HMAC-SHA256 signature
    signature = hmac.new(
        secret.encode('utf-8'),
        signed_payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return f"{SIGNATURE_VERSION}={signature}", timestamp


def verify_webhook_signature(
    payload: str,
    signature: str,
    timestamp: str,
    secret: str,
    tolerance: int = SIGNATURE_VALIDITY_SECONDS
) -> Tuple[bool, Optional[str]]:
    """
    Verify a webhook signature.

    Args:
        payload: The raw payload string
        signature: The X-ReadIn-Signature header value
        timestamp: The X-ReadIn-Timestamp header value
        secret: The webhook secret
        tolerance: Maximum age of signature in seconds

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Parse timestamp
        try:
            ts = int(timestamp)
        except ValueError:
            return False, "Invalid timestamp format"

        # Check timestamp age
        current_time = int(time.time())
        if abs(current_time - ts) > tolerance:
            return False, f"Timestamp too old (>{tolerance}s)"

        # Parse signature version
        if not signature.startswith(f"{SIGNATURE_VERSION}="):
            return False, f"Invalid signature version (expected {SIGNATURE_VERSION})"

        expected_sig_value = signature.split("=", 1)[1]

        # Recreate the signed payload
        signed_payload = f"{ts}.{payload}"

        # Compute expected signature
        computed_signature = hmac.new(
            secret.encode('utf-8'),
            signed_payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        # Constant-time comparison
        if hmac.compare_digest(expected_sig_value, computed_signature):
            return True, None
        else:
            return False, "Signature mismatch"

    except Exception as e:
        return False, f"Verification error: {str(e)}"


def create_webhook_headers(
    payload: Dict[str, Any],
    secret: str,
    custom_headers: Optional[Dict[str, str]] = None
) -> Dict[str, str]:
    """
    Create headers for a webhook request including signature.

    Args:
        payload: The webhook payload
        secret: The webhook secret
        custom_headers: Additional custom headers

    Returns:
        Dict of headers to include in the request
    """
    signature, timestamp = sign_webhook_payload(payload, secret)

    headers = {
        "Content-Type": "application/json",
        SIGNATURE_HEADER: signature,
        TIMESTAMP_HEADER: str(timestamp),
        "User-Agent": "ReadIn-Webhook/1.0",
    }

    if custom_headers:
        headers.update(custom_headers)

    return headers


class WebhookSignatureVerifier:
    """
    Helper class for verifying incoming webhooks.

    Use this when receiving webhooks from external services.
    """

    def __init__(self, secret: str, tolerance: int = SIGNATURE_VALIDITY_SECONDS):
        self.secret = secret
        self.tolerance = tolerance

    def verify(
        self,
        payload: str,
        signature: str,
        timestamp: str
    ) -> bool:
        """Verify a webhook signature. Raises ValueError if invalid."""
        is_valid, error = verify_webhook_signature(
            payload=payload,
            signature=signature,
            timestamp=timestamp,
            secret=self.secret,
            tolerance=self.tolerance
        )

        if not is_valid:
            raise ValueError(f"Invalid webhook signature: {error}")

        return True

    def verify_request(
        self,
        body: bytes,
        headers: Dict[str, str]
    ) -> bool:
        """
        Verify a webhook request from headers and body.

        Args:
            body: Raw request body bytes
            headers: Request headers dict

        Returns:
            True if valid

        Raises:
            ValueError: If signature is invalid
        """
        signature = headers.get(SIGNATURE_HEADER)
        timestamp = headers.get(TIMESTAMP_HEADER)

        if not signature:
            raise ValueError(f"Missing {SIGNATURE_HEADER} header")
        if not timestamp:
            raise ValueError(f"Missing {TIMESTAMP_HEADER} header")

        return self.verify(
            payload=body.decode('utf-8'),
            signature=signature,
            timestamp=timestamp
        )


# Stripe-compatible signature format for receiving Stripe webhooks
def verify_stripe_signature(
    payload: str,
    signature_header: str,
    secret: str,
    tolerance: int = 300
) -> bool:
    """
    Verify a Stripe webhook signature.

    Stripe uses: t=timestamp,v1=signature format
    """
    try:
        # Parse Stripe signature header
        elements = {}
        for element in signature_header.split(","):
            key, value = element.split("=", 1)
            elements[key] = value

        timestamp = elements.get("t")
        signatures = [v for k, v in elements.items() if k.startswith("v")]

        if not timestamp or not signatures:
            return False

        # Check timestamp
        ts = int(timestamp)
        if abs(int(time.time()) - ts) > tolerance:
            return False

        # Compute expected signature
        signed_payload = f"{timestamp}.{payload}"
        expected_sig = hmac.new(
            secret.encode('utf-8'),
            signed_payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        # Check against any provided signature
        return any(
            hmac.compare_digest(expected_sig, sig)
            for sig in signatures
        )

    except Exception:
        return False
