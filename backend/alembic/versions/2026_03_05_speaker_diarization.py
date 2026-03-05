"""Add speaker diarization support

Revision ID: speaker_diarization_202603
Revises: enhanced_summary_202603
Create Date: 2026-03-05

This migration adds:
1. Speaker table for voice profiles
2. speaker_id and speaker_name columns to conversations
3. start_time and end_time columns for audio sync
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'speaker_diarization_202603'
down_revision = 'enhanced_summary_202603'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add speaker diarization support."""

    # Create speakers table
    op.create_table(
        'speakers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('speaker_id', sa.String(50), nullable=False),
        sa.Column('display_name', sa.String(100), nullable=True),
        sa.Column('voice_embedding', sa.Text(), nullable=True),
        sa.Column('total_meetings', sa.Integer(), default=0),
        sa.Column('total_speaking_time', sa.Float(), default=0.0),
        sa.Column('first_seen', sa.DateTime(), nullable=True),
        sa.Column('last_seen', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'speaker_id', name='uq_user_speaker_id')
    )

    # Create indexes for speakers table
    op.create_index('ix_speaker_user_id', 'speakers', ['user_id'])
    op.create_index('ix_speaker_speaker_id', 'speakers', ['speaker_id'])
    op.create_index('ix_speakers_id', 'speakers', ['id'])

    # Add speaker columns to conversations
    with op.batch_alter_table('conversations', schema=None) as batch_op:
        # Speaker identification
        batch_op.add_column(sa.Column('speaker_id', sa.String(50), nullable=True))
        batch_op.add_column(sa.Column('speaker_name', sa.String(100), nullable=True))

        # Timing for audio sync
        batch_op.add_column(sa.Column('start_time', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('end_time', sa.Float(), nullable=True))

        # Create index for speaker_id
        batch_op.create_index('ix_conversation_speaker_id', ['speaker_id'])


def downgrade() -> None:
    """Remove speaker diarization support."""

    # Remove columns from conversations
    with op.batch_alter_table('conversations', schema=None) as batch_op:
        batch_op.drop_index('ix_conversation_speaker_id')
        batch_op.drop_column('end_time')
        batch_op.drop_column('start_time')
        batch_op.drop_column('speaker_name')
        batch_op.drop_column('speaker_id')

    # Drop speakers table
    op.drop_index('ix_speakers_id', table_name='speakers')
    op.drop_index('ix_speaker_speaker_id', table_name='speakers')
    op.drop_index('ix_speaker_user_id', table_name='speakers')
    op.drop_table('speakers')
