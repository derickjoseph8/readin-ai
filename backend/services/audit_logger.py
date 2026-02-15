"""
Comprehensive audit logging service for security and compliance.

Provides decorators and utilities for logging security-sensitive actions
including authentication, data access, and admin operations.
"""

import logging
from datetime import datetime
from typing import Optional, Any, Dict, Callable
from functools import wraps

from fastapi import Request
from sqlalchemy.orm import Session

from models import AuditLog, AuditAction, User
from middleware.request_context import get_request_id

# Configure logger
logger = logging.getLogger("audit")
logger.setLevel(logging.INFO)


class AuditLogger:
    """
    Centralized audit logging service.

    Handles all audit logging operations with consistent formatting
    and database persistence.
    """

    @staticmethod
    def log(
        db: Session,
        action: str,
        user_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        old_value: Optional[Dict] = None,
        new_value: Optional[Dict] = None,
        details: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        status: str = "success",
        failure_reason: Optional[str] = None,
    ) -> AuditLog:
        """
        Create an audit log entry.

        Args:
            db: Database session
            action: Action type (use AuditAction constants)
            user_id: ID of user performing action (None for anonymous)
            resource_type: Type of resource being accessed (e.g., "Meeting")
            resource_id: ID of resource being accessed
            old_value: Previous state (for updates)
            new_value: New state (for updates)
            details: Additional context
            ip_address: Client IP address
            user_agent: Client user agent
            status: "success", "failure", or "blocked"
            failure_reason: Reason for failure

        Returns:
            Created AuditLog entry
        """
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_value=old_value,
            new_value=new_value,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=get_request_id(),
            status=status,
            failure_reason=failure_reason,
            timestamp=datetime.utcnow(),
        )

        db.add(audit_log)
        db.commit()

        # Also log to application logger
        log_level = logging.WARNING if status == "failure" else logging.INFO
        logger.log(
            log_level,
            f"Audit: {action}",
            extra={
                "action": action,
                "user_id": user_id,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "status": status,
                "request_id": get_request_id(),
            }
        )

        return audit_log

    # =========================================================================
    # Authentication Events
    # =========================================================================

    @staticmethod
    def log_login_success(
        db: Session,
        user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """Log successful login."""
        return AuditLogger.log(
            db=db,
            action=AuditAction.LOGIN_SUCCESS,
            user_id=user.id,
            resource_type="User",
            resource_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"email": user.email},
        )

    @staticmethod
    def log_login_failure(
        db: Session,
        email: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        reason: str = "Invalid credentials",
    ):
        """Log failed login attempt."""
        return AuditLogger.log(
            db=db,
            action=AuditAction.LOGIN_FAILURE,
            ip_address=ip_address,
            user_agent=user_agent,
            status="failure",
            failure_reason=reason,
            details={"email": email},
        )

    @staticmethod
    def log_logout(
        db: Session,
        user: User,
        ip_address: Optional[str] = None,
    ):
        """Log user logout."""
        return AuditLogger.log(
            db=db,
            action=AuditAction.LOGOUT,
            user_id=user.id,
            resource_type="User",
            resource_id=user.id,
            ip_address=ip_address,
        )

    @staticmethod
    def log_password_change(
        db: Session,
        user: User,
        ip_address: Optional[str] = None,
    ):
        """Log password change."""
        return AuditLogger.log(
            db=db,
            action=AuditAction.PASSWORD_CHANGE,
            user_id=user.id,
            resource_type="User",
            resource_id=user.id,
            ip_address=ip_address,
        )

    # =========================================================================
    # GDPR Events
    # =========================================================================

    @staticmethod
    def log_data_export(
        db: Session,
        user: User,
        ip_address: Optional[str] = None,
        export_format: str = "json",
    ):
        """Log user data export request."""
        return AuditLogger.log(
            db=db,
            action=AuditAction.DATA_EXPORT,
            user_id=user.id,
            resource_type="User",
            resource_id=user.id,
            ip_address=ip_address,
            details={"format": export_format},
        )

    @staticmethod
    def log_data_delete(
        db: Session,
        user: User,
        ip_address: Optional[str] = None,
        scheduled_date: Optional[datetime] = None,
    ):
        """Log account deletion request."""
        return AuditLogger.log(
            db=db,
            action=AuditAction.DATA_DELETE,
            user_id=user.id,
            resource_type="User",
            resource_id=user.id,
            ip_address=ip_address,
            details={"scheduled_date": scheduled_date.isoformat() if scheduled_date else None},
        )

    @staticmethod
    def log_consent_update(
        db: Session,
        user: User,
        old_consent: Dict,
        new_consent: Dict,
        ip_address: Optional[str] = None,
    ):
        """Log GDPR consent update."""
        return AuditLogger.log(
            db=db,
            action=AuditAction.CONSENT_UPDATE,
            user_id=user.id,
            resource_type="User",
            resource_id=user.id,
            old_value=old_consent,
            new_value=new_consent,
            ip_address=ip_address,
        )

    # =========================================================================
    # Account Events
    # =========================================================================

    @staticmethod
    def log_account_create(
        db: Session,
        user: User,
        ip_address: Optional[str] = None,
    ):
        """Log new account creation."""
        return AuditLogger.log(
            db=db,
            action=AuditAction.ACCOUNT_CREATE,
            user_id=user.id,
            resource_type="User",
            resource_id=user.id,
            ip_address=ip_address,
            details={"email": user.email},
        )

    @staticmethod
    def log_account_update(
        db: Session,
        user: User,
        old_values: Dict,
        new_values: Dict,
        ip_address: Optional[str] = None,
    ):
        """Log account profile update."""
        return AuditLogger.log(
            db=db,
            action=AuditAction.ACCOUNT_UPDATE,
            user_id=user.id,
            resource_type="User",
            resource_id=user.id,
            old_value=old_values,
            new_value=new_values,
            ip_address=ip_address,
        )

    # =========================================================================
    # Subscription Events
    # =========================================================================

    @staticmethod
    def log_subscription_create(
        db: Session,
        user: User,
        subscription_id: str,
        plan: str,
    ):
        """Log subscription creation."""
        return AuditLogger.log(
            db=db,
            action=AuditAction.SUBSCRIPTION_CREATE,
            user_id=user.id,
            resource_type="Subscription",
            details={"subscription_id": subscription_id, "plan": plan},
        )

    @staticmethod
    def log_subscription_cancel(
        db: Session,
        user: User,
        subscription_id: str,
    ):
        """Log subscription cancellation."""
        return AuditLogger.log(
            db=db,
            action=AuditAction.SUBSCRIPTION_CANCEL,
            user_id=user.id,
            resource_type="Subscription",
            details={"subscription_id": subscription_id},
        )

    # =========================================================================
    # API Key Events
    # =========================================================================

    @staticmethod
    def log_api_key_create(
        db: Session,
        user: User,
        key_name: str,
        key_prefix: str,
    ):
        """Log API key creation."""
        return AuditLogger.log(
            db=db,
            action=AuditAction.API_KEY_CREATE,
            user_id=user.id,
            resource_type="APIKey",
            details={"name": key_name, "prefix": key_prefix},
        )

    @staticmethod
    def log_api_key_revoke(
        db: Session,
        user: User,
        key_prefix: str,
    ):
        """Log API key revocation."""
        return AuditLogger.log(
            db=db,
            action=AuditAction.API_KEY_REVOKE,
            user_id=user.id,
            resource_type="APIKey",
            details={"prefix": key_prefix},
        )

    # =========================================================================
    # Rate Limit Events
    # =========================================================================

    @staticmethod
    def log_rate_limit_exceeded(
        db: Session,
        user_id: Optional[int],
        endpoint: str,
        ip_address: Optional[str] = None,
    ):
        """Log rate limit exceeded."""
        return AuditLogger.log(
            db=db,
            action=AuditAction.RATE_LIMIT_EXCEEDED,
            user_id=user_id,
            ip_address=ip_address,
            status="blocked",
            details={"endpoint": endpoint},
        )


# =========================================================================
# Decorators for automatic audit logging
# =========================================================================

def audit_action(action: str, resource_type: Optional[str] = None):
    """
    Decorator to automatically audit endpoint access.

    Usage:
        @audit_action(AuditAction.DATA_EXPORT, "User")
        def export_user_data(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            db = kwargs.get("db")
            user = kwargs.get("user")
            request = kwargs.get("request")

            try:
                result = await func(*args, **kwargs)

                if db and user:
                    AuditLogger.log(
                        db=db,
                        action=action,
                        user_id=user.id if user else None,
                        resource_type=resource_type,
                        ip_address=request.client.host if request else None,
                    )

                return result
            except Exception as e:
                if db:
                    AuditLogger.log(
                        db=db,
                        action=action,
                        user_id=user.id if user else None,
                        resource_type=resource_type,
                        ip_address=request.client.host if request else None,
                        status="failure",
                        failure_reason=str(e)[:200],
                    )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            db = kwargs.get("db")
            user = kwargs.get("user")
            request = kwargs.get("request")

            try:
                result = func(*args, **kwargs)

                if db and user:
                    AuditLogger.log(
                        db=db,
                        action=action,
                        user_id=user.id if user else None,
                        resource_type=resource_type,
                        ip_address=request.client.host if request else None,
                    )

                return result
            except Exception as e:
                if db:
                    AuditLogger.log(
                        db=db,
                        action=action,
                        user_id=user.id if user else None,
                        resource_type=resource_type,
                        ip_address=request.client.host if request else None,
                        status="failure",
                        failure_reason=str(e)[:200],
                    )
                raise

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def get_client_ip(request: Request) -> Optional[str]:
    """Extract client IP from request, handling proxies."""
    # Check X-Forwarded-For header (for proxied requests)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Get the first IP in the chain (original client)
        return forwarded.split(",")[0].strip()

    # Check X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fall back to direct connection
    if request.client:
        return request.client.host

    return None


def get_user_agent(request: Request) -> Optional[str]:
    """Extract user agent from request."""
    return request.headers.get("User-Agent")
