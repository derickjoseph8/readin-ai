"""Pydantic schemas for request/response validation."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field


# =============================================================================
# AUTH SCHEMAS
# =============================================================================

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    profession_id: Optional[int] = None
    specialization: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


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
    terminology: Optional[Dict[str, Any]] = None
    common_topics: Optional[List[str]] = None
    system_prompt_additions: Optional[str] = None
    communication_style: Optional[str] = None
    icon: Optional[str] = None


class ProfessionResponse(ProfessionBase):
    id: int
    terminology: Optional[Dict[str, Any]] = None
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
    name: str
    plan_type: str = "team"  # team, business, enterprise
    billing_email: Optional[str] = None


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
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
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    profession_id: Optional[int] = None
    specialization: Optional[str] = None
    years_experience: Optional[int] = None


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
    meeting_type: str = "general"  # interview, tv_appearance, manager_meeting, general
    title: Optional[str] = None
    meeting_app: Optional[str] = None
    participant_count: Optional[int] = None


class MeetingEnd(BaseModel):
    notes: Optional[str] = None
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
    meeting_id: int
    speaker: str = "other"  # user, other, unknown
    heard_text: str
    response_text: Optional[str] = None


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
    meeting_id: int
    assignee: str
    assignee_role: Optional[str] = None
    description: str
    due_date: Optional[datetime] = None
    priority: str = "medium"


class ActionItemUpdate(BaseModel):
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Optional[str] = None
    status: Optional[str] = None


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
    meeting_id: int
    description: str
    due_date: Optional[datetime] = None
    context: Optional[str] = None


class CommitmentUpdate(BaseModel):
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    status: Optional[str] = None


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
# FORWARD REFERENCES
# =============================================================================

# Update forward references for nested models
MeetingDetail.model_rebuild()
JobApplicationDetail.model_rebuild()
