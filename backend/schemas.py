"""Pydantic schemas for request/response validation."""

import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict

from config import (
    PASSWORD_MIN_LENGTH,
    PASSWORD_REQUIRE_UPPERCASE,
    PASSWORD_REQUIRE_LOWERCASE,
    PASSWORD_REQUIRE_DIGIT,
    PASSWORD_REQUIRE_SPECIAL,
)


# =============================================================================
# VALIDATORS
# =============================================================================

def validate_password(password: str) -> str:
    """
    Validate password meets security requirements.

    Requirements (configurable):
    - Minimum length (default 12 characters)
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    """
    errors = []

    if len(password) < PASSWORD_MIN_LENGTH:
        errors.append(f"Password must be at least {PASSWORD_MIN_LENGTH} characters")

    if PASSWORD_REQUIRE_UPPERCASE and not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")

    if PASSWORD_REQUIRE_LOWERCASE and not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")

    if PASSWORD_REQUIRE_DIGIT and not re.search(r"\d", password):
        errors.append("Password must contain at least one digit")

    if PASSWORD_REQUIRE_SPECIAL and not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        errors.append("Password must contain at least one special character (!@#$%^&*(),.?\":{}|<>)")

    if errors:
        raise ValueError("; ".join(errors))

    return password


def validate_string_length(value: str, field_name: str, max_length: int) -> str:
    """Validate string doesn't exceed maximum length."""
    if value and len(value) > max_length:
        raise ValueError(f"{field_name} must not exceed {max_length} characters")
    return value


# =============================================================================
# AUTH SCHEMAS
# =============================================================================

class UserCreate(BaseModel):
    """User registration schema with password validation."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, max_length=255)
    profession_id: Optional[int] = Field(None, ge=1)
    specialization: Optional[str] = Field(None, max_length=255)
    preferred_language: Optional[str] = Field(default="en", pattern="^(en|es|sw)$")
    account_type: Optional[str] = Field(default="individual", pattern="^(individual|business)$")
    company_name: Optional[str] = Field(None, max_length=255)

    @field_validator("password")
    @classmethod
    def password_validation(cls, v: str) -> str:
        return validate_password(v)

    @field_validator("full_name")
    @classmethod
    def full_name_validation(cls, v: Optional[str]) -> Optional[str]:
        if v:
            # Remove excessive whitespace
            v = " ".join(v.split())
            # Check for potentially dangerous characters
            if re.search(r"[<>\"']", v):
                raise ValueError("Name contains invalid characters")
        return v


class UserLogin(BaseModel):
    """User login schema."""
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PasswordChangeRequest(BaseModel):
    """Password change request schema."""
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return validate_password(v)


class TokenData(BaseModel):
    user_id: Optional[int] = None


# =============================================================================
# PROFESSION SCHEMAS
# =============================================================================

class ProfessionBase(BaseModel):
    name: str
    category: Optional[str] = None
    description: Optional[str] = None


class ProfessionCreate(ProfessionBase):
    terminology: Optional[List[str]] = None
    common_topics: Optional[List[str]] = None
    system_prompt_additions: Optional[str] = None
    communication_style: Optional[str] = None
    icon: Optional[str] = None


class ProfessionResponse(ProfessionBase):
    id: int
    terminology: Optional[List[str]] = None
    common_topics: Optional[List[str]] = None
    communication_style: Optional[str] = None
    icon: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


class ProfessionList(BaseModel):
    professions: List[ProfessionResponse]
    total: int


class ProfessionCategory(BaseModel):
    category: str
    professions: List[ProfessionResponse]


# =============================================================================
# ORGANIZATION SCHEMAS
# =============================================================================

class OrganizationCreate(BaseModel):
    """Organization creation schema with validation."""
    name: str = Field(..., min_length=2, max_length=255)
    plan_type: str = Field("team", pattern="^(team|business|enterprise)$")
    billing_email: Optional[EmailStr] = None

    @field_validator("name")
    @classmethod
    def name_validation(cls, v: str) -> str:
        v = " ".join(v.split())  # Normalize whitespace
        if re.search(r"[<>\"']", v):
            raise ValueError("Name contains invalid characters")
        return v


class OrganizationUpdate(BaseModel):
    """Organization update schema with validation."""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    allow_personal_professions: Optional[bool] = None
    shared_insights_enabled: Optional[bool] = None


class OrganizationResponse(BaseModel):
    id: int
    name: str
    plan_type: str
    max_users: int
    subscription_status: str
    member_count: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class OrganizationInviteCreate(BaseModel):
    email: EmailStr
    role: str = "member"


class OrganizationInviteResponse(BaseModel):
    id: int
    email: str
    role: str
    status: str
    expires_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class OrganizationMember(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    role_in_org: str
    profession: Optional[str] = None
    joined_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# USER SCHEMAS (UPDATED)
# =============================================================================

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    profession_id: Optional[int] = None
    profession_name: Optional[str] = None
    specialization: Optional[str] = None
    organization_id: Optional[int] = None
    organization_name: Optional[str] = None
    role_in_org: Optional[str] = None
    subscription_status: str
    trial_days_remaining: int
    is_active: bool
    email_notifications_enabled: bool
    email_summary_enabled: bool
    email_reminders_enabled: bool
    preferred_language: str = "en"
    account_type: str = "individual"
    company_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    profession_id: Optional[int] = None
    profession: Optional[str] = None  # String name, will be mapped to profession_id
    company: Optional[str] = None
    specialization: Optional[str] = None
    years_experience: Optional[int] = None
    preferred_language: Optional[str] = Field(None, pattern="^(en|es|sw)$")


class UserEmailPreferences(BaseModel):
    email_notifications_enabled: Optional[bool] = None
    email_summary_enabled: Optional[bool] = None
    email_reminders_enabled: Optional[bool] = None


class UserStatus(BaseModel):
    """Status check response for desktop app."""
    is_active: bool
    subscription_status: str
    trial_days_remaining: int
    daily_usage: int
    daily_limit: Optional[int]
    can_use: bool
    profession_name: Optional[str] = None
    organization_name: Optional[str] = None


# =============================================================================
# MEETING SCHEMAS
# =============================================================================

class MeetingCreate(BaseModel):
    """Meeting creation schema with validation."""
    meeting_type: str = Field(
        "general",
        pattern="^(interview|tv_appearance|manager_meeting|general|panel|webinar|phone_call)$"
    )
    title: Optional[str] = Field(None, max_length=500)
    meeting_app: Optional[str] = Field(None, max_length=100)
    participant_count: Optional[int] = Field(None, ge=1, le=1000)


class MeetingEnd(BaseModel):
    """Meeting end schema with validation."""
    notes: Optional[str] = Field(None, max_length=10000)
    generate_summary: bool = True
    send_email: bool = True


class MeetingResponse(BaseModel):
    id: int
    meeting_type: str
    title: Optional[str]
    meeting_app: Optional[str]
    started_at: datetime
    ended_at: Optional[datetime]
    duration_seconds: Optional[int]
    status: str
    participant_count: Optional[int]
    conversation_count: Optional[int] = None

    class Config:
        from_attributes = True


class MeetingDetail(MeetingResponse):
    conversations: List["ConversationResponse"] = []
    action_items: List["ActionItemResponse"] = []
    commitments: List["CommitmentResponse"] = []
    summary: Optional["MeetingSummaryResponse"] = None


class MeetingList(BaseModel):
    meetings: List[MeetingResponse]
    total: int


# =============================================================================
# CONVERSATION SCHEMAS
# =============================================================================

class ConversationCreate(BaseModel):
    """Conversation creation schema with validation."""
    meeting_id: int = Field(..., ge=1)
    speaker: str = Field("other", pattern="^(user|other|unknown)$")
    heard_text: str = Field(..., min_length=1, max_length=50000)
    response_text: Optional[str] = Field(None, max_length=50000)


class ConversationResponse(BaseModel):
    id: int
    meeting_id: int
    speaker: str
    heard_text: str
    response_text: Optional[str]
    timestamp: datetime
    sentiment: Optional[str] = None

    class Config:
        from_attributes = True


# =============================================================================
# TOPIC SCHEMAS
# =============================================================================

class TopicResponse(BaseModel):
    id: int
    name: str
    category: Optional[str]
    frequency: int
    last_discussed: datetime

    class Config:
        from_attributes = True


class TopicAnalytics(BaseModel):
    topics: List[TopicResponse]
    total_topics: int
    top_categories: Dict[str, int]


# =============================================================================
# USER LEARNING PROFILE SCHEMAS
# =============================================================================

class UserLearningProfileResponse(BaseModel):
    formality_level: float
    verbosity: float
    technical_depth: float
    frequent_topics: Dict[str, int]
    topic_expertise: Dict[str, float]
    strengths: List[str]
    areas_for_improvement: List[str]
    preferred_response_length: int
    go_to_phrases: List[str]
    total_conversations_analyzed: int
    confidence_score: float
    updated_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# ACTION ITEM SCHEMAS
# =============================================================================

class ActionItemCreate(BaseModel):
    """Action item creation schema with validation."""
    meeting_id: int = Field(..., ge=1)
    assignee: str = Field(..., min_length=1, max_length=255)
    assignee_role: Optional[str] = Field(None, max_length=100)
    description: str = Field(..., min_length=1, max_length=2000)
    due_date: Optional[datetime] = None
    priority: str = Field("medium", pattern="^(low|medium|high|urgent)$")


class ActionItemUpdate(BaseModel):
    """Action item update schema with validation."""
    description: Optional[str] = Field(None, min_length=1, max_length=2000)
    due_date: Optional[datetime] = None
    priority: Optional[str] = Field(None, pattern="^(low|medium|high|urgent)$")
    status: Optional[str] = Field(None, pattern="^(pending|in_progress|completed|cancelled)$")


class ActionItemResponse(BaseModel):
    id: int
    meeting_id: int
    assignee: str
    assignee_role: Optional[str]
    description: str
    due_date: Optional[datetime]
    priority: str
    status: str
    completed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class ActionItemList(BaseModel):
    action_items: List[ActionItemResponse]
    total: int
    pending_count: int
    completed_count: int


# =============================================================================
# COMMITMENT SCHEMAS
# =============================================================================

class CommitmentCreate(BaseModel):
    """Commitment creation schema with validation."""
    meeting_id: int = Field(..., ge=1)
    description: str = Field(..., min_length=1, max_length=2000)
    due_date: Optional[datetime] = None
    context: Optional[str] = Field(None, max_length=2000)


class CommitmentUpdate(BaseModel):
    """Commitment update schema with validation."""
    description: Optional[str] = Field(None, min_length=1, max_length=2000)
    due_date: Optional[datetime] = None
    status: Optional[str] = Field(None, pattern="^(pending|completed|overdue)$")


class CommitmentResponse(BaseModel):
    id: int
    meeting_id: int
    description: str
    due_date: Optional[datetime]
    context: Optional[str]
    status: str
    reminder_sent: bool
    next_reminder_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class CommitmentList(BaseModel):
    commitments: List[CommitmentResponse]
    total: int
    upcoming: List[CommitmentResponse]
    overdue: List[CommitmentResponse]


# =============================================================================
# MEETING SUMMARY SCHEMAS
# =============================================================================

class MeetingSummaryResponse(BaseModel):
    id: int
    meeting_id: int
    summary_text: Optional[str]
    key_points: Optional[List[str]]
    decisions_made: Optional[List[str]]
    sentiment: Optional[str]
    topics_discussed: Optional[List[str]]
    email_sent: bool
    email_sent_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class MeetingSummaryRequest(BaseModel):
    regenerate: bool = False
    send_email: bool = True


# =============================================================================
# JOB APPLICATION SCHEMAS
# =============================================================================

class JobApplicationCreate(BaseModel):
    company: str
    position: str
    job_description: Optional[str] = None
    job_url: Optional[str] = None
    salary_range: Optional[str] = None
    notes: Optional[str] = None
    applied_at: Optional[datetime] = None


class JobApplicationUpdate(BaseModel):
    company: Optional[str] = None
    position: Optional[str] = None
    status: Optional[str] = None
    job_description: Optional[str] = None
    salary_range: Optional[str] = None
    notes: Optional[str] = None


class JobApplicationResponse(BaseModel):
    id: int
    company: str
    position: str
    status: str
    job_description: Optional[str]
    job_url: Optional[str]
    salary_range: Optional[str]
    notes: Optional[str]
    applied_at: Optional[datetime]
    interview_count: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class JobApplicationDetail(JobApplicationResponse):
    interviews: List["InterviewResponse"] = []
    improvement_suggestions: Optional[List[str]] = None


class JobApplicationList(BaseModel):
    applications: List[JobApplicationResponse]
    total: int
    by_status: Dict[str, int]


# =============================================================================
# INTERVIEW SCHEMAS
# =============================================================================

class InterviewCreate(BaseModel):
    job_application_id: int
    interview_type: Optional[str] = None
    round_number: int = 1
    interviewer_name: Optional[str] = None
    interviewer_role: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None


class InterviewUpdate(BaseModel):
    interview_type: Optional[str] = None
    interviewer_name: Optional[str] = None
    interviewer_role: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    user_feeling: Optional[str] = None
    status: Optional[str] = None
    outcome: Optional[str] = None


class InterviewResponse(BaseModel):
    id: int
    job_application_id: int
    meeting_id: Optional[int]
    interview_type: Optional[str]
    round_number: int
    interviewer_name: Optional[str]
    interviewer_role: Optional[str]
    scheduled_at: Optional[datetime]
    duration_minutes: Optional[int]
    performance_score: Optional[float]
    user_feeling: Optional[str]
    status: str
    outcome: Optional[str]
    improvement_notes: List[str]
    strong_answers: List[str]
    weak_answers: List[str]
    created_at: datetime

    class Config:
        from_attributes = True


class InterviewLinkMeeting(BaseModel):
    meeting_id: int


# =============================================================================
# PARTICIPANT MEMORY SCHEMAS
# =============================================================================

class ParticipantMemoryCreate(BaseModel):
    participant_name: str
    participant_email: Optional[str] = None
    participant_role: Optional[str] = None
    company: Optional[str] = None
    relationship_notes: Optional[str] = None


class ParticipantMemoryUpdate(BaseModel):
    participant_role: Optional[str] = None
    company: Optional[str] = None
    relationship_notes: Optional[str] = None
    key_points: Optional[List[str]] = None
    preferences: Optional[Dict[str, Any]] = None


class ParticipantMemoryResponse(BaseModel):
    id: int
    participant_name: str
    participant_email: Optional[str]
    participant_role: Optional[str]
    company: Optional[str]
    key_points: List[str]
    preferences: Dict[str, Any]
    topics_discussed: List[str]
    communication_style: Optional[str]
    relationship_notes: Optional[str]
    meeting_count: int
    last_interaction: datetime
    first_interaction: datetime

    class Config:
        from_attributes = True


class ParticipantMemoryList(BaseModel):
    participants: List[ParticipantMemoryResponse]
    total: int


# =============================================================================
# MEDIA APPEARANCE SCHEMAS
# =============================================================================

class MediaAppearanceCreate(BaseModel):
    show_name: str
    network: Optional[str] = None
    host_name: Optional[str] = None
    topic: Optional[str] = None
    aired_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None


class MediaAppearanceUpdate(BaseModel):
    points_made: Optional[List[str]] = None
    order_of_points: Optional[List[int]] = None
    questions_asked: Optional[List[str]] = None
    self_rating: Optional[int] = None
    notes: Optional[str] = None


class MediaAppearanceResponse(BaseModel):
    id: int
    meeting_id: Optional[int]
    show_name: str
    network: Optional[str]
    host_name: Optional[str]
    topic: Optional[str]
    points_made: List[str]
    questions_asked: List[str]
    self_rating: Optional[int]
    notes: Optional[str]
    aired_at: Optional[datetime]
    duration_minutes: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class MediaAppearanceList(BaseModel):
    appearances: List[MediaAppearanceResponse]
    total: int


class MediaVarietySuggestion(BaseModel):
    suggested_points: List[str]
    avoid_points: List[str]
    reason: str


# =============================================================================
# EMAIL NOTIFICATION SCHEMAS
# =============================================================================

class EmailNotificationResponse(BaseModel):
    id: int
    email_type: str
    subject: str
    status: str
    sent_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class EmailPreferencesUpdate(BaseModel):
    email_notifications_enabled: Optional[bool] = None
    email_summary_enabled: Optional[bool] = None
    email_reminders_enabled: Optional[bool] = None


class SendEmailRequest(BaseModel):
    email_type: str  # meeting_summary, commitment_reminder, briefing
    related_id: int  # meeting_id or commitment_id


# =============================================================================
# BRIEFING SCHEMAS
# =============================================================================

class BriefingRequest(BaseModel):
    meeting_type: str = "general"
    participant_names: Optional[List[str]] = None
    topics: Optional[List[str]] = None


class BriefingResponse(BaseModel):
    meeting_type: str
    participant_context: List[Dict[str, Any]]
    suggested_topics: List[str]
    topics_to_avoid: List[str]
    past_commitments: List[CommitmentResponse]
    key_points_to_follow_up: List[str]
    generated_at: datetime


class ParticipantBriefing(BaseModel):
    participant_name: str
    role: Optional[str]
    company: Optional[str]
    key_points: List[str]
    communication_style: Optional[str]
    last_interaction: Optional[datetime]
    topics_they_care_about: List[str]


# =============================================================================
# ANALYTICS SCHEMAS
# =============================================================================

class MeetingAnalytics(BaseModel):
    total_meetings: int
    meetings_by_type: Dict[str, int]
    total_conversations: int
    average_meeting_duration: Optional[float]
    meetings_this_week: int
    meetings_this_month: int


class TopicAnalyticsResponse(BaseModel):
    top_topics: List[TopicResponse]
    topic_categories: Dict[str, int]
    trending_topics: List[TopicResponse]


class PerformanceAnalytics(BaseModel):
    interview_count: int
    average_performance_score: Optional[float]
    improvement_areas: List[str]
    strengths: List[str]
    success_rate: Optional[float]


# =============================================================================
# SUBSCRIPTION SCHEMAS
# =============================================================================

class CreateCheckoutSession(BaseModel):
    price_id: Optional[str] = None
    plan_type: str = "premium"  # premium, team, business


class CheckoutSessionResponse(BaseModel):
    checkout_url: str


class SubscriptionResponse(BaseModel):
    status: str
    current_period_end: Optional[datetime]
    cancel_at_period_end: bool
    plan_type: Optional[str] = None


# =============================================================================
# USAGE SCHEMAS
# =============================================================================

class UsageIncrement(BaseModel):
    """Increment usage count."""
    pass


class UsageResponse(BaseModel):
    date: str
    count: int
    limit: Optional[int]
    remaining: Optional[int]


# =============================================================================
# SUPPORT TEAM SCHEMAS
# =============================================================================

class SupportTeamCreate(BaseModel):
    """Support team creation schema."""
    name: str = Field(..., min_length=2, max_length=100)
    slug: str = Field(..., min_length=2, max_length=50, pattern="^[a-z0-9-]+$")
    description: Optional[str] = Field(None, max_length=500)
    color: str = Field("#3B82F6", pattern="^#[0-9A-Fa-f]{6}$")
    accepts_tickets: bool = True
    accepts_chat: bool = True
    working_hours: Optional[Dict[str, Any]] = None
    timezone: str = Field("UTC", max_length=50)


class SupportTeamUpdate(BaseModel):
    """Support team update schema."""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    is_active: Optional[bool] = None
    accepts_tickets: Optional[bool] = None
    accepts_chat: Optional[bool] = None
    working_hours: Optional[Dict[str, Any]] = None
    timezone: Optional[str] = Field(None, max_length=50)


class SupportTeamResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str]
    color: str
    is_active: bool
    accepts_tickets: bool
    accepts_chat: bool
    working_hours: Optional[Dict[str, Any]]
    timezone: str
    member_count: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SupportTeamList(BaseModel):
    teams: List[SupportTeamResponse]
    total: int


# =============================================================================
# TEAM MEMBER SCHEMAS
# =============================================================================

class TeamMemberCreate(BaseModel):
    """Team member assignment schema."""
    user_id: int
    role: str = Field("agent", pattern="^(admin|manager|agent)$")


class TeamMemberInvite(BaseModel):
    """Team member invitation schema."""
    email: EmailStr
    role: str = Field("agent", pattern="^(admin|manager|agent)$")
    team_id: int


class TeamMemberResponse(BaseModel):
    id: int
    user_id: int
    team_id: int
    role: str
    is_active: bool
    joined_at: datetime
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    team_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TeamMemberList(BaseModel):
    members: List[TeamMemberResponse]
    total: int


class TeamInviteResponse(BaseModel):
    id: int
    team_id: int
    email: str
    role: str
    status: str
    expires_at: datetime
    created_at: datetime
    team_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# SLA SCHEMAS
# =============================================================================

class SLAConfigCreate(BaseModel):
    """SLA configuration creation schema."""
    priority: str = Field(..., pattern="^(urgent|high|medium|low)$")
    first_response_minutes: int = Field(..., ge=1)
    resolution_minutes: int = Field(..., ge=1)
    escalation_enabled: bool = True
    escalation_after_minutes: Optional[int] = Field(None, ge=1)


class SLAConfigUpdate(BaseModel):
    """SLA configuration update schema."""
    first_response_minutes: Optional[int] = Field(None, ge=1)
    resolution_minutes: Optional[int] = Field(None, ge=1)
    escalation_enabled: Optional[bool] = None
    escalation_after_minutes: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = None


class SLAConfigResponse(BaseModel):
    id: int
    priority: str
    first_response_minutes: int
    resolution_minutes: int
    escalation_enabled: bool
    escalation_after_minutes: Optional[int]
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# SUPPORT TICKET SCHEMAS
# =============================================================================

class TicketCreate(BaseModel):
    """Support ticket creation schema."""
    category: str = Field(..., pattern="^(billing|technical|sales|account|general)$")
    priority: str = Field("medium", pattern="^(urgent|high|medium|low)$")
    subject: str = Field(..., min_length=5, max_length=255)
    description: str = Field(..., min_length=10, max_length=10000)


class TicketUpdate(BaseModel):
    """Support ticket update schema."""
    priority: Optional[str] = Field(None, pattern="^(urgent|high|medium|low)$")
    status: Optional[str] = Field(None, pattern="^(open|in_progress|waiting_customer|waiting_internal|resolved|closed)$")
    team_id: Optional[int] = None
    assigned_to_id: Optional[int] = None


class TicketResponse(BaseModel):
    id: int
    ticket_number: str
    user_id: int
    team_id: Optional[int]
    assigned_to_id: Optional[int]
    category: str
    priority: str
    status: str
    subject: str
    description: str
    source: str
    sla_first_response_due: Optional[datetime]
    sla_resolution_due: Optional[datetime]
    first_response_at: Optional[datetime]
    sla_breached: bool
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]
    closed_at: Optional[datetime]
    # Related data
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    team_name: Optional[str] = None
    assigned_to_name: Optional[str] = None
    message_count: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class TicketDetail(TicketResponse):
    messages: List["TicketMessageResponse"] = []


class TicketList(BaseModel):
    tickets: List[TicketResponse]
    total: int
    by_status: Dict[str, int]
    by_priority: Dict[str, int]


class TicketMessageCreate(BaseModel):
    """Ticket message creation schema."""
    message: str = Field(..., min_length=1, max_length=10000)
    is_internal: bool = False
    attachments: Optional[List[str]] = None


class TicketMessageResponse(BaseModel):
    id: int
    ticket_id: int
    sender_type: str
    message: str
    attachments: List[str]
    is_internal: bool
    created_at: datetime
    sender_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# CHAT SESSION SCHEMAS
# =============================================================================

class ChatSessionCreate(BaseModel):
    """Chat session initiation schema."""
    team_id: Optional[int] = None


class ChatSessionResponse(BaseModel):
    id: int
    session_token: str
    user_id: int
    agent_id: Optional[int]
    team_id: Optional[int]
    status: str
    queue_position: Optional[int]
    started_at: datetime
    accepted_at: Optional[datetime]
    ended_at: Optional[datetime]
    ticket_id: Optional[int]
    user_name: Optional[str] = None
    agent_name: Optional[str] = None
    team_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ChatSessionList(BaseModel):
    sessions: List[ChatSessionResponse]
    total: int
    waiting: int
    active: int


class ChatMessageCreate(BaseModel):
    """Chat message creation schema."""
    message: str = Field(..., min_length=1, max_length=5000)
    message_type: str = Field("text", pattern="^(text|image|file|system)$")


class ChatMessageResponse(BaseModel):
    id: int
    session_id: int
    sender_type: str
    message: str
    message_type: str
    is_read: bool
    created_at: datetime
    sender_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# AGENT STATUS SCHEMAS
# =============================================================================

class AgentStatusUpdate(BaseModel):
    """Agent status update schema."""
    status: str = Field(..., pattern="^(online|away|busy|offline)$")
    max_chats: Optional[int] = Field(None, ge=1, le=10)


class AgentStatusResponse(BaseModel):
    id: int
    team_member_id: int
    status: str
    current_chats: int
    max_chats: int
    last_seen: datetime
    agent_name: Optional[str] = None
    team_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# ADMIN DASHBOARD SCHEMAS
# =============================================================================

class AdminDashboardStats(BaseModel):
    """Admin dashboard statistics."""
    # Users
    total_users: int
    active_users: int
    trial_users: int
    paying_users: int
    new_users_today: int
    new_users_this_week: int
    new_users_this_month: int

    # Subscriptions
    total_revenue_this_month: float
    mrr: float  # Monthly recurring revenue
    churn_rate: float

    # Support
    open_tickets: int
    tickets_today: int
    avg_response_time_minutes: float
    sla_breach_rate: float
    active_chats: int
    waiting_chats: int

    # Teams
    total_teams: int
    online_agents: int
    total_agents: int


class TicketTrend(BaseModel):
    """Ticket trend data point."""
    date: str
    count: int
    resolved: int
    avg_response_minutes: Optional[float]


class SubscriptionTrend(BaseModel):
    """Subscription trend data point."""
    date: str
    new_subscriptions: int
    cancellations: int
    revenue: float


class AdminTrends(BaseModel):
    """Admin dashboard trends."""
    tickets: List[TicketTrend]
    subscriptions: List[SubscriptionTrend]
    period: str  # daily, weekly, monthly


class AdminActivityLogResponse(BaseModel):
    id: int
    user_id: int
    action: str
    entity_type: Optional[str]
    entity_id: Optional[int]
    details: Optional[Dict[str, Any]]
    ip_address: Optional[str]
    created_at: datetime
    user_email: Optional[str] = None
    user_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# FORWARD REFERENCES
# =============================================================================

# Update forward references for nested models
MeetingDetail.model_rebuild()
JobApplicationDetail.model_rebuild()
TicketDetail.model_rebuild()
