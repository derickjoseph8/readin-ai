"""Add AI-powered QA fields to chat_qa_records

Revision ID: ai_qa_fields_202602
Revises: audit_updates_202602
Create Date: 2026-02-28

This migration adds:
1. is_ai_review - Boolean flag to identify AI reviews
2. ai_analysis - JSON field for detailed AI analysis
3. ai_confidence - Float for AI confidence score
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ai_qa_fields_202602'
down_revision = 'audit_updates_202602'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add AI QA fields to chat_qa_records table."""

    with op.batch_alter_table('chat_qa_records', schema=None) as batch_op:
        # AI Review tracking
        batch_op.add_column(sa.Column('is_ai_review', sa.Boolean(), nullable=True, server_default='false'))
        batch_op.add_column(sa.Column('ai_analysis', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('ai_confidence', sa.Float(), nullable=True))

    # Set default values for existing records
    op.execute("UPDATE chat_qa_records SET is_ai_review = false WHERE is_ai_review IS NULL")


def downgrade() -> None:
    """Remove AI QA fields."""

    with op.batch_alter_table('chat_qa_records', schema=None) as batch_op:
        batch_op.drop_column('ai_confidence')
        batch_op.drop_column('ai_analysis')
        batch_op.drop_column('is_ai_review')
