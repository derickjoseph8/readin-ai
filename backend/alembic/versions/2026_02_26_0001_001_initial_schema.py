"""Initial schema - captures existing database structure.

Revision ID: 001
Revises:
Create Date: 2026-02-26

This migration creates all tables for ReadIn AI backend.
It is designed to work with both SQLite (development) and PostgreSQL (production).

NOTE: If you already have an existing database with tables, you may need to:
1. Run: alembic stamp head
   (This marks the database as up-to-date without running migrations)
2. Or manually adjust this migration to handle existing tables
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables for ReadIn AI backend."""

    # ==========================================================================
    # PROFESSION MODEL
    # ==========================================================================
    op.create_table(
        'professions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('terminology', sa.JSON(), nullable=True),
        sa.Column('common_topics', sa.JSON(), nullable=True),
        sa.Column('system_prompt_additions', sa.Text(), nullable=True),
        sa.Column('communication_style', sa.String(), nullable=True),
        sa.Column('icon', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_professions_id', 'professions', ['id'], unique=False)
    op.create_index('ix_professions_name', 'professions', ['name'], unique=False)
    op.create_index('ix_professions_category', 'professions', ['category'], unique=False)

    # ==========================================================================
    # ORGANIZATION MODELS
    # ==========================================================================
    op.create_table(
        'organizations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('plan_type', sa.String(), nullable=True, default='team'),
        sa.Column('max_users', sa.Integer(), nullable=True, default=10),
        sa.Column('admin_user_id', sa.Integer(), nullable=True),
        sa.Column('billing_email', sa.String(), nullable=True),
        sa.Column('stripe_customer_id', sa.String(), nullable=True),
        sa.Column('subscription_id', sa.String(), nullable=True),
        sa.Column('subscription_status', sa.String(), nullable=True, default='trial'),
        sa.Column('subscription_end_date', sa.DateTime(), nullable=True),
        sa.Column('allow_personal_professions', sa.Boolean(), nullable=True, default=True),
        sa.Column('shared_insights_enabled', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('stripe_customer_id')
    )
    op.create_index('ix_organizations_id', 'organizations', ['id'], unique=False)

    # ==========================================================================
    # USER MODEL
    # ==========================================================================
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('profession_id', sa.Integer(), nullable=True),
        sa.Column('specialization', sa.String(), nullable=True),
        sa.Column('years_experience', sa.Integer(), nullable=True),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('role_in_org', sa.String(), nullable=True, default='member'),
        sa.Column('company', sa.String(), nullable=True),
        sa.Column('industry', sa.String(100), nullable=True),
        sa.Column('country', sa.String(100), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('is_staff', sa.Boolean(), nullable=True, default=False),
        sa.Column('staff_role', sa.String(50), nullable=True),
        sa.Column('stripe_customer_id', sa.String(), nullable=True),
        sa.Column('subscription_status', sa.String(), nullable=True, default='trial'),
        sa.Column('subscription_id', sa.String(), nullable=True),
        sa.Column('subscription_end_date', sa.DateTime(), nullable=True),
        sa.Column('trial_start_date', sa.DateTime(), nullable=True),
        sa.Column('trial_end_date', sa.DateTime(), nullable=True),
        sa.Column('email_notifications_enabled', sa.Boolean(), nullable=True, default=True),
        sa.Column('email_summary_enabled', sa.Boolean(), nullable=True, default=True),
        sa.Column('email_reminders_enabled', sa.Boolean(), nullable=True, default=True),
        sa.Column('totp_secret', sa.String(32), nullable=True),
        sa.Column('totp_enabled', sa.Boolean(), nullable=True, default=False),
        sa.Column('totp_backup_codes', sa.JSON(), nullable=True),
        sa.Column('consent_analytics', sa.Boolean(), nullable=True, default=False),
        sa.Column('consent_marketing', sa.Boolean(), nullable=True, default=False),
        sa.Column('consent_ai_training', sa.Boolean(), nullable=True, default=False),
        sa.Column('consent_updated_at', sa.DateTime(), nullable=True),
        sa.Column('sso_provider', sa.String(50), nullable=True),
        sa.Column('sso_provider_id', sa.String(255), nullable=True),
        sa.Column('google_refresh_token', sa.String(512), nullable=True),
        sa.Column('microsoft_refresh_token', sa.String(512), nullable=True),
        sa.Column('deletion_requested', sa.Boolean(), nullable=True, default=False),
        sa.Column('deletion_scheduled', sa.DateTime(), nullable=True),
        sa.Column('password_reset_token', sa.String(64), nullable=True),
        sa.Column('password_reset_expires', sa.DateTime(), nullable=True),
        sa.Column('email_verified', sa.Boolean(), nullable=True, default=False),
        sa.Column('email_verification_token', sa.String(64), nullable=True),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('timezone', sa.String(), nullable=True, default='UTC'),
        sa.Column('preferred_language', sa.String(), nullable=True, default='en'),
        sa.Column('trial_start', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.ForeignKeyConstraint(['profession_id'], ['professions.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('stripe_customer_id')
    )
    op.create_index('ix_users_id', 'users', ['id'], unique=False)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_created_at', 'users', ['created_at'], unique=False)
    op.create_index('ix_user_email_verification_token', 'users', ['email_verification_token'], unique=False)
    op.create_index('ix_user_password_reset_token', 'users', ['password_reset_token'], unique=False)

    # Add foreign key from organizations.admin_user_id to users.id
    # (Circular dependency resolved after users table exists)
    op.create_foreign_key(
        'fk_organizations_admin_user_id_users',
        'organizations', 'users',
        ['admin_user_id'], ['id']
    )

    # ==========================================================================
    # ORGANIZATION INVITE
    # ==========================================================================
    op.create_table(
        'organization_invites',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('invited_by_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(), nullable=True, default='member'),
        sa.Column('status', sa.String(), nullable=True, default='pending'),
        sa.Column('token', sa.String(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('accepted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['invited_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token')
    )
    op.create_index('ix_organization_invites_id', 'organization_invites', ['id'], unique=False)
    op.create_index('ix_organization_invites_email', 'organization_invites', ['email'], unique=False)

    # ==========================================================================
    # DAILY USAGE
    # ==========================================================================
    op.create_table(
        'daily_usage',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('response_count', sa.Integer(), nullable=True, default=0),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_daily_usage_id', 'daily_usage', ['id'], unique=False)

    # ==========================================================================
    # CALENDAR INTEGRATION
    # ==========================================================================
    op.create_table(
        'calendar_integrations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('access_token', sa.Text(), nullable=False),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('calendar_email', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('connected_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_calendar_integrations_id', 'calendar_integrations', ['id'], unique=False)
    op.create_index('ix_calendar_user_provider', 'calendar_integrations', ['user_id', 'provider'], unique=False)

    # ==========================================================================
    # MEETING MODEL
    # ==========================================================================
    op.create_table(
        'meetings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('meeting_type', sa.String(), nullable=True, default='general'),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('meeting_app', sa.String(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(), nullable=True, default='active'),
        sa.Column('participant_count', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_meetings_id', 'meetings', ['id'], unique=False)
    op.create_index('ix_meetings_status', 'meetings', ['status'], unique=False)
    op.create_index('ix_meeting_user_id', 'meetings', ['user_id'], unique=False)
    op.create_index('ix_meeting_user_status', 'meetings', ['user_id', 'status'], unique=False)
    op.create_index('ix_meeting_started_at', 'meetings', ['started_at'], unique=False)
    op.create_index('ix_meeting_user_date', 'meetings', ['user_id', 'started_at'], unique=False)

    # ==========================================================================
    # CONVERSATION MODEL
    # ==========================================================================
    op.create_table(
        'conversations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('meeting_id', sa.Integer(), nullable=False),
        sa.Column('speaker', sa.String(), nullable=True, default='other'),
        sa.Column('heard_text', sa.Text(), nullable=False),
        sa.Column('response_text', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('sentiment', sa.String(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['meeting_id'], ['meetings.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_conversations_id', 'conversations', ['id'], unique=False)
    op.create_index('ix_conversation_meeting_id', 'conversations', ['meeting_id'], unique=False)
    op.create_index('ix_conversation_timestamp', 'conversations', ['timestamp'], unique=False)

    # ==========================================================================
    # TOPIC MODEL
    # ==========================================================================
    op.create_table(
        'topics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('frequency', sa.Integer(), nullable=True, default=1),
        sa.Column('last_discussed', sa.DateTime(), nullable=True),
        sa.Column('embedding', sa.LargeBinary(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_topics_id', 'topics', ['id'], unique=False)
    op.create_index('ix_topics_name', 'topics', ['name'], unique=False)
    op.create_index('ix_topics_category', 'topics', ['category'], unique=False)
    op.create_index('ix_topics_frequency', 'topics', ['frequency'], unique=False)
    op.create_index('ix_topic_user_id', 'topics', ['user_id'], unique=False)
    op.create_index('ix_topic_user_frequency', 'topics', ['user_id', 'frequency'], unique=False)
    op.create_index('ix_topic_user_name', 'topics', ['user_id', 'name'], unique=False)

    # ==========================================================================
    # CONVERSATION TOPIC (Many-to-Many)
    # ==========================================================================
    op.create_table(
        'conversation_topics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('topic_id', sa.Integer(), nullable=False),
        sa.Column('relevance_score', sa.Float(), nullable=True, default=1.0),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ),
        sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # ==========================================================================
    # USER LEARNING PROFILE
    # ==========================================================================
    op.create_table(
        'user_learning_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('formality_level', sa.Float(), nullable=True, default=0.5),
        sa.Column('verbosity', sa.Float(), nullable=True, default=0.5),
        sa.Column('technical_depth', sa.Float(), nullable=True, default=0.5),
        sa.Column('frequent_topics', sa.JSON(), nullable=True),
        sa.Column('topic_expertise', sa.JSON(), nullable=True),
        sa.Column('avoided_topics', sa.JSON(), nullable=True),
        sa.Column('preferred_response_length', sa.Integer(), nullable=True, default=50),
        sa.Column('filler_words_used', sa.JSON(), nullable=True),
        sa.Column('strengths', sa.JSON(), nullable=True),
        sa.Column('areas_for_improvement', sa.JSON(), nullable=True),
        sa.Column('go_to_phrases', sa.JSON(), nullable=True),
        sa.Column('success_patterns', sa.JSON(), nullable=True),
        sa.Column('total_conversations_analyzed', sa.Integer(), nullable=True, default=0),
        sa.Column('confidence_score', sa.Float(), nullable=True, default=0.0),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index('ix_user_learning_profiles_id', 'user_learning_profiles', ['id'], unique=False)

    # ==========================================================================
    # ACTION ITEMS
    # ==========================================================================
    op.create_table(
        'action_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('meeting_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('assignee', sa.String(), nullable=False),
        sa.Column('assignee_role', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('priority', sa.String(), nullable=True, default='medium'),
        sa.Column('status', sa.String(), nullable=True, default='pending'),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['meeting_id'], ['meetings.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_action_items_id', 'action_items', ['id'], unique=False)
    op.create_index('ix_action_items_priority', 'action_items', ['priority'], unique=False)
    op.create_index('ix_action_items_status', 'action_items', ['status'], unique=False)
    op.create_index('ix_action_item_user_id', 'action_items', ['user_id'], unique=False)
    op.create_index('ix_action_item_user_status', 'action_items', ['user_id', 'status'], unique=False)
    op.create_index('ix_action_item_due_date', 'action_items', ['due_date'], unique=False)
    op.create_index('ix_action_item_meeting_id', 'action_items', ['meeting_id'], unique=False)

    # ==========================================================================
    # COMMITMENTS
    # ==========================================================================
    op.create_table(
        'commitments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('meeting_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('context', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=True, default='pending'),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('reminder_sent', sa.Boolean(), nullable=True, default=False),
        sa.Column('next_reminder_at', sa.DateTime(), nullable=True),
        sa.Column('reminder_count', sa.Integer(), nullable=True, default=0),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['meeting_id'], ['meetings.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_commitments_id', 'commitments', ['id'], unique=False)
    op.create_index('ix_commitments_status', 'commitments', ['status'], unique=False)
    op.create_index('ix_commitment_user_id', 'commitments', ['user_id'], unique=False)
    op.create_index('ix_commitment_user_status', 'commitments', ['user_id', 'status'], unique=False)
    op.create_index('ix_commitment_due_date', 'commitments', ['due_date'], unique=False)
    op.create_index('ix_commitment_next_reminder', 'commitments', ['next_reminder_at'], unique=False)

    # ==========================================================================
    # MEETING SUMMARIES
    # ==========================================================================
    op.create_table(
        'meeting_summaries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('meeting_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('summary_text', sa.Text(), nullable=True),
        sa.Column('key_points', sa.JSON(), nullable=True),
        sa.Column('decisions_made', sa.JSON(), nullable=True),
        sa.Column('sentiment', sa.String(), nullable=True),
        sa.Column('topics_discussed', sa.JSON(), nullable=True),
        sa.Column('email_sent', sa.Boolean(), nullable=True, default=False),
        sa.Column('email_sent_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['meeting_id'], ['meetings.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('meeting_id')
    )
    op.create_index('ix_meeting_summaries_id', 'meeting_summaries', ['id'], unique=False)

    # ==========================================================================
    # JOB APPLICATION & INTERVIEW
    # ==========================================================================
    op.create_table(
        'job_applications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('company', sa.String(), nullable=False),
        sa.Column('position', sa.String(), nullable=False),
        sa.Column('job_description', sa.Text(), nullable=True),
        sa.Column('job_url', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True, default='active'),
        sa.Column('salary_range', sa.String(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('applied_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_job_applications_id', 'job_applications', ['id'], unique=False)

    op.create_table(
        'interviews',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_application_id', sa.Integer(), nullable=False),
        sa.Column('meeting_id', sa.Integer(), nullable=True),
        sa.Column('interview_type', sa.String(), nullable=True),
        sa.Column('round_number', sa.Integer(), nullable=True, default=1),
        sa.Column('interviewer_name', sa.String(), nullable=True),
        sa.Column('interviewer_role', sa.String(), nullable=True),
        sa.Column('scheduled_at', sa.DateTime(), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('performance_score', sa.Float(), nullable=True),
        sa.Column('user_feeling', sa.String(), nullable=True),
        sa.Column('improvement_notes', sa.JSON(), nullable=True),
        sa.Column('questions_asked', sa.JSON(), nullable=True),
        sa.Column('strong_answers', sa.JSON(), nullable=True),
        sa.Column('weak_answers', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(), nullable=True, default='scheduled'),
        sa.Column('outcome', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['job_application_id'], ['job_applications.id'], ),
        sa.ForeignKeyConstraint(['meeting_id'], ['meetings.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_interviews_id', 'interviews', ['id'], unique=False)

    # ==========================================================================
    # PARTICIPANT MEMORY
    # ==========================================================================
    op.create_table(
        'participant_memories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('participant_name', sa.String(), nullable=False),
        sa.Column('participant_email', sa.String(), nullable=True),
        sa.Column('participant_role', sa.String(), nullable=True),
        sa.Column('company', sa.String(), nullable=True),
        sa.Column('key_points', sa.JSON(), nullable=True),
        sa.Column('preferences', sa.JSON(), nullable=True),
        sa.Column('topics_discussed', sa.JSON(), nullable=True),
        sa.Column('communication_style', sa.String(), nullable=True),
        sa.Column('relationship_notes', sa.Text(), nullable=True),
        sa.Column('meeting_count', sa.Integer(), nullable=True, default=1),
        sa.Column('last_interaction', sa.DateTime(), nullable=True),
        sa.Column('first_interaction', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_participant_memories_id', 'participant_memories', ['id'], unique=False)
    op.create_index('ix_participant_memories_participant_name', 'participant_memories', ['participant_name'], unique=False)
    op.create_index('ix_participant_memories_participant_email', 'participant_memories', ['participant_email'], unique=False)
    op.create_index('ix_participant_memories_company', 'participant_memories', ['company'], unique=False)
    op.create_index('ix_participant_memory_user_id', 'participant_memories', ['user_id'], unique=False)
    op.create_index('ix_participant_memory_user_name', 'participant_memories', ['user_id', 'participant_name'], unique=False)
    op.create_index('ix_participant_memory_last_interaction', 'participant_memories', ['last_interaction'], unique=False)

    # ==========================================================================
    # MEDIA APPEARANCES
    # ==========================================================================
    op.create_table(
        'media_appearances',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('meeting_id', sa.Integer(), nullable=True),
        sa.Column('show_name', sa.String(), nullable=False),
        sa.Column('network', sa.String(), nullable=True),
        sa.Column('host_name', sa.String(), nullable=True),
        sa.Column('topic', sa.String(), nullable=True),
        sa.Column('points_made', sa.JSON(), nullable=True),
        sa.Column('order_of_points', sa.JSON(), nullable=True),
        sa.Column('questions_asked', sa.JSON(), nullable=True),
        sa.Column('self_rating', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('aired_at', sa.DateTime(), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['meeting_id'], ['meetings.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_media_appearances_id', 'media_appearances', ['id'], unique=False)

    # ==========================================================================
    # EMAIL NOTIFICATIONS
    # ==========================================================================
    op.create_table(
        'email_notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('email_type', sa.String(), nullable=False),
        sa.Column('subject', sa.String(), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('recipient_email', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=True, default='pending'),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('related_meeting_id', sa.Integer(), nullable=True),
        sa.Column('related_commitment_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['related_commitment_id'], ['commitments.id'], ),
        sa.ForeignKeyConstraint(['related_meeting_id'], ['meetings.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_email_notifications_id', 'email_notifications', ['id'], unique=False)

    # ==========================================================================
    # PAYMENT HISTORY
    # ==========================================================================
    op.create_table(
        'payment_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('stripe_invoice_id', sa.String(), nullable=True),
        sa.Column('stripe_payment_intent_id', sa.String(), nullable=True),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(3), nullable=True, default='usd'),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_payment_history_id', 'payment_history', ['id'], unique=False)
    op.create_index('ix_payment_history_stripe_invoice_id', 'payment_history', ['stripe_invoice_id'], unique=False)

    # ==========================================================================
    # AUDIT LOG
    # ==========================================================================
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('resource_type', sa.String(), nullable=True),
        sa.Column('resource_id', sa.Integer(), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.Column('request_id', sa.String(), nullable=True),
        sa.Column('old_value', sa.JSON(), nullable=True),
        sa.Column('new_value', sa.JSON(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(), nullable=True, default='success'),
        sa.Column('failure_reason', sa.String(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_logs_id', 'audit_logs', ['id'], unique=False)
    op.create_index('ix_audit_logs_timestamp', 'audit_logs', ['timestamp'], unique=False)
    op.create_index('ix_audit_log_user_id', 'audit_logs', ['user_id'], unique=False)
    op.create_index('ix_audit_log_action', 'audit_logs', ['action'], unique=False)
    op.create_index('ix_audit_log_user_action', 'audit_logs', ['user_id', 'action'], unique=False)

    # ==========================================================================
    # PRE-MEETING BRIEFINGS
    # ==========================================================================
    op.create_table(
        'pre_meeting_briefings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('scheduled_time', sa.DateTime(), nullable=True),
        sa.Column('meeting_type', sa.String(), nullable=True, default='general'),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('participants', sa.JSON(), nullable=True),
        sa.Column('key_topics', sa.JSON(), nullable=True),
        sa.Column('suggested_questions', sa.JSON(), nullable=True),
        sa.Column('context_notes', sa.Text(), nullable=True),
        sa.Column('participant_memories_used', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(), nullable=True, default='generated'),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('viewed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_pre_meeting_briefings_id', 'pre_meeting_briefings', ['id'], unique=False)
    op.create_index('ix_briefing_user_id', 'pre_meeting_briefings', ['user_id'], unique=False)
    op.create_index('ix_briefing_scheduled_time', 'pre_meeting_briefings', ['scheduled_time'], unique=False)

    # ==========================================================================
    # ROLES (RBAC)
    # ==========================================================================
    op.create_table(
        'roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('permissions', sa.JSON(), nullable=True),
        sa.Column('is_system', sa.Boolean(), nullable=True, default=False),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index('ix_roles_id', 'roles', ['id'], unique=False)
    op.create_index('ix_roles_name', 'roles', ['name'], unique=False)

    # ==========================================================================
    # USER ROLES (Many-to-Many)
    # ==========================================================================
    op.create_table(
        'user_roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('assigned_by', sa.Integer(), nullable=True),
        sa.Column('assigned_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['assigned_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'role_id', name='uq_user_role')
    )
    op.create_index('ix_user_roles_id', 'user_roles', ['id'], unique=False)
    op.create_index('ix_user_role_user_id', 'user_roles', ['user_id'], unique=False)

    # ==========================================================================
    # SSO PROVIDERS
    # ==========================================================================
    op.create_table(
        'sso_providers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('provider_type', sa.String(50), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('is_default', sa.Boolean(), nullable=True, default=False),
        sa.Column('saml_entity_id', sa.String(500), nullable=True),
        sa.Column('saml_sso_url', sa.String(500), nullable=True),
        sa.Column('saml_slo_url', sa.String(500), nullable=True),
        sa.Column('saml_certificate', sa.Text(), nullable=True),
        sa.Column('saml_metadata_url', sa.String(500), nullable=True),
        sa.Column('oidc_client_id', sa.String(255), nullable=True),
        sa.Column('oidc_client_secret', sa.Text(), nullable=True),
        sa.Column('oidc_discovery_url', sa.String(500), nullable=True),
        sa.Column('oidc_authorization_url', sa.String(500), nullable=True),
        sa.Column('oidc_token_url', sa.String(500), nullable=True),
        sa.Column('oidc_userinfo_url', sa.String(500), nullable=True),
        sa.Column('oidc_scopes', sa.JSON(), nullable=True),
        sa.Column('attribute_mapping', sa.JSON(), nullable=True),
        sa.Column('auto_provision_users', sa.Boolean(), nullable=True, default=True),
        sa.Column('default_role_id', sa.Integer(), nullable=True),
        sa.Column('allowed_domains', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['default_role_id'], ['roles.id'], ),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'provider_type', name='uq_org_provider')
    )
    op.create_index('ix_sso_providers_id', 'sso_providers', ['id'], unique=False)
    op.create_index('ix_sso_provider_org', 'sso_providers', ['organization_id'], unique=False)

    # ==========================================================================
    # SSO SESSIONS
    # ==========================================================================
    op.create_table(
        'sso_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('provider_id', sa.Integer(), nullable=False),
        sa.Column('session_token', sa.String(255), nullable=False),
        sa.Column('external_session_id', sa.String(255), nullable=True),
        sa.Column('identity_data', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('last_activity', sa.DateTime(), nullable=True),
        sa.Column('terminated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['provider_id'], ['sso_providers.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_token')
    )
    op.create_index('ix_sso_sessions_id', 'sso_sessions', ['id'], unique=False)
    op.create_index('ix_sso_sessions_session_token', 'sso_sessions', ['session_token'], unique=False)
    op.create_index('ix_sso_session_user', 'sso_sessions', ['user_id'], unique=False)
    op.create_index('ix_sso_session_provider', 'sso_sessions', ['provider_id'], unique=False)
    op.create_index('ix_sso_session_external', 'sso_sessions', ['external_session_id'], unique=False)

    # ==========================================================================
    # API KEYS
    # ==========================================================================
    op.create_table(
        'api_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('key_prefix', sa.String(10), nullable=False),
        sa.Column('key_hash', sa.String(255), nullable=False),
        sa.Column('scopes', sa.JSON(), nullable=True),
        sa.Column('rate_limit_per_minute', sa.Integer(), nullable=True, default=60),
        sa.Column('rate_limit_per_day', sa.Integer(), nullable=True, default=10000),
        sa.Column('allowed_ips', sa.JSON(), nullable=True),
        sa.Column('allowed_ip_enabled', sa.Boolean(), nullable=True, default=False),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('last_used_ip', sa.String(45), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=True, default=0),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key_hash')
    )
    op.create_index('ix_api_keys_id', 'api_keys', ['id'], unique=False)
    op.create_index('ix_api_key_user', 'api_keys', ['user_id'], unique=False)
    op.create_index('ix_api_key_org', 'api_keys', ['organization_id'], unique=False)
    op.create_index('ix_api_key_hash', 'api_keys', ['key_hash'], unique=False)

    # ==========================================================================
    # WEBHOOKS
    # ==========================================================================
    op.create_table(
        'webhooks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('url', sa.String(500), nullable=False),
        sa.Column('secret', sa.String(255), nullable=True),
        sa.Column('events', sa.JSON(), nullable=True),
        sa.Column('custom_headers', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('max_retries', sa.Integer(), nullable=True, default=3),
        sa.Column('retry_delay_seconds', sa.Integer(), nullable=True, default=60),
        sa.Column('total_deliveries', sa.Integer(), nullable=True, default=0),
        sa.Column('successful_deliveries', sa.Integer(), nullable=True, default=0),
        sa.Column('failed_deliveries', sa.Integer(), nullable=True, default=0),
        sa.Column('last_triggered_at', sa.DateTime(), nullable=True),
        sa.Column('last_success_at', sa.DateTime(), nullable=True),
        sa.Column('last_failure_at', sa.DateTime(), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_webhooks_id', 'webhooks', ['id'], unique=False)
    op.create_index('ix_webhook_user', 'webhooks', ['user_id'], unique=False)
    op.create_index('ix_webhook_org', 'webhooks', ['organization_id'], unique=False)

    # ==========================================================================
    # WEBHOOK DELIVERIES
    # ==========================================================================
    op.create_table(
        'webhook_deliveries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('webhook_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(20), nullable=True, default='pending'),
        sa.Column('response_status_code', sa.Integer(), nullable=True),
        sa.Column('response_body', sa.Text(), nullable=True),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('attempt_count', sa.Integer(), nullable=True, default=1),
        sa.Column('next_retry_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('triggered_at', sa.DateTime(), nullable=True),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['webhook_id'], ['webhooks.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_webhook_deliveries_id', 'webhook_deliveries', ['id'], unique=False)
    op.create_index('ix_webhook_delivery_webhook', 'webhook_deliveries', ['webhook_id'], unique=False)
    op.create_index('ix_webhook_delivery_timestamp', 'webhook_deliveries', ['triggered_at'], unique=False)

    # ==========================================================================
    # WHITE-LABEL CONFIG
    # ==========================================================================
    op.create_table(
        'white_label_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('company_name', sa.String(100), nullable=True),
        sa.Column('logo_url', sa.String(500), nullable=True),
        sa.Column('favicon_url', sa.String(500), nullable=True),
        sa.Column('primary_color', sa.String(7), nullable=True, default='#d4af37'),
        sa.Column('secondary_color', sa.String(7), nullable=True, default='#10b981'),
        sa.Column('background_color', sa.String(7), nullable=True, default='#0a0a0a'),
        sa.Column('text_color', sa.String(7), nullable=True, default='#ffffff'),
        sa.Column('custom_domain', sa.String(255), nullable=True),
        sa.Column('domain_verified', sa.Boolean(), nullable=True, default=False),
        sa.Column('ssl_certificate', sa.Text(), nullable=True),
        sa.Column('email_from_name', sa.String(100), nullable=True),
        sa.Column('email_reply_to', sa.String(255), nullable=True),
        sa.Column('email_footer_text', sa.Text(), nullable=True),
        sa.Column('hide_powered_by', sa.Boolean(), nullable=True, default=False),
        sa.Column('custom_terms_url', sa.String(500), nullable=True),
        sa.Column('custom_privacy_url', sa.String(500), nullable=True),
        sa.Column('custom_support_email', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('custom_domain'),
        sa.UniqueConstraint('organization_id', name='uq_white_label_org')
    )
    op.create_index('ix_white_label_configs_id', 'white_label_configs', ['id'], unique=False)

    # ==========================================================================
    # USER SESSIONS
    # ==========================================================================
    op.create_table(
        'user_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_token', sa.String(255), nullable=False),
        sa.Column('refresh_token', sa.String(255), nullable=True),
        sa.Column('device_name', sa.String(255), nullable=True),
        sa.Column('device_type', sa.String(50), nullable=True),
        sa.Column('browser', sa.String(100), nullable=True),
        sa.Column('os', sa.String(100), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('is_current', sa.Boolean(), nullable=True, default=False),
        sa.Column('last_activity', sa.DateTime(), nullable=True),
        sa.Column('last_ip', sa.String(45), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('refresh_token'),
        sa.UniqueConstraint('session_token')
    )
    op.create_index('ix_user_sessions_id', 'user_sessions', ['id'], unique=False)
    op.create_index('ix_user_sessions_session_token', 'user_sessions', ['session_token'], unique=False)
    op.create_index('ix_user_session_user_id', 'user_sessions', ['user_id'], unique=False)
    op.create_index('ix_user_session_token', 'user_sessions', ['session_token'], unique=False)
    op.create_index('ix_user_session_expires', 'user_sessions', ['expires_at'], unique=False)

    # ==========================================================================
    # LOGIN ATTEMPTS
    # ==========================================================================
    op.create_table(
        'login_attempts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(512), nullable=True),
        sa.Column('device_type', sa.String(50), nullable=True),
        sa.Column('browser', sa.String(100), nullable=True),
        sa.Column('os', sa.String(100), nullable=True),
        sa.Column('country', sa.String(100), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=True, default=False),
        sa.Column('failure_reason', sa.String(255), nullable=True),
        sa.Column('is_new_device', sa.Boolean(), nullable=True, default=False),
        sa.Column('is_new_location', sa.Boolean(), nullable=True, default=False),
        sa.Column('is_suspicious', sa.Boolean(), nullable=True, default=False),
        sa.Column('anomaly_score', sa.Float(), nullable=True, default=0.0),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_login_attempts_id', 'login_attempts', ['id'], unique=False)
    op.create_index('ix_login_attempt_user_id', 'login_attempts', ['user_id'], unique=False)
    op.create_index('ix_login_attempt_email', 'login_attempts', ['email'], unique=False)
    op.create_index('ix_login_attempt_ip', 'login_attempts', ['ip_address'], unique=False)
    op.create_index('ix_login_attempt_timestamp', 'login_attempts', ['timestamp'], unique=False)

    # ==========================================================================
    # SECURITY ALERTS
    # ==========================================================================
    op.create_table(
        'security_alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('alert_type', sa.String(50), nullable=False),
        sa.Column('severity', sa.String(20), nullable=True, default='medium'),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('device_info', sa.JSON(), nullable=True),
        sa.Column('location_info', sa.JSON(), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=True, default=False),
        sa.Column('is_resolved', sa.Boolean(), nullable=True, default=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_security_alerts_id', 'security_alerts', ['id'], unique=False)
    op.create_index('ix_security_alert_user_id', 'security_alerts', ['user_id'], unique=False)
    op.create_index('ix_security_alert_type', 'security_alerts', ['alert_type'], unique=False)

    # ==========================================================================
    # TRUSTED DEVICES
    # ==========================================================================
    op.create_table(
        'trusted_devices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('device_fingerprint', sa.String(255), nullable=False),
        sa.Column('device_name', sa.String(255), nullable=True),
        sa.Column('device_type', sa.String(50), nullable=True),
        sa.Column('browser', sa.String(100), nullable=True),
        sa.Column('os', sa.String(100), nullable=True),
        sa.Column('last_used', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_trusted_devices_id', 'trusted_devices', ['id'], unique=False)
    op.create_index('ix_trusted_device_user_id', 'trusted_devices', ['user_id'], unique=False)

    # ==========================================================================
    # IN-APP NOTIFICATIONS
    # ==========================================================================
    op.create_table(
        'in_app_notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(100), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('data', sa.JSON(), nullable=True),
        sa.Column('priority', sa.String(20), nullable=True, default='normal'),
        sa.Column('is_read', sa.Boolean(), nullable=True, default=False),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_in_app_notifications_id', 'in_app_notifications', ['id'], unique=False)
    op.create_index('ix_in_app_notification_user', 'in_app_notifications', ['user_id'], unique=False)
    op.create_index('ix_in_app_notification_read', 'in_app_notifications', ['user_id', 'is_read'], unique=False)

    # ==========================================================================
    # TEMPLATES
    # ==========================================================================
    op.create_table(
        'templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('template_type', sa.String(50), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('variables', sa.JSON(), nullable=True),
        sa.Column('default_values', sa.JSON(), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=True, default=False),
        sa.Column('is_system', sa.Boolean(), nullable=True, default=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('version', sa.Integer(), nullable=True, default=1),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.ForeignKeyConstraint(['parent_id'], ['templates.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'name', name='uq_user_template_name')
    )
    op.create_index('ix_templates_id', 'templates', ['id'], unique=False)
    op.create_index('ix_template_user', 'templates', ['user_id'], unique=False)
    op.create_index('ix_template_type', 'templates', ['template_type'], unique=False)

    # ==========================================================================
    # USER AI PREFERENCES
    # ==========================================================================
    op.create_table(
        'user_ai_preferences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('preferred_model', sa.String(50), nullable=True, default='sonnet'),
        sa.Column('fallback_model', sa.String(50), nullable=True, default='haiku'),
        sa.Column('response_length', sa.String(20), nullable=True, default='medium'),
        sa.Column('response_style', sa.String(50), nullable=True, default='professional'),
        sa.Column('bullet_points', sa.Boolean(), nullable=True, default=True),
        sa.Column('include_sources', sa.Boolean(), nullable=True, default=False),
        sa.Column('monthly_budget_cents', sa.Integer(), nullable=True),
        sa.Column('current_month_usage_cents', sa.Integer(), nullable=True, default=0),
        sa.Column('budget_alert_threshold', sa.Float(), nullable=True, default=0.8),
        sa.Column('temperature', sa.Float(), nullable=True, default=0.7),
        sa.Column('max_tokens', sa.Integer(), nullable=True, default=1000),
        sa.Column('custom_instructions', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index('ix_user_ai_preferences_id', 'user_ai_preferences', ['id'], unique=False)

    # ==========================================================================
    # ANALYTICS EVENTS
    # ==========================================================================
    op.create_table(
        'analytics_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('event_category', sa.String(50), nullable=True),
        sa.Column('event_action', sa.String(100), nullable=True),
        sa.Column('properties', sa.JSON(), nullable=True),
        sa.Column('value', sa.Float(), nullable=True),
        sa.Column('session_id', sa.String(100), nullable=True),
        sa.Column('source', sa.String(50), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_analytics_events_id', 'analytics_events', ['id'], unique=False)
    op.create_index('ix_analytics_user', 'analytics_events', ['user_id'], unique=False)
    op.create_index('ix_analytics_event', 'analytics_events', ['event_type'], unique=False)
    op.create_index('ix_analytics_timestamp', 'analytics_events', ['timestamp'], unique=False)

    # ==========================================================================
    # SUPPORT TEAMS
    # ==========================================================================
    op.create_table(
        'support_teams',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('slug', sa.String(50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color', sa.String(7), nullable=True, default='#3B82F6'),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('accepts_tickets', sa.Boolean(), nullable=True, default=True),
        sa.Column('accepts_chat', sa.Boolean(), nullable=True, default=True),
        sa.Column('working_hours', sa.JSON(), nullable=True),
        sa.Column('timezone', sa.String(50), nullable=True, default='UTC'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )
    op.create_index('ix_support_teams_id', 'support_teams', ['id'], unique=False)
    op.create_index('ix_support_teams_slug', 'support_teams', ['slug'], unique=False)

    # ==========================================================================
    # TEAM MEMBERS
    # ==========================================================================
    op.create_table(
        'team_members',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(50), nullable=True, default='agent'),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('joined_at', sa.DateTime(), nullable=True),
        sa.Column('removed_at', sa.DateTime(), nullable=True),
        sa.Column('invited_by_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['invited_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['team_id'], ['support_teams.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'team_id', name='uq_user_team')
    )
    op.create_index('ix_team_members_id', 'team_members', ['id'], unique=False)
    op.create_index('ix_team_member_user', 'team_members', ['user_id'], unique=False)
    op.create_index('ix_team_member_team', 'team_members', ['team_id'], unique=False)

    # ==========================================================================
    # TEAM INVITES
    # ==========================================================================
    op.create_table(
        'team_invites',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), nullable=True, default='agent'),
        sa.Column('token', sa.String(100), nullable=False),
        sa.Column('invited_by_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), nullable=True, default='pending'),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('accepted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['invited_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['team_id'], ['support_teams.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token')
    )
    op.create_index('ix_team_invites_id', 'team_invites', ['id'], unique=False)
    op.create_index('ix_team_invite_email', 'team_invites', ['email'], unique=False)
    op.create_index('ix_team_invite_token', 'team_invites', ['token'], unique=False)

    # ==========================================================================
    # SLA CONFIGS
    # ==========================================================================
    op.create_table(
        'sla_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('priority', sa.String(20), nullable=False),
        sa.Column('first_response_minutes', sa.Integer(), nullable=False),
        sa.Column('resolution_minutes', sa.Integer(), nullable=False),
        sa.Column('escalation_enabled', sa.Boolean(), nullable=True, default=True),
        sa.Column('escalation_after_minutes', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('priority')
    )
    op.create_index('ix_sla_configs_id', 'sla_configs', ['id'], unique=False)

    # ==========================================================================
    # SUPPORT TICKETS
    # ==========================================================================
    op.create_table(
        'support_tickets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticket_number', sa.String(20), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=True),
        sa.Column('assigned_to_id', sa.Integer(), nullable=True),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('priority', sa.String(20), nullable=True, default='medium'),
        sa.Column('status', sa.String(30), nullable=True, default='open'),
        sa.Column('subject', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('sla_first_response_due', sa.DateTime(), nullable=True),
        sa.Column('sla_resolution_due', sa.DateTime(), nullable=True),
        sa.Column('first_response_at', sa.DateTime(), nullable=True),
        sa.Column('sla_breached', sa.Boolean(), nullable=True, default=False),
        sa.Column('source', sa.String(30), nullable=True, default='dashboard'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['assigned_to_id'], ['team_members.id'], ),
        sa.ForeignKeyConstraint(['team_id'], ['support_teams.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ticket_number')
    )
    op.create_index('ix_support_tickets_id', 'support_tickets', ['id'], unique=False)
    op.create_index('ix_ticket_user', 'support_tickets', ['user_id'], unique=False)
    op.create_index('ix_ticket_team', 'support_tickets', ['team_id'], unique=False)
    op.create_index('ix_ticket_status', 'support_tickets', ['status'], unique=False)
    op.create_index('ix_ticket_priority', 'support_tickets', ['priority'], unique=False)
    op.create_index('ix_ticket_number', 'support_tickets', ['ticket_number'], unique=False)

    # ==========================================================================
    # TICKET MESSAGES
    # ==========================================================================
    op.create_table(
        'ticket_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticket_id', sa.Integer(), nullable=False),
        sa.Column('sender_user_id', sa.Integer(), nullable=True),
        sa.Column('sender_member_id', sa.Integer(), nullable=True),
        sa.Column('sender_type', sa.String(20), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('attachments', sa.JSON(), nullable=True),
        sa.Column('is_internal', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['sender_member_id'], ['team_members.id'], ),
        sa.ForeignKeyConstraint(['sender_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['ticket_id'], ['support_tickets.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ticket_messages_id', 'ticket_messages', ['id'], unique=False)
    op.create_index('ix_ticket_message_ticket', 'ticket_messages', ['ticket_id'], unique=False)

    # ==========================================================================
    # CHAT SESSIONS
    # ==========================================================================
    op.create_table(
        'chat_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_token', sa.String(100), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.Integer(), nullable=True),
        sa.Column('team_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(20), nullable=True, default='waiting'),
        sa.Column('ticket_id', sa.Integer(), nullable=True),
        sa.Column('queue_position', sa.Integer(), nullable=True),
        sa.Column('is_ai_handled', sa.Boolean(), nullable=True, default=True),
        sa.Column('ai_transferred_at', sa.DateTime(), nullable=True),
        sa.Column('ai_resolution_status', sa.String(20), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('accepted_at', sa.DateTime(), nullable=True),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['team_members.id'], ),
        sa.ForeignKeyConstraint(['team_id'], ['support_teams.id'], ),
        sa.ForeignKeyConstraint(['ticket_id'], ['support_tickets.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_token')
    )
    op.create_index('ix_chat_sessions_id', 'chat_sessions', ['id'], unique=False)
    op.create_index('ix_chat_session_user', 'chat_sessions', ['user_id'], unique=False)
    op.create_index('ix_chat_session_agent', 'chat_sessions', ['agent_id'], unique=False)
    op.create_index('ix_chat_session_status', 'chat_sessions', ['status'], unique=False)

    # ==========================================================================
    # CHAT MESSAGES
    # ==========================================================================
    op.create_table(
        'chat_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('sender_id', sa.Integer(), nullable=True),
        sa.Column('sender_type', sa.String(20), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('message_type', sa.String(20), nullable=True, default='text'),
        sa.Column('is_read', sa.Boolean(), nullable=True, default=False),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_chat_messages_id', 'chat_messages', ['id'], unique=False)
    op.create_index('ix_chat_message_session', 'chat_messages', ['session_id'], unique=False)

    # ==========================================================================
    # AGENT STATUS
    # ==========================================================================
    op.create_table(
        'agent_status',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('team_member_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), nullable=True, default='offline'),
        sa.Column('current_chats', sa.Integer(), nullable=True, default=0),
        sa.Column('max_chats', sa.Integer(), nullable=True, default=3),
        sa.Column('last_seen', sa.DateTime(), nullable=True),
        sa.Column('went_online_at', sa.DateTime(), nullable=True),
        sa.Column('went_offline_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['team_member_id'], ['team_members.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('team_member_id')
    )
    op.create_index('ix_agent_status_id', 'agent_status', ['id'], unique=False)
    op.create_index('ix_agent_status_member', 'agent_status', ['team_member_id'], unique=False)
    op.create_index('ix_agent_status_status', 'agent_status', ['status'], unique=False)

    # ==========================================================================
    # ADMIN ACTIVITY LOGS
    # ==========================================================================
    op.create_table(
        'admin_activity_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=True),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_admin_activity_logs_id', 'admin_activity_logs', ['id'], unique=False)
    op.create_index('ix_admin_log_user', 'admin_activity_logs', ['user_id'], unique=False)
    op.create_index('ix_admin_log_action', 'admin_activity_logs', ['action'], unique=False)
    op.create_index('ix_admin_log_timestamp', 'admin_activity_logs', ['created_at'], unique=False)

    # ==========================================================================
    # KNOWLEDGE BASE ARTICLES
    # ==========================================================================
    op.create_table(
        'knowledge_base_articles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('url', sa.String(500), nullable=True),
        sa.Column('related_articles', sa.JSON(), nullable=True),
        sa.Column('is_published', sa.Boolean(), nullable=True, default=True),
        sa.Column('view_count', sa.Integer(), nullable=True, default=0),
        sa.Column('helpful_count', sa.Integer(), nullable=True, default=0),
        sa.Column('not_helpful_count', sa.Integer(), nullable=True, default=0),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_knowledge_base_articles_id', 'knowledge_base_articles', ['id'], unique=False)
    op.create_index('ix_kb_category', 'knowledge_base_articles', ['category'], unique=False)
    op.create_index('ix_kb_is_published', 'knowledge_base_articles', ['is_published'], unique=False)

    # ==========================================================================
    # CHAT QA RECORDS
    # ==========================================================================
    op.create_table(
        'chat_qa_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('reviewer_id', sa.Integer(), nullable=False),
        sa.Column('overall_score', sa.Integer(), nullable=False),
        sa.Column('response_time_score', sa.Integer(), nullable=True),
        sa.Column('resolution_score', sa.Integer(), nullable=True),
        sa.Column('professionalism_score', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['reviewer_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_chat_qa_records_id', 'chat_qa_records', ['id'], unique=False)
    op.create_index('ix_qa_session', 'chat_qa_records', ['session_id'], unique=False)
    op.create_index('ix_qa_reviewer', 'chat_qa_records', ['reviewer_id'], unique=False)

    # ==========================================================================
    # USER INTEGRATIONS
    # ==========================================================================
    op.create_table(
        'user_integrations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('provider_user_id', sa.String(255), nullable=True),
        sa.Column('provider_team_id', sa.String(255), nullable=True),
        sa.Column('provider_team_name', sa.String(255), nullable=True),
        sa.Column('access_token', sa.Text(), nullable=False),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(), nullable=True),
        sa.Column('instance_url', sa.String(500), nullable=True),
        sa.Column('org_id', sa.String(255), nullable=True),
        sa.Column('auto_sync_contacts', sa.Boolean(), nullable=True, default=True),
        sa.Column('auto_log_meetings', sa.Boolean(), nullable=True, default=True),
        sa.Column('auto_sync_notes', sa.Boolean(), nullable=True, default=False),
        sa.Column('auto_create_tasks', sa.Boolean(), nullable=True, default=False),
        sa.Column('display_name', sa.String(255), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('default_channel_id', sa.String(255), nullable=True),
        sa.Column('default_channel_name', sa.String(255), nullable=True),
        sa.Column('notifications_enabled', sa.Boolean(), nullable=True, default=True),
        sa.Column('meeting_summaries_enabled', sa.Boolean(), nullable=True, default=True),
        sa.Column('action_item_reminders_enabled', sa.Boolean(), nullable=True, default=True),
        sa.Column('briefing_notifications_enabled', sa.Boolean(), nullable=True, default=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('connected_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'provider', name='uq_user_integration_provider')
    )
    op.create_index('ix_user_integrations_id', 'user_integrations', ['id'], unique=False)
    op.create_index('ix_user_integration_user', 'user_integrations', ['user_id'], unique=False)
    op.create_index('ix_user_integration_provider', 'user_integrations', ['provider'], unique=False)

    # ==========================================================================
    # WEBAUTHN CREDENTIALS
    # ==========================================================================
    op.create_table(
        'webauthn_credentials',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('credential_id', sa.String(512), nullable=False),
        sa.Column('public_key', sa.Text(), nullable=False),
        sa.Column('sign_count', sa.Integer(), nullable=False, default=0),
        sa.Column('device_name', sa.String(100), nullable=True, default='Security Key'),
        sa.Column('device_type', sa.String(50), nullable=True),
        sa.Column('attestation_type', sa.String(50), nullable=True),
        sa.Column('aaguid', sa.String(36), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('credential_id', name='uq_webauthn_credential_id')
    )
    op.create_index('ix_webauthn_credentials_id', 'webauthn_credentials', ['id'], unique=False)
    op.create_index('ix_webauthn_user_id', 'webauthn_credentials', ['user_id'], unique=False)
    op.create_index('ix_webauthn_credential_id', 'webauthn_credentials', ['credential_id'], unique=False)


def downgrade() -> None:
    """Drop all tables in reverse order."""
    # Drop tables in reverse order of creation to handle foreign key dependencies

    op.drop_table('webauthn_credentials')
    op.drop_table('user_integrations')
    op.drop_table('chat_qa_records')
    op.drop_table('knowledge_base_articles')
    op.drop_table('admin_activity_logs')
    op.drop_table('agent_status')
    op.drop_table('chat_messages')
    op.drop_table('chat_sessions')
    op.drop_table('ticket_messages')
    op.drop_table('support_tickets')
    op.drop_table('sla_configs')
    op.drop_table('team_invites')
    op.drop_table('team_members')
    op.drop_table('support_teams')
    op.drop_table('analytics_events')
    op.drop_table('user_ai_preferences')
    op.drop_table('templates')
    op.drop_table('in_app_notifications')
    op.drop_table('trusted_devices')
    op.drop_table('security_alerts')
    op.drop_table('login_attempts')
    op.drop_table('user_sessions')
    op.drop_table('white_label_configs')
    op.drop_table('webhook_deliveries')
    op.drop_table('webhooks')
    op.drop_table('api_keys')
    op.drop_table('sso_sessions')
    op.drop_table('sso_providers')
    op.drop_table('user_roles')
    op.drop_table('roles')
    op.drop_table('pre_meeting_briefings')
    op.drop_table('audit_logs')
    op.drop_table('payment_history')
    op.drop_table('email_notifications')
    op.drop_table('media_appearances')
    op.drop_table('participant_memories')
    op.drop_table('interviews')
    op.drop_table('job_applications')
    op.drop_table('meeting_summaries')
    op.drop_table('commitments')
    op.drop_table('action_items')
    op.drop_table('user_learning_profiles')
    op.drop_table('conversation_topics')
    op.drop_table('topics')
    op.drop_table('conversations')
    op.drop_table('meetings')
    op.drop_table('calendar_integrations')
    op.drop_table('daily_usage')
    op.drop_table('organization_invites')

    # Drop the foreign key from organizations to users before dropping users
    op.drop_constraint('fk_organizations_admin_user_id_users', 'organizations', type_='foreignkey')

    op.drop_table('users')
    op.drop_table('organizations')
    op.drop_table('professions')
