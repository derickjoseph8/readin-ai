"""
Login Security Service for anomaly detection.

Provides functionality to detect and alert on suspicious login activity:
- New device detection
- New location detection
- Failed login attempt tracking
- Rate limiting per account
- Security alerts and notifications
"""

import hashlib
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, List

from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from models import User, LoginAttempt, SecurityAlert, TrustedDevice
from services.audit_logger import AuditLogger


class LoginSecurityService:
    """
    Service for detecting and handling login anomalies.
    """

    # Thresholds
    MAX_FAILED_ATTEMPTS_PER_HOUR = 5
    MAX_FAILED_ATTEMPTS_PER_DAY = 15
    ANOMALY_SCORE_THRESHOLD = 50  # Score above which login is flagged as suspicious

    @staticmethod
    def generate_device_fingerprint(
        user_agent: Optional[str],
        ip_address: Optional[str],
    ) -> str:
        """
        Generate a fingerprint for device identification.

        Uses a combination of user agent and IP prefix to identify devices.
        """
        components = []

        if user_agent:
            components.append(user_agent)

        # Use IP prefix (first 3 octets for IPv4) for some location stability
        if ip_address and '.' in ip_address:
            ip_prefix = '.'.join(ip_address.split('.')[:3])
            components.append(ip_prefix)

        fingerprint_str = '|'.join(components)
        return hashlib.sha256(fingerprint_str.encode()).hexdigest()[:32]

    @staticmethod
    def parse_user_agent(user_agent: Optional[str]) -> Dict[str, str]:
        """
        Parse user agent string for device information.
        """
        if not user_agent:
            return {"device_type": "unknown", "browser": None, "os": None}

        ua_lower = user_agent.lower()

        # Device type
        device_type = "desktop"
        if "mobile" in ua_lower or "android" in ua_lower or "iphone" in ua_lower:
            device_type = "mobile"
        elif "tablet" in ua_lower or "ipad" in ua_lower:
            device_type = "tablet"

        # Browser
        browser = None
        if "chrome" in ua_lower and "edg" not in ua_lower:
            browser = "Chrome"
        elif "firefox" in ua_lower:
            browser = "Firefox"
        elif "safari" in ua_lower and "chrome" not in ua_lower:
            browser = "Safari"
        elif "edg" in ua_lower:
            browser = "Edge"
        elif "msie" in ua_lower or "trident" in ua_lower:
            browser = "Internet Explorer"

        # OS
        os = None
        if "windows" in ua_lower:
            os = "Windows"
        elif "mac" in ua_lower:
            os = "macOS"
        elif "linux" in ua_lower and "android" not in ua_lower:
            os = "Linux"
        elif "android" in ua_lower:
            os = "Android"
        elif "iphone" in ua_lower or "ipad" in ua_lower:
            os = "iOS"

        return {"device_type": device_type, "browser": browser, "os": os}

    @staticmethod
    def check_new_device(
        db: Session,
        user: User,
        device_fingerprint: str,
    ) -> bool:
        """
        Check if this is a new device for the user.
        """
        trusted = db.query(TrustedDevice).filter(
            TrustedDevice.user_id == user.id,
            TrustedDevice.device_fingerprint == device_fingerprint,
            TrustedDevice.is_active == True,
        ).first()

        return trusted is None

    @staticmethod
    def check_new_location(
        db: Session,
        user: User,
        ip_address: Optional[str],
    ) -> bool:
        """
        Check if this is a new location (IP range) for the user.
        """
        if not ip_address:
            return False

        # Get IP prefix
        if '.' in ip_address:
            ip_prefix = '.'.join(ip_address.split('.')[:2])  # First 2 octets
        else:
            return False

        # Check recent successful logins
        recent_ips = db.query(LoginAttempt.ip_address).filter(
            LoginAttempt.user_id == user.id,
            LoginAttempt.success == True,
            LoginAttempt.timestamp >= datetime.utcnow() - timedelta(days=30),
        ).distinct().all()

        for (recent_ip,) in recent_ips:
            if recent_ip and recent_ip.startswith(ip_prefix):
                return False

        return True

    @staticmethod
    def get_failed_attempts_count(
        db: Session,
        email: str,
        hours: int = 1,
    ) -> int:
        """
        Get count of failed login attempts for an email in the last N hours.
        """
        since = datetime.utcnow() - timedelta(hours=hours)

        return db.query(LoginAttempt).filter(
            LoginAttempt.email == email,
            LoginAttempt.success == False,
            LoginAttempt.timestamp >= since,
        ).count()

    @staticmethod
    def calculate_anomaly_score(
        is_new_device: bool,
        is_new_location: bool,
        failed_attempts_hour: int,
        failed_attempts_day: int,
    ) -> float:
        """
        Calculate an anomaly score for the login attempt.

        Higher score = more suspicious.
        """
        score = 0.0

        # New device adds to suspicion
        if is_new_device:
            score += 20

        # New location adds more
        if is_new_location:
            score += 25

        # Failed attempts increase score
        if failed_attempts_hour > 0:
            score += min(failed_attempts_hour * 5, 25)

        if failed_attempts_day > 5:
            score += min((failed_attempts_day - 5) * 2, 20)

        # Both new device AND new location is very suspicious
        if is_new_device and is_new_location:
            score += 10

        return min(score, 100)

    @staticmethod
    def record_login_attempt(
        db: Session,
        email: str,
        success: bool,
        user: Optional[User] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        failure_reason: Optional[str] = None,
    ) -> Tuple[LoginAttempt, bool]:
        """
        Record a login attempt and check for anomalies.

        Returns:
            Tuple of (LoginAttempt, is_suspicious)
        """
        # Parse user agent
        device_info = LoginSecurityService.parse_user_agent(user_agent)

        # Check for anomalies if successful login
        is_new_device = False
        is_new_location = False
        anomaly_score = 0.0

        if success and user:
            device_fingerprint = LoginSecurityService.generate_device_fingerprint(
                user_agent, ip_address
            )
            is_new_device = LoginSecurityService.check_new_device(
                db, user, device_fingerprint
            )
            is_new_location = LoginSecurityService.check_new_location(
                db, user, ip_address
            )

        # Get failed attempts count
        failed_hour = LoginSecurityService.get_failed_attempts_count(db, email, hours=1)
        failed_day = LoginSecurityService.get_failed_attempts_count(db, email, hours=24)

        # Calculate anomaly score
        anomaly_score = LoginSecurityService.calculate_anomaly_score(
            is_new_device, is_new_location, failed_hour, failed_day
        )

        is_suspicious = anomaly_score >= LoginSecurityService.ANOMALY_SCORE_THRESHOLD

        # Create login attempt record
        attempt = LoginAttempt(
            user_id=user.id if user else None,
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
            device_type=device_info["device_type"],
            browser=device_info["browser"],
            os=device_info["os"],
            success=success,
            failure_reason=failure_reason,
            is_new_device=is_new_device,
            is_new_location=is_new_location,
            is_suspicious=is_suspicious,
            anomaly_score=anomaly_score,
        )

        db.add(attempt)
        db.commit()
        db.refresh(attempt)

        # Create security alerts if needed
        if success and user:
            if is_new_device:
                LoginSecurityService.create_security_alert(
                    db=db,
                    user=user,
                    alert_type="new_device",
                    severity="medium",
                    title="Login from new device",
                    description=f"A new {device_info['device_type']} ({device_info['browser']} on {device_info['os']}) was used to sign in.",
                    ip_address=ip_address,
                    device_info=device_info,
                )

            if is_new_location:
                LoginSecurityService.create_security_alert(
                    db=db,
                    user=user,
                    alert_type="new_location",
                    severity="medium",
                    title="Login from new location",
                    description=f"Your account was accessed from a new IP address: {ip_address}",
                    ip_address=ip_address,
                )

        # Check for too many failed attempts
        if not success and failed_hour >= LoginSecurityService.MAX_FAILED_ATTEMPTS_PER_HOUR:
            if user:
                LoginSecurityService.create_security_alert(
                    db=db,
                    user=user,
                    alert_type="failed_attempts",
                    severity="high",
                    title="Multiple failed login attempts",
                    description=f"There have been {failed_hour} failed login attempts to your account in the last hour.",
                    ip_address=ip_address,
                )

        return attempt, is_suspicious

    @staticmethod
    def create_security_alert(
        db: Session,
        user: User,
        alert_type: str,
        severity: str,
        title: str,
        description: Optional[str] = None,
        ip_address: Optional[str] = None,
        device_info: Optional[Dict] = None,
        location_info: Optional[Dict] = None,
    ) -> SecurityAlert:
        """
        Create a security alert for the user.
        """
        alert = SecurityAlert(
            user_id=user.id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            description=description,
            ip_address=ip_address,
            device_info=device_info,
            location_info=location_info,
        )

        db.add(alert)
        db.commit()
        db.refresh(alert)

        return alert

    @staticmethod
    def trust_device(
        db: Session,
        user: User,
        user_agent: Optional[str],
        ip_address: Optional[str],
        device_name: Optional[str] = None,
    ) -> TrustedDevice:
        """
        Mark a device as trusted for the user.
        """
        device_fingerprint = LoginSecurityService.generate_device_fingerprint(
            user_agent, ip_address
        )
        device_info = LoginSecurityService.parse_user_agent(user_agent)

        # Check if already trusted
        existing = db.query(TrustedDevice).filter(
            TrustedDevice.user_id == user.id,
            TrustedDevice.device_fingerprint == device_fingerprint,
        ).first()

        if existing:
            existing.last_used = datetime.utcnow()
            existing.is_active = True
            db.commit()
            return existing

        # Create new trusted device
        trusted = TrustedDevice(
            user_id=user.id,
            device_fingerprint=device_fingerprint,
            device_name=device_name or f"{device_info['browser']} on {device_info['os']}",
            device_type=device_info["device_type"],
            browser=device_info["browser"],
            os=device_info["os"],
        )

        db.add(trusted)
        db.commit()
        db.refresh(trusted)

        return trusted

    @staticmethod
    def get_user_security_alerts(
        db: Session,
        user: User,
        unread_only: bool = False,
        limit: int = 20,
    ) -> List[SecurityAlert]:
        """
        Get security alerts for a user.
        """
        query = db.query(SecurityAlert).filter(SecurityAlert.user_id == user.id)

        if unread_only:
            query = query.filter(SecurityAlert.is_read == False)

        return query.order_by(desc(SecurityAlert.created_at)).limit(limit).all()

    @staticmethod
    def mark_alert_read(
        db: Session,
        alert_id: int,
        user: User,
    ) -> bool:
        """
        Mark a security alert as read.
        """
        alert = db.query(SecurityAlert).filter(
            SecurityAlert.id == alert_id,
            SecurityAlert.user_id == user.id,
        ).first()

        if alert:
            alert.is_read = True
            db.commit()
            return True

        return False

    @staticmethod
    def is_rate_limited(
        db: Session,
        email: str,
    ) -> Tuple[bool, Optional[int]]:
        """
        Check if login attempts should be rate limited.

        Returns:
            Tuple of (is_limited, seconds_until_unlock)
        """
        failed_hour = LoginSecurityService.get_failed_attempts_count(db, email, hours=1)

        if failed_hour >= LoginSecurityService.MAX_FAILED_ATTEMPTS_PER_HOUR:
            # Find the oldest failed attempt in the last hour
            oldest = db.query(LoginAttempt).filter(
                LoginAttempt.email == email,
                LoginAttempt.success == False,
                LoginAttempt.timestamp >= datetime.utcnow() - timedelta(hours=1),
            ).order_by(LoginAttempt.timestamp.asc()).first()

            if oldest:
                unlock_time = oldest.timestamp + timedelta(hours=1)
                seconds_remaining = int((unlock_time - datetime.utcnow()).total_seconds())
                if seconds_remaining > 0:
                    return True, seconds_remaining

        return False, None
