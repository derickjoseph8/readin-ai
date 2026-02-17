"""SQLAlchemy database models for ReadIn AI."""

from datetime import datetime, timedelta
from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, Date, ForeignKey, Text,
    Float, LargeBinary, JSON, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship

from database import Base
from config import TRIAL_DAYS


# =============================================================================
# PROFESSION & CAREER MODELS
# =============================================================================

class Profession(Base):
    """Global profession/career database for tailored AI responses."""
    __tablename__ = "professions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    category = Column(String, index=True)  # Legal, Medical, Tech, Finance, etc.
    description = Column(Text)

    # AI Customization
    terminology = Column(JSON)  # Industry-specific terms
    common_topics = Column(JSON)  # Typical discussion topics
    system_prompt_additions = Column(Text)  # AI prompt enhancements
    communication_style = Column(String)  # formal, technical, casual, etc.

    # Metadata
    icon = Column(String)  # Icon identifier for UI
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    users = relationship("User", back_populates="profession")


# =============================================================================
# ORGANIZATION & CORPORATE MODELS
# =============================================================================

class Organization(Base):
    """Corporate/team accounts - admin pays, team joins free."""
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)

    # Plan details
    plan_type = Column(String, default="team")  # team, business, enterprise
    max_users = Column(Integer, default=10)

    # Admin & billing
    admin_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    billing_email = Column(String)

    # Stripe
    stripe_customer_id = Column(String, unique=True, nullable=True)
    subscription_id = Column(String, nullable=True)
    subscription_status = Column(String, default="trial")  # trial, active, cancelled
    subscription_end_date = Column(DateTime, nullable=True)

    # Settings
    allow_personal_professions = Column(Boolean, default=True)
    shared_insights_enabled = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    members = relationship("User", back_populates="organization", foreign_keys="User.organization_id")
    invites = relationship("OrganizationInvite", back_populates="organization")


class OrganizationInvite(Base):
    """Invitations for team members to join an organization."""
    __tablename__ = "organization_invites"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    email = Column(String, nullable=False, index=True)
    invited_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    role = Column(String, default="member")  # admin, member
    status = Column(String, default="pending")  # pending, accepted, expired, cancelled

    token = Column(String, unique=True)  # Unique invite token
    expires_at = Column(DateTime)
    accepted_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="invites")
    invited_by = relationship("User", foreign_keys=[invited_by_id])


# =============================================================================
# USER MODEL (UPDATED)
# =============================================================================

class User(Base):
    """User account model with profession and organization support."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)

    # Profession
    profession_id = Column(Integer, ForeignKey("professions.id"), nullable=True)
    specialization = Column(String, nullable=True)  # e.g., "Corporate Law", "Cardiology"
    years_experience = Column(Integer, nullable=True)

    # Organization (Corporate)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    role_in_org = Column(String, default="member")  # admin, member
    company = Column(String, nullable=True)  # For individual users not in an organization

    # Staff/Team Member status (for internal teams - lifetime access while active)
    is_staff = Column(Boolean, default=False)
    staff_role = Column(String(50), nullable=True)  # super_admin, admin, manager, agent

    # Stripe (for individual users)
    stripe_customer_id = Column(String, unique=True, nullable=True)

    # Subscription status
    subscription_status = Column(String, default="trial")  # trial, active, cancelled, expired
    subscription_id = Column(String, nullable=True)
    subscription_end_date = Column(DateTime, nullable=True)

    # Trial
    trial_start_date = Column(DateTime, default=datetime.utcnow)
    trial_end_date = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=TRIAL_DAYS))

    # Email preferences
    email_notifications_enabled = Column(Boolean, default=True)
    email_summary_enabled = Column(Boolean, default=True)
    email_reminders_enabled = Column(Boolean, default=True)

    # Two-Factor Authentication (TOTP)
    totp_secret = Column(String(32), nullable=True)
    totp_enabled = Column(Boolean, default=False)
    totp_backup_codes = Column(JSON, default=list)  # Encrypted backup codes

    # GDPR Consent fields
    consent_analytics = Column(Boolean, default=False)
    consent_marketing = Column(Boolean, default=False)
    consent_ai_training = Column(Boolean, default=False)
    consent_updated_at = Column(DateTime, nullable=True)

    # SSO / Social Login
    sso_provider = Column(String(50), nullable=True)  # google, microsoft, apple
    sso_provider_id = Column(String(255), nullable=True)  # Provider's user ID
    google_refresh_token = Column(String(512), nullable=True)  # For calendar access
    microsoft_refresh_token = Column(String(512), nullable=True)  # For calendar access

    # Account deletion scheduling
    deletion_requested = Column(Boolean, default=False)
    deletion_scheduled = Column(DateTime, nullable=True)

    # Additional user tracking
    last_login = Column(DateTime, nullable=True)
    timezone = Column(String, default="UTC")
    preferred_language = Column(String, default="en")  # en, es, sw (Swahili)
    trial_start = Column(DateTime, default=datetime.utcnow)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    profession = relationship("Profession", back_populates="users")
    organization = relationship("Organization", back_populates="members", foreign_keys=[organization_id])
    usage = relationship("DailyUsage", back_populates="user")
    meetings = relationship("Meeting", back_populates="user")
    topics = relationship("Topic", back_populates="user")
    action_items = relationship("ActionItem", back_populates="user")
    calendar_integrations = relationship("CalendarIntegration", back_populates="user")
    commitments = relationship("Commitment", back_populates="user")
    job_applications = relationship("JobApplication", back_populates="user")
    learning_profile = relationship("UserLearningProfile", back_populates="user", uselist=False)
    participant_memories = relationship("ParticipantMemory", back_populates="user")
    media_appearances = relationship("MediaAppearance", back_populates="user")
    email_notifications = relationship("EmailNotification", back_populates="user")
    payment_history = relationship("PaymentHistory", back_populates="user")

    @property
    def is_trial(self) -> bool:
        return self.subscription_status == "trial"

    @property
    def is_active(self) -> bool:
        # Check organization subscription first
        if self.organization_id and self.organization:
            if self.organization.subscription_status == "active":
                return True
        # Check individual subscription
        if self.subscription_status == "active":
            return True
        if self.subscription_status == "trial":
            return datetime.utcnow() < self.trial_end_date
        return False

    @property
    def trial_days_remaining(self) -> int:
        if not self.is_trial:
            return 0
        remaining = (self.trial_end_date - datetime.utcnow()).days
        return max(0, remaining)

    @property
    def is_org_admin(self) -> bool:
        return self.organization_id is not None and self.role_in_org == "admin"


class DailyUsage(Base):
    """Track daily AI response usage for trial users."""
    __tablename__ = "daily_usage"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    response_count = Column(Integer, default=0)

    user = relationship("User", back_populates="usage")


class CalendarIntegration(Base):
    """Calendar provider integrations for users."""
    __tablename__ = "calendar_integrations"
    __table_args__ = (
        Index("ix_calendar_user_provider", "user_id", "provider"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider = Column(String(50), nullable=False)  # 'google' or 'microsoft'
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    calendar_email = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    connected_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="calendar_integrations")


# =============================================================================
# MEETING & CONVERSATION MODELS
# =============================================================================

class Meeting(Base):
    """Meeting session tracking."""
    __tablename__ = "meetings"
    __table_args__ = (
        Index("ix_meeting_user_id", "user_id"),
        Index("ix_meeting_user_status", "user_id", "status"),
        Index("ix_meeting_started_at", "started_at"),
        Index("ix_meeting_user_date", "user_id", "started_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Meeting info
    meeting_type = Column(String, default="general")  # interview, tv_appearance, manager_meeting, general
    title = Column(String)
    meeting_app = Column(String)  # Teams, Zoom, etc.

    # Timing
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    # Status
    status = Column(String, default="active", index=True)  # active, ended, cancelled

    # Metadata
    participant_count = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="meetings")
    conversations = relationship("Conversation", back_populates="meeting", cascade="all, delete-orphan")
    action_items = relationship("ActionItem", back_populates="meeting")
    commitments = relationship("Commitment", back_populates="meeting")
    summary = relationship("MeetingSummary", back_populates="meeting", uselist=False)


class Conversation(Base):
    """Individual Q&A exchanges within a meeting."""
    __tablename__ = "conversations"
    __table_args__ = (
        Index("ix_conversation_meeting_id", "meeting_id"),
        Index("ix_conversation_timestamp", "timestamp"),
    )

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False)

    # Content
    speaker = Column(String, default="other")  # user, other, unknown
    heard_text = Column(Text, nullable=False)
    response_text = Column(Text, nullable=True)

    # Timing
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Analysis
    sentiment = Column(String, nullable=True)  # positive, neutral, negative
    confidence_score = Column(Float, nullable=True)

    # Relationships
    meeting = relationship("Meeting", back_populates="conversations")
    topics = relationship("ConversationTopic", back_populates="conversation")


# =============================================================================
# TOPIC TRACKING & ML MODELS
# =============================================================================

class Topic(Base):
    """Topics extracted from conversations for ML tracking."""
    __tablename__ = "topics"
    __table_args__ = (
        Index("ix_topic_user_id", "user_id"),
        Index("ix_topic_user_frequency", "user_id", "frequency"),
        Index("ix_topic_user_name", "user_id", "name"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    name = Column(String, nullable=False, index=True)
    category = Column(String, index=True)  # technical, behavioral, situational, company-specific

    # Frequency tracking
    frequency = Column(Integer, default=1, index=True)
    last_discussed = Column(DateTime, default=datetime.utcnow)

    # ML data
    embedding = Column(LargeBinary, nullable=True)  # Vector embedding for similarity

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="topics")
    conversations = relationship("ConversationTopic", back_populates="topic")


class ConversationTopic(Base):
    """Many-to-many relationship between conversations and topics."""
    __tablename__ = "conversation_topics"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    relevance_score = Column(Float, default=1.0)  # 0-1 how relevant

    conversation = relationship("Conversation", back_populates="topics")
    topic = relationship("Topic", back_populates="conversations")


class UserLearningProfile(Base):
    """ML-learned profile of user's communication patterns."""
    __tablename__ = "user_learning_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # Communication Style (0-1 scales)
    formality_level = Column(Float, default=0.5)  # casual to formal
    verbosity = Column(Float, default=0.5)  # concise to detailed
    technical_depth = Column(Float, default=0.5)  # simple to technical

    # Topic Preferences
    frequent_topics = Column(JSON, default=dict)  # {"topic": frequency}
    topic_expertise = Column(JSON, default=dict)  # {"topic": confidence_score}
    avoided_topics = Column(JSON, default=list)

    # Response Patterns
    preferred_response_length = Column(Integer, default=50)  # avg words
    filler_words_used = Column(JSON, default=list)
    strengths = Column(JSON, default=list)
    areas_for_improvement = Column(JSON, default=list)

    # Readiness Data
    go_to_phrases = Column(JSON, default=list)  # User's favorite expressions
    success_patterns = Column(JSON, default=dict)  # What works for them

    # Metadata
    total_conversations_analyzed = Column(Integer, default=0)
    confidence_score = Column(Float, default=0.0)  # How confident ML is
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="learning_profile")


# =============================================================================
# ACTION ITEMS & COMMITMENTS
# =============================================================================

class ActionItem(Base):
    """Action items extracted from meetings - WHO does WHAT by WHEN."""
    __tablename__ = "action_items"
    __table_args__ = (
        Index("ix_action_item_user_id", "user_id"),
        Index("ix_action_item_user_status", "user_id", "status"),
        Index("ix_action_item_due_date", "due_date"),
        Index("ix_action_item_meeting_id", "meeting_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Assignment
    assignee = Column(String, nullable=False)  # Name of person responsible
    assignee_role = Column(String)  # user, other, team

    # Task details
    description = Column(Text, nullable=False)
    due_date = Column(DateTime, nullable=True)
    priority = Column(String, default="medium", index=True)  # low, medium, high

    # Status
    status = Column(String, default="pending", index=True)  # pending, in_progress, completed, cancelled
    completed_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    meeting = relationship("Meeting", back_populates="action_items")
    user = relationship("User", back_populates="action_items")


class Commitment(Base):
    """Commitments the user made - things they promised to do."""
    __tablename__ = "commitments"
    __table_args__ = (
        Index("ix_commitment_user_id", "user_id"),
        Index("ix_commitment_user_status", "user_id", "status"),
        Index("ix_commitment_due_date", "due_date"),
        Index("ix_commitment_next_reminder", "next_reminder_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Commitment details
    description = Column(Text, nullable=False)
    due_date = Column(DateTime, nullable=True)
    context = Column(Text, nullable=True)  # Why/to whom the commitment was made

    # Status
    status = Column(String, default="pending", index=True)  # pending, completed, overdue
    completed_at = Column(DateTime, nullable=True)

    # Reminders
    reminder_sent = Column(Boolean, default=False)
    next_reminder_at = Column(DateTime, nullable=True)
    reminder_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    meeting = relationship("Meeting", back_populates="commitments")
    user = relationship("User", back_populates="commitments")


# =============================================================================
# MEETING SUMMARIES
# =============================================================================

class MeetingSummary(Base):
    """Auto-generated meeting summaries."""
    __tablename__ = "meeting_summaries"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Summary content
    summary_text = Column(Text)
    key_points = Column(JSON)  # List of key discussion points
    decisions_made = Column(JSON)  # List of decisions

    # Analysis
    sentiment = Column(String)  # positive, neutral, negative
    topics_discussed = Column(JSON)  # List of topic names

    # Email status
    email_sent = Column(Boolean, default=False)
    email_sent_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    meeting = relationship("Meeting", back_populates="summary")


# =============================================================================
# JOB INTERVIEW TRACKING
# =============================================================================

class JobApplication(Base):
    """Track job applications for interview improvement."""
    __tablename__ = "job_applications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Job details
    company = Column(String, nullable=False)
    position = Column(String, nullable=False)
    job_description = Column(Text, nullable=True)
    job_url = Column(String, nullable=True)

    # Status
    status = Column(String, default="active")  # active, offer, rejected, withdrawn, accepted

    # Salary info
    salary_range = Column(String, nullable=True)

    # Notes
    notes = Column(Text, nullable=True)

    # Timestamps
    applied_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="job_applications")
    interviews = relationship("Interview", back_populates="job_application", cascade="all, delete-orphan")


class Interview(Base):
    """Individual interviews within a job application."""
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True)
    job_application_id = Column(Integer, ForeignKey("job_applications.id"), nullable=False)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=True)

    # Interview details
    interview_type = Column(String)  # phone, technical, behavioral, final, hr
    round_number = Column(Integer, default=1)

    # Interviewer info
    interviewer_name = Column(String, nullable=True)
    interviewer_role = Column(String, nullable=True)

    # Scheduling
    scheduled_at = Column(DateTime, nullable=True)
    duration_minutes = Column(Integer, nullable=True)

    # Performance tracking
    performance_score = Column(Float, nullable=True)  # 0-1 ML-assessed
    user_feeling = Column(String, nullable=True)  # good, neutral, bad

    # Improvement
    improvement_notes = Column(JSON, default=list)  # Suggestions for next time
    questions_asked = Column(JSON, default=list)  # Questions that were asked
    strong_answers = Column(JSON, default=list)  # What went well
    weak_answers = Column(JSON, default=list)  # What to improve

    # Status
    status = Column(String, default="scheduled")  # scheduled, completed, cancelled
    outcome = Column(String, nullable=True)  # passed, failed, pending

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    job_application = relationship("JobApplication", back_populates="interviews")


# =============================================================================
# PARTICIPANT MEMORY
# =============================================================================

class ParticipantMemory(Base):
    """Remember what other participants have said across meetings."""
    __tablename__ = "participant_memories"
    __table_args__ = (
        Index("ix_participant_memory_user_id", "user_id"),
        Index("ix_participant_memory_user_name", "user_id", "participant_name"),
        Index("ix_participant_memory_last_interaction", "last_interaction"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Participant info
    participant_name = Column(String, nullable=False, index=True)
    participant_email = Column(String, nullable=True, index=True)
    participant_role = Column(String, nullable=True)
    company = Column(String, nullable=True, index=True)

    # Memory data
    key_points = Column(JSON, default=list)  # Things they've said/mentioned
    preferences = Column(JSON, default=dict)  # Known preferences/tendencies
    topics_discussed = Column(JSON, default=list)  # Topics they care about
    communication_style = Column(String, nullable=True)  # How they communicate

    # Relationship context
    relationship_notes = Column(Text, nullable=True)

    # Interaction tracking
    meeting_count = Column(Integer, default=1)
    last_interaction = Column(DateTime, default=datetime.utcnow)
    first_interaction = Column(DateTime, default=datetime.utcnow)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="participant_memories")


# =============================================================================
# MEDIA APPEARANCE TRACKING
# =============================================================================

class MediaAppearance(Base):
    """Track TV/podcast/media appearances for variety."""
    __tablename__ = "media_appearances"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=True)

    # Appearance details
    show_name = Column(String, nullable=False)
    network = Column(String, nullable=True)
    host_name = Column(String, nullable=True)
    topic = Column(String, nullable=True)

    # Content tracking
    points_made = Column(JSON, default=list)  # List of talking points used
    order_of_points = Column(JSON, default=list)  # Sequence for variety tracking
    questions_asked = Column(JSON, default=list)  # Questions from host

    # Performance
    self_rating = Column(Integer, nullable=True)  # 1-5 self assessment
    notes = Column(Text, nullable=True)

    # Timing
    aired_at = Column(DateTime, nullable=True)
    duration_minutes = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="media_appearances")


# =============================================================================
# EMAIL NOTIFICATIONS
# =============================================================================

class EmailNotification(Base):
    """Log of all email notifications sent."""
    __tablename__ = "email_notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Email details
    email_type = Column(String, nullable=False)  # meeting_summary, commitment_reminder, briefing, weekly_digest
    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    recipient_email = Column(String, nullable=False)

    # Status
    status = Column(String, default="pending")  # pending, sent, failed
    sent_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    # Related entities
    related_meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=True)
    related_commitment_id = Column(Integer, ForeignKey("commitments.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="email_notifications")


# =============================================================================
# PAYMENT HISTORY
# =============================================================================


class PaymentHistory(Base):
    """Log of all payment transactions."""
    __tablename__ = "payment_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Stripe details
    stripe_invoice_id = Column(String, nullable=True, index=True)
    stripe_payment_intent_id = Column(String, nullable=True)

    # Payment info
    amount = Column(Integer, nullable=False)  # Amount in cents
    currency = Column(String(3), default="usd")
    status = Column(String, nullable=False)  # paid, failed, refunded, pending
    description = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="payment_history")


# =============================================================================
# AUDIT LOG (GDPR COMPLIANCE)
# =============================================================================


class AuditLog(Base):
    """
    Audit log for tracking security-sensitive actions.

    Used for:
    - GDPR compliance (data access, export, deletion)
    - Security monitoring (login attempts, password changes)
    - Admin actions (subscription changes, user management)
    """
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_log_user_id", "user_id"),
        Index("ix_audit_log_action", "action"),
        Index("ix_audit_log_timestamp", "timestamp"),
        Index("ix_audit_log_user_action", "user_id", "action"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Nullable for anonymous actions

    # Action details
    action = Column(String, nullable=False)  # login, logout, password_change, data_export, data_delete, etc.
    resource_type = Column(String, nullable=True)  # User, Meeting, Conversation, etc.
    resource_id = Column(Integer, nullable=True)

    # Request context
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    request_id = Column(String, nullable=True)

    # Change details
    old_value = Column(JSON, nullable=True)  # Previous state (for updates)
    new_value = Column(JSON, nullable=True)  # New state (for updates)
    details = Column(JSON, nullable=True)  # Additional context

    # Status
    status = Column(String, default="success")  # success, failure, blocked
    failure_reason = Column(String, nullable=True)

    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


# Audit action constants
class AuditAction:
    """Constants for audit log actions."""
    # Authentication
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET_REQUEST = "password_reset_request"

    # GDPR
    DATA_EXPORT = "data_export"
    DATA_DELETE = "data_delete"
    CONSENT_UPDATE = "consent_update"

    # Account
    ACCOUNT_CREATE = "account_create"
    ACCOUNT_UPDATE = "account_update"
    ACCOUNT_DELETE = "account_delete"

    # Subscription
    SUBSCRIPTION_CREATE = "subscription_create"
    SUBSCRIPTION_UPDATE = "subscription_update"
    SUBSCRIPTION_CANCEL = "subscription_cancel"

    # Admin actions
    USER_IMPERSONATION = "user_impersonation"
    ROLE_CHANGE = "role_change"
    ORG_MEMBER_ADD = "org_member_add"
    ORG_MEMBER_REMOVE = "org_member_remove"

    # API
    API_KEY_CREATE = "api_key_create"
    API_KEY_REVOKE = "api_key_revoke"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"


# =============================================================================
# PRE-MEETING BRIEFINGS
# =============================================================================

class PreMeetingBriefing(Base):
    """Auto-generated briefings before meetings."""
    __tablename__ = "pre_meeting_briefings"
    __table_args__ = (
        Index("ix_briefing_user_id", "user_id"),
        Index("ix_briefing_scheduled_time", "scheduled_time"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Meeting info
    title = Column(String)
    scheduled_time = Column(DateTime, nullable=True)
    meeting_type = Column(String, default="general")

    # Briefing content
    content = Column(Text)
    participants = Column(JSON, default=list)  # List of participant info
    key_topics = Column(JSON, default=list)  # Topics to prepare for
    suggested_questions = Column(JSON, default=list)  # Questions to ask
    context_notes = Column(Text)  # Background info

    # Participant memories included
    participant_memories_used = Column(JSON, default=list)  # IDs of memories used

    # Status
    status = Column(String, default="generated")  # generated, sent, viewed
    sent_at = Column(DateTime, nullable=True)
    viewed_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)


# =============================================================================
# LEARNING PROFILE (ALIAS)
# =============================================================================

# Alias for backward compatibility
LearningProfile = UserLearningProfile


# =============================================================================
# ROLE-BASED ACCESS CONTROL (RBAC)
# =============================================================================

class Role(Base):
    """
    RBAC Role definition.

    Roles define a set of permissions that can be assigned to users.
    """
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)

    # Permission flags stored as JSON
    permissions = Column(JSON, default=list)

    # System roles cannot be deleted
    is_system = Column(Boolean, default=False)

    # Organization scope (null = global)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = relationship("Organization")
    user_roles = relationship("UserRole", back_populates="role")


class UserRole(Base):
    """Many-to-many relationship between users and roles."""
    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_role"),
        Index("ix_user_role_user_id", "user_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)

    # Optional organization scope
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)

    # Who assigned this role
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    role = relationship("Role", back_populates="user_roles")


# Permission constants
class Permission:
    """Constants for RBAC permissions."""
    # Meetings
    VIEW_MEETINGS = "meetings:view"
    EDIT_MEETINGS = "meetings:edit"
    DELETE_MEETINGS = "meetings:delete"

    # Analytics
    VIEW_ANALYTICS = "analytics:view"
    EXPORT_ANALYTICS = "analytics:export"

    # Team management
    VIEW_TEAM = "team:view"
    MANAGE_TEAM = "team:manage"
    INVITE_MEMBERS = "team:invite"
    REMOVE_MEMBERS = "team:remove"

    # Organization
    VIEW_ORG_SETTINGS = "org:view_settings"
    MANAGE_ORG_SETTINGS = "org:manage_settings"

    # Billing
    VIEW_BILLING = "billing:view"
    MANAGE_BILLING = "billing:manage"

    # SSO
    MANAGE_SSO = "sso:manage"

    # API Keys
    VIEW_API_KEYS = "api_keys:view"
    MANAGE_API_KEYS = "api_keys:manage"

    # Admin
    SUPER_ADMIN = "admin:super"


# =============================================================================
# SINGLE SIGN-ON (SSO)
# =============================================================================

class SSOProvider(Base):
    """
    SSO Provider configuration for organizations.

    Supports SAML 2.0, OAuth 2.0 / OIDC.
    """
    __tablename__ = "sso_providers"
    __table_args__ = (
        UniqueConstraint("organization_id", "provider_type", name="uq_org_provider"),
        Index("ix_sso_provider_org", "organization_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)

    # Provider type
    provider_type = Column(String(50), nullable=False)  # saml, oidc, azure_ad, okta, google
    name = Column(String(100), nullable=False)  # Display name

    # Common settings
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)

    # SAML Settings
    saml_entity_id = Column(String(500), nullable=True)
    saml_sso_url = Column(String(500), nullable=True)
    saml_slo_url = Column(String(500), nullable=True)  # Single Logout URL
    saml_certificate = Column(Text, nullable=True)
    saml_metadata_url = Column(String(500), nullable=True)

    # OIDC/OAuth Settings
    oidc_client_id = Column(String(255), nullable=True)
    oidc_client_secret = Column(Text, nullable=True)
    oidc_discovery_url = Column(String(500), nullable=True)
    oidc_authorization_url = Column(String(500), nullable=True)
    oidc_token_url = Column(String(500), nullable=True)
    oidc_userinfo_url = Column(String(500), nullable=True)
    oidc_scopes = Column(JSON, default=["openid", "email", "profile"])

    # Attribute mapping
    attribute_mapping = Column(JSON, default={
        "email": "email",
        "name": "name",
        "given_name": "given_name",
        "family_name": "family_name"
    })

    # Auto-provisioning
    auto_provision_users = Column(Boolean, default=True)
    default_role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)

    # Domain restrictions
    allowed_domains = Column(JSON, default=list)  # Empty = all domains allowed

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = relationship("Organization")
    sessions = relationship("SSOSession", back_populates="provider")


class SSOSession(Base):
    """
    SSO Session tracking for single logout and session management.
    """
    __tablename__ = "sso_sessions"
    __table_args__ = (
        Index("ix_sso_session_user", "user_id"),
        Index("ix_sso_session_provider", "provider_id"),
        Index("ix_sso_session_external", "external_session_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider_id = Column(Integer, ForeignKey("sso_providers.id"), nullable=False)

    # Session identifiers
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    external_session_id = Column(String(255), nullable=True)  # IdP session ID

    # Session data
    identity_data = Column(JSON, nullable=True)  # Claims/attributes from IdP

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    last_activity = Column(DateTime, default=datetime.utcnow)
    terminated_at = Column(DateTime, nullable=True)

    # Relationships
    provider = relationship("SSOProvider", back_populates="sessions")


# =============================================================================
# API KEYS
# =============================================================================

class APIKey(Base):
    """
    API Keys for programmatic access.
    """
    __tablename__ = "api_keys"
    __table_args__ = (
        Index("ix_api_key_user", "user_id"),
        Index("ix_api_key_org", "organization_id"),
        Index("ix_api_key_hash", "key_hash"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)

    # Key identification
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    key_prefix = Column(String(10), nullable=False)  # First 8 chars for identification
    key_hash = Column(String(255), unique=True, nullable=False)  # SHA256 hash

    # Permissions (scopes)
    scopes = Column(JSON, default=["read"])  # read, write, admin

    # Rate limiting
    rate_limit_per_minute = Column(Integer, default=60)
    rate_limit_per_day = Column(Integer, default=10000)

    # Usage tracking
    last_used_at = Column(DateTime, nullable=True)
    usage_count = Column(Integer, default=0)

    # Status
    is_active = Column(Boolean, default=True)

    # Expiration
    expires_at = Column(DateTime, nullable=True)  # Null = never expires

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    revoked_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User")
    organization = relationship("Organization")


# =============================================================================
# WEBHOOKS
# =============================================================================

class Webhook(Base):
    """
    Webhook subscriptions for external integrations.
    """
    __tablename__ = "webhooks"
    __table_args__ = (
        Index("ix_webhook_user", "user_id"),
        Index("ix_webhook_org", "organization_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)

    # Webhook configuration
    name = Column(String(100), nullable=False)
    url = Column(String(500), nullable=False)
    secret = Column(String(255), nullable=True)  # For signature verification

    # Events to subscribe to
    events = Column(JSON, default=["meeting.ended"])  # meeting.ended, meeting.started, etc.

    # Headers to include
    custom_headers = Column(JSON, default={})

    # Status
    is_active = Column(Boolean, default=True)

    # Retry configuration
    max_retries = Column(Integer, default=3)
    retry_delay_seconds = Column(Integer, default=60)

    # Stats
    total_deliveries = Column(Integer, default=0)
    successful_deliveries = Column(Integer, default=0)
    failed_deliveries = Column(Integer, default=0)
    last_triggered_at = Column(DateTime, nullable=True)
    last_success_at = Column(DateTime, nullable=True)
    last_failure_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")
    organization = relationship("Organization")
    deliveries = relationship("WebhookDelivery", back_populates="webhook")


class WebhookDelivery(Base):
    """
    Log of webhook delivery attempts.
    """
    __tablename__ = "webhook_deliveries"
    __table_args__ = (
        Index("ix_webhook_delivery_webhook", "webhook_id"),
        Index("ix_webhook_delivery_timestamp", "triggered_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    webhook_id = Column(Integer, ForeignKey("webhooks.id"), nullable=False)

    # Event details
    event_type = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False)

    # Delivery status
    status = Column(String(20), default="pending")  # pending, success, failed

    # Response
    response_status_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    response_time_ms = Column(Integer, nullable=True)

    # Retry tracking
    attempt_count = Column(Integer, default=1)
    next_retry_at = Column(DateTime, nullable=True)

    # Error
    error_message = Column(Text, nullable=True)

    # Timestamps
    triggered_at = Column(DateTime, default=datetime.utcnow)
    delivered_at = Column(DateTime, nullable=True)

    # Relationships
    webhook = relationship("Webhook", back_populates="deliveries")


# =============================================================================
# WHITE-LABEL CONFIGURATION
# =============================================================================

class WhiteLabelConfig(Base):
    """
    White-label branding configuration for organizations.
    """
    __tablename__ = "white_label_configs"
    __table_args__ = (
        UniqueConstraint("organization_id", name="uq_white_label_org"),
    )

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)

    # Branding
    company_name = Column(String(100), nullable=True)
    logo_url = Column(String(500), nullable=True)
    favicon_url = Column(String(500), nullable=True)

    # Colors
    primary_color = Column(String(7), default="#d4af37")  # Hex color
    secondary_color = Column(String(7), default="#10b981")
    background_color = Column(String(7), default="#0a0a0a")
    text_color = Column(String(7), default="#ffffff")

    # Custom domain
    custom_domain = Column(String(255), nullable=True, unique=True)
    domain_verified = Column(Boolean, default=False)
    ssl_certificate = Column(Text, nullable=True)

    # Email branding
    email_from_name = Column(String(100), nullable=True)
    email_reply_to = Column(String(255), nullable=True)
    email_footer_text = Column(Text, nullable=True)

    # Features visibility
    hide_powered_by = Column(Boolean, default=False)
    custom_terms_url = Column(String(500), nullable=True)
    custom_privacy_url = Column(String(500), nullable=True)
    custom_support_email = Column(String(255), nullable=True)

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = relationship("Organization")


# =============================================================================
# USER SESSIONS
# =============================================================================

class UserSession(Base):
    """
    Active user sessions for session management.

    Tracks all active sessions across devices for security monitoring
    and session revocation.
    """
    __tablename__ = "user_sessions"
    __table_args__ = (
        Index("ix_user_session_user_id", "user_id"),
        Index("ix_user_session_token", "session_token"),
        Index("ix_user_session_expires", "expires_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Session identification
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    refresh_token = Column(String(255), unique=True, nullable=True)

    # Device info
    device_name = Column(String(255), nullable=True)
    device_type = Column(String(50), nullable=True)  # desktop, mobile, tablet, browser
    browser = Column(String(100), nullable=True)
    os = Column(String(100), nullable=True)

    # Location
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    location = Column(String(255), nullable=True)  # City, Country

    # Status
    is_active = Column(Boolean, default=True)
    is_current = Column(Boolean, default=False)  # Mark the current session

    # Activity tracking
    last_activity = Column(DateTime, default=datetime.utcnow)
    last_ip = Column(String(45), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User")


# =============================================================================
# LOGIN ANOMALY DETECTION
# =============================================================================

class LoginAttempt(Base):
    """
    Track login attempts for anomaly detection.

    Records both successful and failed login attempts to detect
    suspicious activity patterns.
    """
    __tablename__ = "login_attempts"
    __table_args__ = (
        Index("ix_login_attempt_user_id", "user_id"),
        Index("ix_login_attempt_email", "email"),
        Index("ix_login_attempt_ip", "ip_address"),
        Index("ix_login_attempt_timestamp", "timestamp"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # User info (user_id may be null for failed attempts with unknown email)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    email = Column(String(255), nullable=False, index=True)

    # Attempt details
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(String(512), nullable=True)
    device_type = Column(String(50), nullable=True)  # desktop, mobile, tablet
    browser = Column(String(100), nullable=True)
    os = Column(String(100), nullable=True)

    # Location (if available via IP geolocation)
    country = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)

    # Result
    success = Column(Boolean, default=False)
    failure_reason = Column(String(255), nullable=True)

    # Anomaly flags
    is_new_device = Column(Boolean, default=False)
    is_new_location = Column(Boolean, default=False)
    is_suspicious = Column(Boolean, default=False)
    anomaly_score = Column(Float, default=0.0)  # 0-100 score

    # Timestamps
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User")


class SecurityAlert(Base):
    """
    Security alerts for users.

    Generated when suspicious activity is detected.
    """
    __tablename__ = "security_alerts"
    __table_args__ = (
        Index("ix_security_alert_user_id", "user_id"),
        Index("ix_security_alert_type", "alert_type"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Alert details
    alert_type = Column(String(50), nullable=False)  # new_device, new_location, failed_attempts, etc.
    severity = Column(String(20), default="medium")  # low, medium, high, critical
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Related data
    ip_address = Column(String(45), nullable=True)
    device_info = Column(JSON, nullable=True)
    location_info = Column(JSON, nullable=True)

    # Status
    is_read = Column(Boolean, default=False)
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User")


class TrustedDevice(Base):
    """
    User's trusted devices for login.

    When a user logs in from a new device and marks it as trusted,
    future logins from that device won't trigger alerts.
    """
    __tablename__ = "trusted_devices"
    __table_args__ = (
        Index("ix_trusted_device_user_id", "user_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Device fingerprint
    device_fingerprint = Column(String(255), nullable=False)  # Hash of device characteristics
    device_name = Column(String(255), nullable=True)  # User-friendly name
    device_type = Column(String(50), nullable=True)
    browser = Column(String(100), nullable=True)
    os = Column(String(100), nullable=True)

    # Trust metadata
    last_used = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User")


# =============================================================================
# IN-APP NOTIFICATIONS
# =============================================================================

class InAppNotification(Base):
    """
    In-app notifications for users.

    Displayed in the notification center/bell icon.
    """
    __tablename__ = "in_app_notifications"
    __table_args__ = (
        Index("ix_in_app_notification_user", "user_id"),
        Index("ix_in_app_notification_read", "user_id", "is_read"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Notification content
    type = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    data = Column(JSON, nullable=True)

    # Priority
    priority = Column(String(20), default="normal")  # low, normal, high, urgent

    # Status
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User")


# =============================================================================
# TEMPLATES
# =============================================================================

class Template(Base):
    """
    User-customizable templates for briefings, summaries, and AI responses.
    """
    __tablename__ = "templates"
    __table_args__ = (
        Index("ix_template_user", "user_id"),
        Index("ix_template_type", "template_type"),
        UniqueConstraint("user_id", "name", name="uq_user_template_name"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Null for system templates
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)

    # Template identification
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    template_type = Column(String(50), nullable=False)  # briefing, summary, response, email

    # Template content
    content = Column(Text, nullable=False)  # Template with placeholders
    variables = Column(JSON, default=list)  # List of available variables
    default_values = Column(JSON, default=dict)  # Default values for variables

    # Settings
    is_default = Column(Boolean, default=False)
    is_system = Column(Boolean, default=False)  # System templates can't be deleted
    is_active = Column(Boolean, default=True)

    # Versioning
    version = Column(Integer, default=1)
    parent_id = Column(Integer, ForeignKey("templates.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")
    organization = relationship("Organization")


class TemplateType:
    """Template type constants."""
    BRIEFING = "briefing"
    SUMMARY = "summary"
    RESPONSE = "response"
    EMAIL = "email"
    ACTION_ITEM = "action_item"


# =============================================================================
# AI MODEL PREFERENCES
# =============================================================================

class UserAIPreferences(Base):
    """
    User preferences for AI model selection and behavior.
    """
    __tablename__ = "user_ai_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # Model selection
    preferred_model = Column(String(50), default="sonnet")  # sonnet, opus, haiku
    fallback_model = Column(String(50), default="haiku")

    # Response preferences
    response_length = Column(String(20), default="medium")  # short, medium, long
    response_style = Column(String(50), default="professional")  # professional, casual, technical
    bullet_points = Column(Boolean, default=True)
    include_sources = Column(Boolean, default=False)

    # Cost management
    monthly_budget_cents = Column(Integer, nullable=True)  # Max monthly spend
    current_month_usage_cents = Column(Integer, default=0)
    budget_alert_threshold = Column(Float, default=0.8)  # Alert at 80%

    # Advanced settings
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=1000)
    custom_instructions = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")


# =============================================================================
# ANALYTICS TRACKING
# =============================================================================

class AnalyticsEvent(Base):
    """
    Analytics events for tracking user behavior and system metrics.
    """
    __tablename__ = "analytics_events"
    __table_args__ = (
        Index("ix_analytics_user", "user_id"),
        Index("ix_analytics_event", "event_type"),
        Index("ix_analytics_timestamp", "timestamp"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Event details
    event_type = Column(String(100), nullable=False)
    event_category = Column(String(50), nullable=True)  # meeting, ai, user, system
    event_action = Column(String(100), nullable=True)

    # Event data
    properties = Column(JSON, default=dict)
    value = Column(Float, nullable=True)  # Numeric value (e.g., duration, count)

    # Context
    session_id = Column(String(100), nullable=True)
    source = Column(String(50), nullable=True)  # desktop, web, mobile, api

    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


# =============================================================================
# SUPPORT TEAMS & TICKETING SYSTEM
# =============================================================================

class SupportTeam(Base):
    """
    Internal support teams (Tech Support, Sales, Accounts, etc.)
    Team members get lifetime app access while active.
    """
    __tablename__ = "support_teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    color = Column(String(7), default="#3B82F6")  # Hex color for UI

    # Settings
    is_active = Column(Boolean, default=True)
    accepts_tickets = Column(Boolean, default=True)
    accepts_chat = Column(Boolean, default=True)

    # Working hours (JSON: {"monday": {"start": "09:00", "end": "17:00"}, ...})
    working_hours = Column(JSON, default=dict)
    timezone = Column(String(50), default="UTC")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")
    tickets = relationship("SupportTicket", back_populates="team")
    chat_sessions = relationship("ChatSession", back_populates="team")


class TeamMember(Base):
    """
    Internal staff members assigned to support teams.
    Members have lifetime app access while active - no subscription needed.
    """
    __tablename__ = "team_members"
    __table_args__ = (
        UniqueConstraint("user_id", "team_id", name="uq_user_team"),
        Index("ix_team_member_user", "user_id"),
        Index("ix_team_member_team", "team_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("support_teams.id"), nullable=False)

    # Role within team
    role = Column(String(50), default="agent")  # super_admin, admin, manager, agent

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    joined_at = Column(DateTime, default=datetime.utcnow)
    removed_at = Column(DateTime, nullable=True)
    invited_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    team = relationship("SupportTeam", back_populates="members")
    invited_by = relationship("User", foreign_keys=[invited_by_id])
    assigned_tickets = relationship("SupportTicket", back_populates="assigned_to_member", foreign_keys="SupportTicket.assigned_to_id")
    ticket_messages = relationship("TicketMessage", back_populates="sender_member")
    agent_status = relationship("AgentStatus", back_populates="team_member", uselist=False)
    chat_sessions = relationship("ChatSession", back_populates="agent")


class TeamInvite(Base):
    """Invitations for team members to join a support team."""
    __tablename__ = "team_invites"
    __table_args__ = (
        Index("ix_team_invite_email", "email"),
        Index("ix_team_invite_token", "token"),
    )

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("support_teams.id"), nullable=False)
    email = Column(String(255), nullable=False)
    role = Column(String(50), default="agent")  # admin, manager, agent

    # Invitation details
    token = Column(String(100), unique=True, nullable=False)
    invited_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Status
    status = Column(String(20), default="pending")  # pending, accepted, expired, cancelled
    expires_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    team = relationship("SupportTeam")
    invited_by = relationship("User")


class SLAConfig(Base):
    """SLA configuration for ticket priorities."""
    __tablename__ = "sla_configs"

    id = Column(Integer, primary_key=True, index=True)
    priority = Column(String(20), unique=True, nullable=False)  # urgent, high, medium, low

    # Response times in minutes
    first_response_minutes = Column(Integer, nullable=False)
    resolution_minutes = Column(Integer, nullable=False)

    # Escalation
    escalation_enabled = Column(Boolean, default=True)
    escalation_after_minutes = Column(Integer, nullable=True)

    # Active
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SupportTicket(Base):
    """Customer support tickets."""
    __tablename__ = "support_tickets"
    __table_args__ = (
        Index("ix_ticket_user", "user_id"),
        Index("ix_ticket_team", "team_id"),
        Index("ix_ticket_status", "status"),
        Index("ix_ticket_priority", "priority"),
        Index("ix_ticket_number", "ticket_number"),
    )

    id = Column(Integer, primary_key=True, index=True)
    ticket_number = Column(String(20), unique=True, nullable=False)  # TKT-2026-00001

    # Customer
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Assignment
    team_id = Column(Integer, ForeignKey("support_teams.id"), nullable=True)
    assigned_to_id = Column(Integer, ForeignKey("team_members.id"), nullable=True)

    # Ticket details
    category = Column(String(50), nullable=False)  # billing, technical, sales, general, account
    priority = Column(String(20), default="medium")  # urgent, high, medium, low
    status = Column(String(30), default="open")  # open, in_progress, waiting_customer, waiting_internal, resolved, closed

    # Content
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)

    # SLA tracking
    sla_first_response_due = Column(DateTime, nullable=True)
    sla_resolution_due = Column(DateTime, nullable=True)
    first_response_at = Column(DateTime, nullable=True)
    sla_breached = Column(Boolean, default=False)

    # Source
    source = Column(String(30), default="dashboard")  # dashboard, chat, email, api

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User")
    team = relationship("SupportTeam", back_populates="tickets")
    assigned_to_member = relationship("TeamMember", back_populates="assigned_tickets", foreign_keys=[assigned_to_id])
    messages = relationship("TicketMessage", back_populates="ticket", cascade="all, delete-orphan", order_by="TicketMessage.created_at")
    chat_session = relationship("ChatSession", back_populates="ticket", uselist=False)


class TicketMessage(Base):
    """Messages/replies within a ticket."""
    __tablename__ = "ticket_messages"
    __table_args__ = (
        Index("ix_ticket_message_ticket", "ticket_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("support_tickets.id"), nullable=False)

    # Sender
    sender_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    sender_member_id = Column(Integer, ForeignKey("team_members.id"), nullable=True)
    sender_type = Column(String(20), nullable=False)  # customer, agent, system

    # Content
    message = Column(Text, nullable=False)
    attachments = Column(JSON, default=list)  # List of attachment URLs

    # Visibility
    is_internal = Column(Boolean, default=False)  # Internal notes not visible to customer

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    ticket = relationship("SupportTicket", back_populates="messages")
    sender_user = relationship("User")
    sender_member = relationship("TeamMember", back_populates="ticket_messages")


class ChatSession(Base):
    """Live chat sessions between customers and agents."""
    __tablename__ = "chat_sessions"
    __table_args__ = (
        Index("ix_chat_session_user", "user_id"),
        Index("ix_chat_session_agent", "agent_id"),
        Index("ix_chat_session_status", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    session_token = Column(String(100), unique=True, nullable=False)

    # Participants
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    agent_id = Column(Integer, ForeignKey("team_members.id"), nullable=True)
    team_id = Column(Integer, ForeignKey("support_teams.id"), nullable=True)

    # Status
    status = Column(String(20), default="waiting")  # waiting, active, ended, abandoned

    # Linked ticket (if converted)
    ticket_id = Column(Integer, ForeignKey("support_tickets.id"), nullable=True)

    # Queue position (for waiting chats)
    queue_position = Column(Integer, nullable=True)

    # AI handling (Novah)
    is_ai_handled = Column(Boolean, default=True)  # Start with Novah, transfer to agent if needed
    ai_transferred_at = Column(DateTime, nullable=True)  # When transferred to human agent
    ai_resolution_status = Column(String(20), nullable=True)  # resolved_by_ai, transferred, abandoned

    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow)
    accepted_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User")
    agent = relationship("TeamMember", back_populates="chat_sessions")
    team = relationship("SupportTeam", back_populates="chat_sessions")
    ticket = relationship("SupportTicket", back_populates="chat_session")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at")


class ChatMessage(Base):
    """Messages within a chat session."""
    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("ix_chat_message_session", "session_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)

    # Sender
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    sender_type = Column(String(20), nullable=False)  # customer, agent, bot, system

    # Content
    message = Column(Text, nullable=False)
    message_type = Column(String(20), default="text")  # text, image, file, system

    # Read status
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    session = relationship("ChatSession", back_populates="messages")
    sender = relationship("User")


class AgentStatus(Base):
    """Agent availability status for chat routing."""
    __tablename__ = "agent_status"
    __table_args__ = (
        Index("ix_agent_status_member", "team_member_id"),
        Index("ix_agent_status_status", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    team_member_id = Column(Integer, ForeignKey("team_members.id"), unique=True, nullable=False)

    # Status
    status = Column(String(20), default="offline")  # online, away, busy, offline

    # Chat capacity
    current_chats = Column(Integer, default=0)
    max_chats = Column(Integer, default=3)

    # Activity tracking
    last_seen = Column(DateTime, default=datetime.utcnow)
    went_online_at = Column(DateTime, nullable=True)
    went_offline_at = Column(DateTime, nullable=True)

    # Relationships
    team_member = relationship("TeamMember", back_populates="agent_status")


class AdminActivityLog(Base):
    """Audit log for admin/team member actions."""
    __tablename__ = "admin_activity_logs"
    __table_args__ = (
        Index("ix_admin_log_user", "user_id"),
        Index("ix_admin_log_action", "action"),
        Index("ix_admin_log_timestamp", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Action details
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=True)  # ticket, team, user, subscription
    entity_id = Column(Integer, nullable=True)

    # Details
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User")


# =============================================================================
# KNOWLEDGE BASE & QA
# =============================================================================

class KnowledgeBaseArticle(Base):
    """Knowledge base articles for Novah AI assistant."""
    __tablename__ = "knowledge_base_articles"
    __table_args__ = (
        Index("ix_kb_category", "category"),
        Index("ix_kb_is_published", "is_published"),
    )

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)  # Short summary for search results

    # Categorization
    category = Column(String(50), nullable=False)  # faq, guide, troubleshooting, feature
    tags = Column(JSON, default=list)  # ["billing", "subscription", "pricing"]

    # URLs and references
    url = Column(String(500), nullable=True)  # Link to full documentation
    related_articles = Column(JSON, default=list)  # IDs of related articles

    # Status
    is_published = Column(Boolean, default=True)
    view_count = Column(Integer, default=0)
    helpful_count = Column(Integer, default=0)
    not_helpful_count = Column(Integer, default=0)

    # Metadata
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChatQARecord(Base):
    """QA review records for completed chat sessions."""
    __tablename__ = "chat_qa_records"
    __table_args__ = (
        Index("ix_qa_session", "session_id"),
        Index("ix_qa_reviewer", "reviewer_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Scores (1-5)
    overall_score = Column(Integer, nullable=False)
    response_time_score = Column(Integer, nullable=True)
    resolution_score = Column(Integer, nullable=True)
    professionalism_score = Column(Integer, nullable=True)

    # Notes
    notes = Column(Text, nullable=True)

    # Tags
    tags = Column(JSON, default=list)  # ["escalated", "resolved_first_contact", "novah_handled"]

    # Timestamps
    reviewed_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    session = relationship("ChatSession")
    reviewer = relationship("User")


# =============================================================================
# ADMIN ROLE CONSTANTS
# =============================================================================

class StaffRole:
    """Staff role constants."""
    SUPER_ADMIN = "super_admin"  # Only owner - can add/remove admins
    ADMIN = "admin"  # Same as super admin except cannot manage other admins
    MANAGER = "manager"  # Team manager
    AGENT = "agent"  # Support agent


class TicketCategory:
    """Ticket category constants."""
    BILLING = "billing"
    TECHNICAL = "technical"
    SALES = "sales"
    ACCOUNT = "account"
    GENERAL = "general"


class TicketStatus:
    """Ticket status constants."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_CUSTOMER = "waiting_customer"
    WAITING_INTERNAL = "waiting_internal"
    RESOLVED = "resolved"
    CLOSED = "closed"


# Category to team mapping
CATEGORY_TEAM_MAP = {
    "billing": "accounts",
    "payment": "accounts",
    "refund": "accounts",
    "subscription": "accounts",
    "technical": "tech-support",
    "bug": "tech-support",
    "installation": "tech-support",
    "feature": "tech-support",
    "sales": "sales",
    "pricing": "sales",
    "enterprise": "sales",
    "account": "tech-support",
    "general": "tech-support",
}


# =============================================================================
# USER INTEGRATIONS (SLACK, TEAMS, ETC.)
# =============================================================================

class UserIntegration(Base):
    """
    Third-party service integrations for users.

    Stores OAuth tokens and settings for Slack, Teams, and other integrations.
    """
    __tablename__ = "user_integrations"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_user_integration_provider"),
        Index("ix_user_integration_user", "user_id"),
        Index("ix_user_integration_provider", "provider"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Provider info
    provider = Column(String(50), nullable=False)  # slack, teams
    provider_user_id = Column(String(255), nullable=True)  # User ID in provider system
    provider_team_id = Column(String(255), nullable=True)  # Workspace/tenant ID
    provider_team_name = Column(String(255), nullable=True)  # Workspace/team display name

    # OAuth tokens (encrypted in production)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)

    # User info from provider
    display_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)

    # Settings
    default_channel_id = Column(String(255), nullable=True)  # Default channel for notifications
    default_channel_name = Column(String(255), nullable=True)
    notifications_enabled = Column(Boolean, default=True)
    meeting_summaries_enabled = Column(Boolean, default=True)
    action_item_reminders_enabled = Column(Boolean, default=True)
    briefing_notifications_enabled = Column(Boolean, default=True)

    # Status
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)  # Last error if any

    # Timestamps
    connected_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")


class IntegrationProvider:
    """Integration provider constants."""
    # Messaging integrations
    SLACK = "slack"
    TEAMS = "teams"

    # Video platform integrations (STEALTH MODE - calendar sync only)
    ZOOM = "zoom"
    GOOGLE_MEET = "google_meet"
    MICROSOFT_TEAMS_MEETING = "microsoft_teams"  # For video/calendar, separate from messaging
    WEBEX = "webex"


class IntegrationNotificationType:
    """Types of notifications that can be sent via integrations."""
    MEETING_SUMMARY = "meeting_summary"
    ACTION_ITEM_REMINDER = "action_item_reminder"
    BRIEFING = "briefing"
    COMMITMENT_REMINDER = "commitment_reminder"
