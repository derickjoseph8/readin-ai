"""User-friendly error messages with actionable suggestions."""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class ErrorAction(Enum):
    """Actions that can be taken in response to an error."""
    RETRY = "retry"
    LOGIN = "login"
    UPGRADE = "upgrade"
    SETTINGS = "settings"
    RECONNECT = "reconnect"
    RESTART = "restart"
    CONTACT_SUPPORT = "contact_support"
    IGNORE = "ignore"
    UPDATE = "update"


@dataclass
class ErrorInfo:
    """Structured error information."""
    code: str
    title: str
    message: str
    suggestion: str
    action: ErrorAction
    icon: str = "error"  # error, warning, info
    is_recoverable: bool = True


# Error catalog
ERRORS: Dict[str, ErrorInfo] = {
    # Network errors
    "connection_failed": ErrorInfo(
        code="NET001",
        title="Connection Failed",
        message="Cannot connect to the server.",
        suggestion="Check your internet connection and try again.",
        action=ErrorAction.RETRY,
        icon="error",
        is_recoverable=True
    ),
    "connection_timeout": ErrorInfo(
        code="NET002",
        title="Connection Timeout",
        message="The server took too long to respond.",
        suggestion="Try again in a moment. If the problem persists, check your network.",
        action=ErrorAction.RETRY,
        icon="warning",
        is_recoverable=True
    ),
    "server_unavailable": ErrorInfo(
        code="NET003",
        title="Service Unavailable",
        message="ReadIn AI servers are temporarily unavailable.",
        suggestion="Please wait a few minutes and try again.",
        action=ErrorAction.RETRY,
        icon="warning",
        is_recoverable=True
    ),

    # Authentication errors
    "auth_expired": ErrorInfo(
        code="AUTH001",
        title="Session Expired",
        message="Your login session has expired.",
        suggestion="Please log in again to continue using ReadIn AI.",
        action=ErrorAction.LOGIN,
        icon="warning",
        is_recoverable=True
    ),
    "auth_invalid": ErrorInfo(
        code="AUTH002",
        title="Invalid Credentials",
        message="The email or password you entered is incorrect.",
        suggestion="Please check your credentials and try again.",
        action=ErrorAction.LOGIN,
        icon="error",
        is_recoverable=True
    ),
    "auth_required": ErrorInfo(
        code="AUTH003",
        title="Login Required",
        message="You need to be logged in to use this feature.",
        suggestion="Please log in to continue.",
        action=ErrorAction.LOGIN,
        icon="info",
        is_recoverable=True
    ),

    # Usage/subscription errors
    "trial_limit_reached": ErrorInfo(
        code="SUB001",
        title="Daily Limit Reached",
        message="You've used all your free responses for today.",
        suggestion="Upgrade to Premium for unlimited responses, or wait until tomorrow.",
        action=ErrorAction.UPGRADE,
        icon="warning",
        is_recoverable=True
    ),
    "trial_expired": ErrorInfo(
        code="SUB002",
        title="Trial Expired",
        message="Your 7-day free trial has ended.",
        suggestion="Upgrade to Premium to continue using ReadIn AI.",
        action=ErrorAction.UPGRADE,
        icon="info",
        is_recoverable=True
    ),
    "subscription_expired": ErrorInfo(
        code="SUB003",
        title="Subscription Expired",
        message="Your Premium subscription has expired.",
        suggestion="Renew your subscription to continue with unlimited responses.",
        action=ErrorAction.UPGRADE,
        icon="warning",
        is_recoverable=True
    ),
    "payment_failed": ErrorInfo(
        code="SUB004",
        title="Payment Failed",
        message="We couldn't process your payment.",
        suggestion="Please update your payment method to continue.",
        action=ErrorAction.UPGRADE,
        icon="error",
        is_recoverable=True
    ),

    # Audio errors
    "audio_device_not_found": ErrorInfo(
        code="AUD001",
        title="No Audio Device",
        message="No audio input device was found.",
        suggestion="Connect a microphone or enable Stereo Mix in your sound settings.",
        action=ErrorAction.SETTINGS,
        icon="error",
        is_recoverable=True
    ),
    "audio_device_busy": ErrorInfo(
        code="AUD002",
        title="Audio Device Busy",
        message="The audio device is being used by another application.",
        suggestion="Close other apps using the microphone and try again.",
        action=ErrorAction.RETRY,
        icon="warning",
        is_recoverable=True
    ),
    "audio_permission_denied": ErrorInfo(
        code="AUD003",
        title="Microphone Access Denied",
        message="ReadIn AI doesn't have permission to access your microphone.",
        suggestion="Allow microphone access in your system privacy settings.",
        action=ErrorAction.SETTINGS,
        icon="error",
        is_recoverable=True
    ),
    "audio_capture_failed": ErrorInfo(
        code="AUD004",
        title="Audio Capture Failed",
        message="Could not start audio capture.",
        suggestion="Try selecting a different audio device in Settings.",
        action=ErrorAction.SETTINGS,
        icon="error",
        is_recoverable=True
    ),

    # AI errors
    "ai_rate_limit": ErrorInfo(
        code="AI001",
        title="AI Rate Limited",
        message="Too many requests to the AI service.",
        suggestion="Please wait a moment before trying again.",
        action=ErrorAction.RETRY,
        icon="warning",
        is_recoverable=True
    ),
    "ai_unavailable": ErrorInfo(
        code="AI002",
        title="AI Service Unavailable",
        message="The AI service is temporarily unavailable.",
        suggestion="This usually resolves in a few minutes. Please try again.",
        action=ErrorAction.RETRY,
        icon="warning",
        is_recoverable=True
    ),
    "ai_invalid_response": ErrorInfo(
        code="AI003",
        title="AI Response Error",
        message="Received an unexpected response from the AI.",
        suggestion="Try asking the question again.",
        action=ErrorAction.RETRY,
        icon="warning",
        is_recoverable=True
    ),
    "api_key_invalid": ErrorInfo(
        code="AI004",
        title="API Key Invalid",
        message="The AI API key is missing or invalid.",
        suggestion="Check your API key configuration.",
        action=ErrorAction.SETTINGS,
        icon="error",
        is_recoverable=False
    ),

    # Transcription errors
    "transcription_failed": ErrorInfo(
        code="TRX001",
        title="Transcription Failed",
        message="Could not transcribe the audio.",
        suggestion="Make sure you're speaking clearly and try again.",
        action=ErrorAction.RETRY,
        icon="warning",
        is_recoverable=True
    ),
    "model_loading_failed": ErrorInfo(
        code="TRX002",
        title="Model Loading Failed",
        message="Could not load the speech recognition model.",
        suggestion="Restart the application. If the problem persists, reinstall.",
        action=ErrorAction.RESTART,
        icon="error",
        is_recoverable=True
    ),

    # Application errors
    "update_available": ErrorInfo(
        code="APP001",
        title="Update Available",
        message="A new version of ReadIn AI is available.",
        suggestion="Download the latest version for new features and bug fixes.",
        action=ErrorAction.UPDATE,
        icon="info",
        is_recoverable=True
    ),
    "update_required": ErrorInfo(
        code="APP002",
        title="Update Required",
        message="This version of ReadIn AI is no longer supported.",
        suggestion="Please update to the latest version to continue.",
        action=ErrorAction.UPDATE,
        icon="warning",
        is_recoverable=True
    ),
    "unexpected_error": ErrorInfo(
        code="APP999",
        title="Unexpected Error",
        message="Something went wrong.",
        suggestion="Please try again. If the problem persists, contact support.",
        action=ErrorAction.CONTACT_SUPPORT,
        icon="error",
        is_recoverable=True
    ),
}


def get_error(error_code: str) -> ErrorInfo:
    """Get error information by code.

    Args:
        error_code: The error code (e.g., 'connection_failed')

    Returns:
        ErrorInfo object, or generic unexpected_error if not found
    """
    return ERRORS.get(error_code, ERRORS["unexpected_error"])


def get_error_for_exception(exception: Exception) -> ErrorInfo:
    """Map an exception to an appropriate error message.

    Args:
        exception: The exception that occurred

    Returns:
        Appropriate ErrorInfo based on exception type
    """
    exception_name = type(exception).__name__.lower()
    exception_str = str(exception).lower()

    # Connection errors
    if any(term in exception_name for term in ['connect', 'network', 'socket']):
        return ERRORS["connection_failed"]
    if 'timeout' in exception_name or 'timeout' in exception_str:
        return ERRORS["connection_timeout"]

    # HTTP status code errors
    if '401' in exception_str or 'unauthorized' in exception_str:
        return ERRORS["auth_expired"]
    if '403' in exception_str or 'forbidden' in exception_str:
        return ERRORS["auth_required"]
    if '429' in exception_str or 'rate limit' in exception_str:
        return ERRORS["ai_rate_limit"]
    if '503' in exception_str or 'service unavailable' in exception_str:
        return ERRORS["server_unavailable"]

    # Audio errors
    if 'audio' in exception_str or 'microphone' in exception_str:
        if 'permission' in exception_str:
            return ERRORS["audio_permission_denied"]
        if 'busy' in exception_str or 'in use' in exception_str:
            return ERRORS["audio_device_busy"]
        return ERRORS["audio_capture_failed"]

    return ERRORS["unexpected_error"]


def format_error_message(error: ErrorInfo, details: Optional[str] = None) -> str:
    """Format an error for display.

    Args:
        error: ErrorInfo object
        details: Optional additional details

    Returns:
        Formatted error message string
    """
    message = f"{error.title}\n\n{error.message}"
    if details:
        message += f"\n\nDetails: {details}"
    message += f"\n\n{error.suggestion}"
    return message


def get_action_button_text(action: ErrorAction) -> str:
    """Get the appropriate button text for an error action.

    Args:
        action: The ErrorAction enum value

    Returns:
        Button text string
    """
    action_texts = {
        ErrorAction.RETRY: "Try Again",
        ErrorAction.LOGIN: "Log In",
        ErrorAction.UPGRADE: "Upgrade",
        ErrorAction.SETTINGS: "Open Settings",
        ErrorAction.RECONNECT: "Reconnect",
        ErrorAction.RESTART: "Restart App",
        ErrorAction.CONTACT_SUPPORT: "Contact Support",
        ErrorAction.IGNORE: "Dismiss",
        ErrorAction.UPDATE: "Update Now",
    }
    return action_texts.get(action, "OK")
