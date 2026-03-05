"""Add embedding and transcript editing columns

Revision ID: embedding_columns_202603
Revises: speaker_diarization_202603
Create Date: 2026-03-05

This migration adds:
1. embedding column to meetings table (for semantic search)
2. embedding column to conversations table (for semantic search)
3. transcript editing columns to conversations table
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'embedding_columns_202603'
down_revision = 'speaker_diarization_202603'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add embedding and transcript editing columns."""

    # Add embedding to meetings
    with op.batch_alter_table('meetings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('embedding', sa.JSON(), nullable=True))

    # Add embedding and transcript editing columns to conversations
    with op.batch_alter_table('conversations', schema=None) as batch_op:
        batch_op.add_column(sa.Column('embedding', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('original_text', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('edited_text', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('is_edited', sa.Boolean(), default=False))
        batch_op.add_column(sa.Column('edited_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Remove embedding and transcript editing columns."""

    with op.batch_alter_table('conversations', schema=None) as batch_op:
        batch_op.drop_column('edited_at')
        batch_op.drop_column('is_edited')
        batch_op.drop_column('edited_text')
        batch_op.drop_column('original_text')
        batch_op.drop_column('embedding')

    with op.batch_alter_table('meetings', schema=None) as batch_op:
        batch_op.drop_column('embedding')
