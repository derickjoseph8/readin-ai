"""Add enhanced AI summary fields to meeting_summaries

Revision ID: enhanced_summary_202603
Revises: ai_qa_fields_202602
Create Date: 2026-03-04

This migration adds enhanced AI analysis fields to meeting_summaries:
1. risks_identified - JSON array of identified risks with severity and mitigation
2. follow_up_suggestions - JSON array of recommended follow-up actions
3. action_item_summary - Text executive summary of action items
4. participant_contributions - JSON mapping of topics to participants
5. meeting_effectiveness_score - Integer 1-10 score for meeting quality
6. next_steps - JSON array of recommended next steps
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'enhanced_summary_202603'
down_revision = 'ai_qa_fields_202602'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add enhanced AI analysis fields to meeting_summaries table."""

    with op.batch_alter_table('meeting_summaries', schema=None) as batch_op:
        # Risk identification
        batch_op.add_column(sa.Column('risks_identified', sa.JSON(), nullable=True))

        # Follow-up suggestions
        batch_op.add_column(sa.Column('follow_up_suggestions', sa.JSON(), nullable=True))

        # Action item summary (executive summary of all action items)
        batch_op.add_column(sa.Column('action_item_summary', sa.Text(), nullable=True))

        # Participant contributions mapping (topic -> participants)
        batch_op.add_column(sa.Column('participant_contributions', sa.JSON(), nullable=True))

        # Meeting effectiveness score (1-10)
        batch_op.add_column(sa.Column('meeting_effectiveness_score', sa.Integer(), nullable=True))

        # Recommended next steps
        batch_op.add_column(sa.Column('next_steps', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Remove enhanced AI analysis fields."""

    with op.batch_alter_table('meeting_summaries', schema=None) as batch_op:
        batch_op.drop_column('next_steps')
        batch_op.drop_column('meeting_effectiveness_score')
        batch_op.drop_column('participant_contributions')
        batch_op.drop_column('action_item_summary')
        batch_op.drop_column('follow_up_suggestions')
        batch_op.drop_column('risks_identified')
