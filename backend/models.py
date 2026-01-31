"""SQLAlchemy database models for ReadIn AI."""

from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Date, ForeignKey, Text, Float, LargeBinary, JSON
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
    commitments = relationship("Commitment", back_populates="user")
    job_applications = relationship("JobApplication", back_populates="user")
    learning_profile = relationship("UserLearningProfile", back_populates="user", uselist=False)
    participant_memories = relationship("ParticipantMemory", back_populates="user")
    media_appearances = relationship("MediaAppearance", back_populates="user")
    email_notifications = relationship("EmailNotification", back_populates="user")

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


# =============================================================================
# MEETING & CONVERSATION MODELS
# =============================================================================

class Meeting(Base):
    """Meeting session tracking."""
    __tablename__ = "meetings"

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
    status = Column(String, default="active")  # active, ended, cancelled

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

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    name = Column(String, nullable=False, index=True)
    category = Column(String)  # technical, behavioral, situational, company-specific

    # Frequency tracking
    frequency = Column(Integer, default=1)
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

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Assignment
    assignee = Column(String, nullable=False)  # Name of person responsible
    assignee_role = Column(String)  # user, other, team

    # Task details
    description = Column(Text, nullable=False)
    due_date = Column(DateTime, nullable=True)
    priority = Column(String, default="medium")  # low, medium, high

    # Status
    status = Column(String, default="pending")  # pending, in_progress, completed, cancelled
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

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Commitment details
    description = Column(Text, nullable=False)
    due_date = Column(DateTime, nullable=True)
    context = Column(Text, nullable=True)  # Why/to whom the commitment was made

    # Status
    status = Column(String, default="pending")  # pending, completed, overdue
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

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Participant info
    participant_name = Column(String, nullable=False, index=True)
    participant_email = Column(String, nullable=True)
    participant_role = Column(String, nullable=True)
    company = Column(String, nullable=True)

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
