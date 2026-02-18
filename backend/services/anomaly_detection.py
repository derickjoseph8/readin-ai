"""
Anomaly Detection Service for ReadIn AI.

Detects suspicious activity patterns including:
- Unusual login patterns (time, location, frequency)
- Brute force attempts
- API abuse patterns
- Data exfiltration attempts
- Account takeover indicators
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import func

from models import User, LoginAttempt, SecurityAlert, AuditLog
from config import IS_PRODUCTION


logger = logging.getLogger(__name__)


class ThreatLevel(str, Enum):
    """Threat severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AnomalyType(str, Enum):
    """Types of detected anomalies."""
    BRUTE_FORCE = "brute_force"
    IMPOSSIBLE_TRAVEL = "impossible_travel"
    UNUSUAL_TIME = "unusual_time"
    UNUSUAL_LOCATION = "unusual_location"
    RAPID_REQUESTS = "rapid_requests"
    DATA_EXFILTRATION = "data_exfiltration"
    ACCOUNT_ENUMERATION = "account_enumeration"
    CREDENTIAL_STUFFING = "credential_stuffing"
    SESSION_HIJACKING = "session_hijacking"
    PRIVILEGE_ESCALATION = "privilege_escalation"


@dataclass
class AnomalyAlert:
    """Represents a detected anomaly."""
    anomaly_type: AnomalyType
    threat_level: ThreatLevel
    user_id: Optional[int]
    ip_address: str
    description: str
    details: Dict[str, Any]
    timestamp: datetime
    recommended_action: str


class AnomalyDetector:
    """
    Detects suspicious activity patterns.

    Uses statistical analysis and rule-based detection to identify
    potential security threats.
    """

    # Configuration thresholds
    FAILED_LOGIN_THRESHOLD = 5  # Failed logins before alert
    FAILED_LOGIN_WINDOW = 300  # 5 minutes
    RAPID_REQUEST_THRESHOLD = 100  # Requests per minute
    UNUSUAL_HOUR_START = 2  # 2 AM
    UNUSUAL_HOUR_END = 5  # 5 AM
    DATA_EXPORT_THRESHOLD = 10  # Exports per hour

    def __init__(self, db: Session):
        self.db = db
        self._ip_request_counts: Dict[str, List[datetime]] = defaultdict(list)
        self._ip_failed_logins: Dict[str, List[datetime]] = defaultdict(list)

    async def analyze_login_attempt(
        self,
        user_id: Optional[int],
        email: str,
        ip_address: str,
        user_agent: str,
        success: bool,
        location: Optional[str] = None,
    ) -> List[AnomalyAlert]:
        """Analyze a login attempt for suspicious patterns."""
        alerts = []
        now = datetime.utcnow()

        # Track failed login
        if not success:
            self._ip_failed_logins[ip_address].append(now)
            # Clean old entries
            cutoff = now - timedelta(seconds=self.FAILED_LOGIN_WINDOW)
            self._ip_failed_logins[ip_address] = [
                t for t in self._ip_failed_logins[ip_address] if t > cutoff
            ]

            # Check for brute force
            if len(self._ip_failed_logins[ip_address]) >= self.FAILED_LOGIN_THRESHOLD:
                alerts.append(AnomalyAlert(
                    anomaly_type=AnomalyType.BRUTE_FORCE,
                    threat_level=ThreatLevel.HIGH,
                    user_id=user_id,
                    ip_address=ip_address,
                    description=f"Multiple failed login attempts detected from {ip_address}",
                    details={
                        "failed_attempts": len(self._ip_failed_logins[ip_address]),
                        "window_seconds": self.FAILED_LOGIN_WINDOW,
                        "email_targeted": email,
                    },
                    timestamp=now,
                    recommended_action="Block IP temporarily and notify user"
                ))

        # Check for successful login anomalies
        if success and user_id:
            # Check unusual time
            if self.UNUSUAL_HOUR_START <= now.hour <= self.UNUSUAL_HOUR_END:
                # Check if user normally logs in at this time
                if not self._is_normal_login_time(user_id, now.hour):
                    alerts.append(AnomalyAlert(
                        anomaly_type=AnomalyType.UNUSUAL_TIME,
                        threat_level=ThreatLevel.LOW,
                        user_id=user_id,
                        ip_address=ip_address,
                        description=f"Login at unusual hour ({now.hour}:00)",
                        details={"hour": now.hour, "location": location},
                        timestamp=now,
                        recommended_action="Send notification to user"
                    ))

            # Check for impossible travel
            travel_alert = await self._check_impossible_travel(
                user_id, ip_address, location, now
            )
            if travel_alert:
                alerts.append(travel_alert)

        # Log alerts
        for alert in alerts:
            await self._save_alert(alert)

        return alerts

    async def analyze_api_request(
        self,
        user_id: Optional[int],
        ip_address: str,
        endpoint: str,
        method: str,
    ) -> List[AnomalyAlert]:
        """Analyze API request patterns for abuse."""
        alerts = []
        now = datetime.utcnow()

        # Track request rate
        self._ip_request_counts[ip_address].append(now)

        # Clean old entries (keep last minute)
        cutoff = now - timedelta(minutes=1)
        self._ip_request_counts[ip_address] = [
            t for t in self._ip_request_counts[ip_address] if t > cutoff
        ]

        # Check for rapid requests
        request_count = len(self._ip_request_counts[ip_address])
        if request_count >= self.RAPID_REQUEST_THRESHOLD:
            alerts.append(AnomalyAlert(
                anomaly_type=AnomalyType.RAPID_REQUESTS,
                threat_level=ThreatLevel.MEDIUM,
                user_id=user_id,
                ip_address=ip_address,
                description=f"Unusually high request rate: {request_count}/min",
                details={
                    "requests_per_minute": request_count,
                    "threshold": self.RAPID_REQUEST_THRESHOLD,
                    "endpoint": endpoint,
                },
                timestamp=now,
                recommended_action="Rate limit IP address"
            ))

        # Check for data exfiltration (bulk exports)
        if "export" in endpoint.lower() or "bulk" in endpoint.lower():
            export_alert = await self._check_data_exfiltration(
                user_id, ip_address, endpoint, now
            )
            if export_alert:
                alerts.append(export_alert)

        return alerts

    async def analyze_password_reset(
        self,
        email: str,
        ip_address: str,
    ) -> List[AnomalyAlert]:
        """Analyze password reset requests for account enumeration."""
        alerts = []
        now = datetime.utcnow()

        # Check for account enumeration (many reset requests to different emails)
        recent_resets = self.db.query(AuditLog).filter(
            AuditLog.action == "password_reset_request",
            AuditLog.ip_address == ip_address,
            AuditLog.created_at > now - timedelta(hours=1)
        ).count()

        if recent_resets >= 10:
            alerts.append(AnomalyAlert(
                anomaly_type=AnomalyType.ACCOUNT_ENUMERATION,
                threat_level=ThreatLevel.MEDIUM,
                user_id=None,
                ip_address=ip_address,
                description="Multiple password reset requests from single IP",
                details={
                    "reset_requests": recent_resets,
                    "window": "1 hour",
                    "last_email": email,
                },
                timestamp=now,
                recommended_action="Add CAPTCHA or rate limit"
            ))

        return alerts

    def _is_normal_login_time(self, user_id: int, hour: int) -> bool:
        """Check if user normally logs in at this hour."""
        # Get login history for past 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        login_hours = self.db.query(
            func.extract('hour', LoginAttempt.created_at)
        ).filter(
            LoginAttempt.user_id == user_id,
            LoginAttempt.success == True,
            LoginAttempt.created_at > thirty_days_ago
        ).all()

        if not login_hours:
            return True  # No history, don't alert

        # Check if user has logged in at this hour before
        hour_counts = defaultdict(int)
        for (h,) in login_hours:
            hour_counts[int(h)] += 1

        return hour_counts.get(hour, 0) > 0

    async def _check_impossible_travel(
        self,
        user_id: int,
        ip_address: str,
        location: Optional[str],
        timestamp: datetime
    ) -> Optional[AnomalyAlert]:
        """Check for impossible travel (login from distant locations in short time)."""
        if not location:
            return None

        # Get last login
        last_login = self.db.query(LoginAttempt).filter(
            LoginAttempt.user_id == user_id,
            LoginAttempt.success == True,
            LoginAttempt.created_at < timestamp
        ).order_by(LoginAttempt.created_at.desc()).first()

        if not last_login or not last_login.location:
            return None

        # Check time difference
        time_diff = (timestamp - last_login.created_at).total_seconds() / 3600  # hours

        # If different locations within 2 hours, flag as suspicious
        if (
            last_login.location != location and
            time_diff < 2 and
            last_login.ip_address != ip_address
        ):
            return AnomalyAlert(
                anomaly_type=AnomalyType.IMPOSSIBLE_TRAVEL,
                threat_level=ThreatLevel.HIGH,
                user_id=user_id,
                ip_address=ip_address,
                description="Login from different location in impossibly short time",
                details={
                    "previous_location": last_login.location,
                    "current_location": location,
                    "time_between_logins_hours": round(time_diff, 2),
                    "previous_ip": last_login.ip_address,
                    "current_ip": ip_address,
                },
                timestamp=timestamp,
                recommended_action="Require additional verification"
            )

        return None

    async def _check_data_exfiltration(
        self,
        user_id: Optional[int],
        ip_address: str,
        endpoint: str,
        timestamp: datetime
    ) -> Optional[AnomalyAlert]:
        """Check for potential data exfiltration patterns."""
        # Count exports in last hour
        hour_ago = timestamp - timedelta(hours=1)

        export_count = self.db.query(AuditLog).filter(
            AuditLog.user_id == user_id if user_id else AuditLog.ip_address == ip_address,
            AuditLog.action.like("%export%"),
            AuditLog.created_at > hour_ago
        ).count()

        if export_count >= self.DATA_EXPORT_THRESHOLD:
            return AnomalyAlert(
                anomaly_type=AnomalyType.DATA_EXFILTRATION,
                threat_level=ThreatLevel.HIGH,
                user_id=user_id,
                ip_address=ip_address,
                description="Unusually high number of data exports",
                details={
                    "exports_last_hour": export_count,
                    "threshold": self.DATA_EXPORT_THRESHOLD,
                    "last_endpoint": endpoint,
                },
                timestamp=timestamp,
                recommended_action="Review user activity and consider temporary suspension"
            )

        return None

    async def _save_alert(self, alert: AnomalyAlert) -> None:
        """Save anomaly alert to database."""
        try:
            security_alert = SecurityAlert(
                user_id=alert.user_id,
                alert_type=alert.anomaly_type.value,
                severity=alert.threat_level.value,
                title=alert.description[:200],
                description=str(alert.details),
                ip_address=alert.ip_address,
                is_resolved=False,
            )
            self.db.add(security_alert)
            self.db.commit()

            logger.warning(
                f"Security alert: {alert.anomaly_type.value} - {alert.description}",
                extra={
                    "threat_level": alert.threat_level.value,
                    "ip_address": alert.ip_address,
                    "user_id": alert.user_id,
                }
            )
        except Exception as e:
            logger.error(f"Failed to save security alert: {e}")

    def get_threat_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get summary of threats in the last N hours."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        alerts = self.db.query(SecurityAlert).filter(
            SecurityAlert.created_at > cutoff
        ).all()

        by_type = defaultdict(int)
        by_severity = defaultdict(int)

        for alert in alerts:
            by_type[alert.alert_type] += 1
            by_severity[alert.severity] += 1

        return {
            "total_alerts": len(alerts),
            "by_type": dict(by_type),
            "by_severity": dict(by_severity),
            "unresolved": sum(1 for a in alerts if not a.is_resolved),
            "period_hours": hours,
        }


async def get_anomaly_detector(db: Session) -> AnomalyDetector:
    """Factory function to get anomaly detector instance."""
    return AnomalyDetector(db)
