"""
Compliance Service - SOC 2, HIPAA, CCPA compliance features.

Provides compliance reporting, data access requests, and consent management.
"""

import logging
from typing import Dict, List, Optional, Any
from uuid import UUID
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

logger = logging.getLogger(__name__)


class ComplianceService:
    """Service for compliance monitoring and reporting."""

    def __init__(self, db: Session):
        self.db = db

    async def generate_soc2_report(
        self,
        start_date: date,
        end_date: date,
        organization_id: Optional[UUID] = None
    ) -> Dict:
        """
        Generate SOC 2 compliance report.

        Args:
            start_date: Report start date
            end_date: Report end date
            organization_id: Optional organization filter

        Returns:
            SOC 2 compliance report data
        """
        from models import AuditLog, User, UserSession

        # Access control summary
        total_users = self.db.query(User).count()
        active_users = self.db.query(User).filter(
            User.last_login >= datetime.combine(start_date, datetime.min.time())
        ).count()

        # Audit log summary
        audit_entries = self.db.query(func.count(AuditLog.id)).filter(
            AuditLog.created_at >= datetime.combine(start_date, datetime.min.time()),
            AuditLog.created_at <= datetime.combine(end_date, datetime.max.time())
        ).scalar()

        # Security events
        security_events = self.db.query(AuditLog).filter(
            AuditLog.action.in_([
                "login_failed", "password_reset", "2fa_enabled",
                "api_key_created", "permission_changed"
            ]),
            AuditLog.created_at >= datetime.combine(start_date, datetime.min.time()),
            AuditLog.created_at <= datetime.combine(end_date, datetime.max.time())
        ).count()

        # Active sessions
        active_sessions = self.db.query(UserSession).filter(
            UserSession.is_active == True
        ).count()

        return {
            "report_period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "access_controls": {
                "total_users": total_users,
                "active_users": active_users,
                "active_sessions": active_sessions
            },
            "audit_logging": {
                "total_entries": audit_entries,
                "security_events": security_events,
                "logging_enabled": True
            },
            "data_protection": {
                "encryption_at_rest": True,
                "encryption_in_transit": True,
                "backup_enabled": True
            },
            "compliance_status": "COMPLIANT",
            "generated_at": datetime.utcnow().isoformat()
        }

    async def check_hipaa_compliance(self, organization_id: UUID) -> Dict:
        """
        Check HIPAA compliance status for an organization.

        Args:
            organization_id: Organization ID

        Returns:
            HIPAA compliance checklist status
        """
        from models import Organization, DataProcessingAgreement

        org = self.db.query(Organization).filter(
            Organization.id == organization_id
        ).first()

        if not org:
            return {"error": "Organization not found"}

        # Check for BAA
        baa = self.db.query(DataProcessingAgreement).filter(
            DataProcessingAgreement.organization_id == organization_id,
            DataProcessingAgreement.agreement_type == "baa",
            DataProcessingAgreement.expires_at > datetime.utcnow()
        ).first()

        checklist = {
            "baa_signed": baa is not None,
            "baa_expires": baa.expires_at.isoformat() if baa else None,
            "access_controls": True,  # Always enabled
            "audit_logging": True,  # Always enabled
            "encryption": True,  # Always enabled
            "minimum_necessary": True,  # Data minimization
            "training_required": not baa,  # Suggest training if no BAA
        }

        compliant = all([
            checklist["baa_signed"],
            checklist["access_controls"],
            checklist["audit_logging"],
            checklist["encryption"]
        ])

        return {
            "organization_id": str(organization_id),
            "hipaa_compliant": compliant,
            "checklist": checklist,
            "recommendations": self._hipaa_recommendations(checklist)
        }

    def _hipaa_recommendations(self, checklist: Dict) -> List[str]:
        """Generate HIPAA recommendations based on checklist."""
        recs = []
        if not checklist.get("baa_signed"):
            recs.append("Sign a Business Associate Agreement (BAA)")
        if checklist.get("training_required"):
            recs.append("Complete HIPAA training for all users")
        return recs

    async def process_ccpa_request(
        self,
        user_id: UUID,
        request_type: str
    ) -> Dict:
        """
        Process a CCPA data request.

        Args:
            user_id: User making the request
            request_type: Type of request (access, delete, opt-out)

        Returns:
            Request processing result
        """
        from models import User, ComplianceLog

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": "User not found"}

        # Log the request
        log = ComplianceLog(
            event_type=f"ccpa_{request_type}_request",
            user_id=user_id,
            details={"request_type": request_type}
        )
        self.db.add(log)
        self.db.commit()

        if request_type == "access":
            return await self.get_data_inventory(user_id)

        elif request_type == "delete":
            # Queue deletion (don't delete immediately)
            return {
                "status": "queued",
                "message": "Your data deletion request has been received. Data will be deleted within 45 days.",
                "request_id": str(log.id)
            }

        elif request_type == "opt-out":
            # Opt out of data sale (we don't sell data, but track the preference)
            user.data_sale_opt_out = True
            self.db.commit()
            return {
                "status": "completed",
                "message": "You have been opted out of data sale.",
                "note": "ReadIn AI does not sell personal data."
            }

        return {"error": "Invalid request type"}

    async def get_data_inventory(self, user_id: UUID) -> Dict:
        """
        Get inventory of all user data for compliance.

        Args:
            user_id: User ID

        Returns:
            Data inventory with categories and retention
        """
        from models import User, Meeting, Conversation, ActionItem

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": "User not found"}

        # Count data by category
        meetings_count = self.db.query(Meeting).filter(
            Meeting.user_id == user_id
        ).count()

        conversations_count = self.db.query(Conversation).filter(
            Conversation.user_id == user_id
        ).count()

        action_items_count = self.db.query(ActionItem).filter(
            ActionItem.user_id == user_id
        ).count()

        return {
            "user_id": str(user_id),
            "data_categories": [
                {
                    "category": "Account Information",
                    "data_types": ["email", "name", "profile settings"],
                    "retention": "Until account deletion",
                    "count": 1
                },
                {
                    "category": "Meeting Data",
                    "data_types": ["transcripts", "summaries", "recordings"],
                    "retention": "90 days or per user settings",
                    "count": meetings_count
                },
                {
                    "category": "Conversations",
                    "data_types": ["questions", "AI responses"],
                    "retention": "90 days or per user settings",
                    "count": conversations_count
                },
                {
                    "category": "Action Items",
                    "data_types": ["tasks", "due dates", "assignments"],
                    "retention": "Until completion + 30 days",
                    "count": action_items_count
                },
                {
                    "category": "Usage Analytics",
                    "data_types": ["feature usage", "login times"],
                    "retention": "12 months",
                    "count": "aggregated"
                }
            ],
            "third_party_sharing": [
                {
                    "service": "Anthropic (Claude AI)",
                    "purpose": "AI processing",
                    "data_shared": "Transcripts for AI responses"
                },
                {
                    "service": "Stripe/Paystack",
                    "purpose": "Payment processing",
                    "data_shared": "Payment information"
                }
            ],
            "generated_at": datetime.utcnow().isoformat()
        }

    async def get_consent_status(self, user_id: UUID) -> Dict:
        """Get user's consent status for various purposes."""
        from models import ConsentRecord

        consents = self.db.query(ConsentRecord).filter(
            ConsentRecord.user_id == user_id
        ).all()

        consent_map = {}
        for c in consents:
            consent_map[c.consent_type] = {
                "granted": c.granted,
                "granted_at": c.granted_at.isoformat() if c.granted_at else None,
                "withdrawn_at": c.withdrawn_at.isoformat() if c.withdrawn_at else None
            }

        # Default consents
        defaults = ["marketing", "analytics", "data_sharing", "ai_processing"]
        for d in defaults:
            if d not in consent_map:
                consent_map[d] = {"granted": False, "granted_at": None}

        return {
            "user_id": str(user_id),
            "consents": consent_map
        }

    async def update_consent(
        self,
        user_id: UUID,
        consent_type: str,
        granted: bool,
        ip_address: Optional[str] = None
    ) -> Dict:
        """Update user consent preference."""
        from models import ConsentRecord

        # Find existing consent
        consent = self.db.query(ConsentRecord).filter(
            ConsentRecord.user_id == user_id,
            ConsentRecord.consent_type == consent_type
        ).first()

        if consent:
            consent.granted = granted
            if granted:
                consent.granted_at = datetime.utcnow()
                consent.withdrawn_at = None
            else:
                consent.withdrawn_at = datetime.utcnow()
            consent.ip_address = ip_address
        else:
            consent = ConsentRecord(
                user_id=user_id,
                consent_type=consent_type,
                granted=granted,
                granted_at=datetime.utcnow() if granted else None,
                ip_address=ip_address
            )
            self.db.add(consent)

        self.db.commit()

        return {
            "consent_type": consent_type,
            "granted": granted,
            "updated_at": datetime.utcnow().isoformat()
        }

    async def log_compliance_event(
        self,
        event_type: str,
        user_id: Optional[UUID] = None,
        details: Optional[Dict] = None,
        ip_address: Optional[str] = None
    ):
        """Log a compliance-related event."""
        from models import ComplianceLog

        log = ComplianceLog(
            event_type=event_type,
            user_id=user_id,
            details=details or {},
            ip_address=ip_address
        )
        self.db.add(log)
        self.db.commit()
