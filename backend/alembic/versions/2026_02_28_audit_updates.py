"""Add Paystack fields, indexes, and audit improvements

Revision ID: audit_updates_202602
Revises:
Create Date: 2026-02-28

This migration adds:
1. Paystack payment fields to User model
2. Subscription management fields
3. Missing indexes for performance
4. Payment history improvements (idempotency, Paystack)
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'audit_updates_202602'
down_revision = '001'  # Previous migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add new columns and indexes."""

    # Add Paystack fields to users table
    with op.batch_alter_table('users', schema=None) as batch_op:
        # Paystack payment fields
        batch_op.add_column(sa.Column('paystack_customer_code', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('paystack_authorization_code', sa.String(), nullable=True))

        # Subscription management fields
        batch_op.add_column(sa.Column('subscription_seats', sa.Integer(), server_default='1', nullable=True))
        batch_op.add_column(sa.Column('subscription_plan', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('subscription_region', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('subscription_is_annual', sa.Boolean(), server_default='false', nullable=True))
        batch_op.add_column(sa.Column('subscription_billing_cycle_start', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('country_code', sa.String(2), nullable=True))

        # Add indexes
        batch_op.create_index('ix_users_paystack_customer_code', ['paystack_customer_code'], unique=False)
        batch_op.create_index('ix_users_subscription_status', ['subscription_status'], unique=False)

    # Add index to daily_usage table
    with op.batch_alter_table('daily_usage', schema=None) as batch_op:
        batch_op.create_index('ix_daily_usage_user_date', ['user_id', 'date'], unique=False)

    # Add index to calendar_integrations table
    with op.batch_alter_table('calendar_integrations', schema=None) as batch_op:
        batch_op.create_index('ix_calendar_user_id', ['user_id'], unique=False)

    # Add Paystack and idempotency fields to payment_history table
    with op.batch_alter_table('payment_history', schema=None) as batch_op:
        batch_op.add_column(sa.Column('paystack_reference', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('paystack_transaction_id', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('payment_provider', sa.String(), server_default='stripe', nullable=True))
        batch_op.add_column(sa.Column('idempotency_key', sa.String(), nullable=True))

        # Add indexes
        batch_op.create_index('ix_payment_history_paystack_reference', ['paystack_reference'], unique=False)
        batch_op.create_index('ix_payment_history_idempotency_key', ['idempotency_key'], unique=True)
        batch_op.create_index('ix_payment_history_user_id', ['user_id'], unique=False)
        batch_op.create_index('ix_payment_history_created_at', ['created_at'], unique=False)


def downgrade() -> None:
    """Remove added columns and indexes."""

    # Remove from payment_history
    with op.batch_alter_table('payment_history', schema=None) as batch_op:
        batch_op.drop_index('ix_payment_history_created_at')
        batch_op.drop_index('ix_payment_history_user_id')
        batch_op.drop_index('ix_payment_history_idempotency_key')
        batch_op.drop_index('ix_payment_history_paystack_reference')
        batch_op.drop_column('idempotency_key')
        batch_op.drop_column('payment_provider')
        batch_op.drop_column('paystack_transaction_id')
        batch_op.drop_column('paystack_reference')

    # Remove from calendar_integrations
    with op.batch_alter_table('calendar_integrations', schema=None) as batch_op:
        batch_op.drop_index('ix_calendar_user_id')

    # Remove from daily_usage
    with op.batch_alter_table('daily_usage', schema=None) as batch_op:
        batch_op.drop_index('ix_daily_usage_user_date')

    # Remove from users
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index('ix_users_subscription_status')
        batch_op.drop_index('ix_users_paystack_customer_code')
        batch_op.drop_column('country_code')
        batch_op.drop_column('subscription_billing_cycle_start')
        batch_op.drop_column('subscription_is_annual')
        batch_op.drop_column('subscription_region')
        batch_op.drop_column('subscription_plan')
        batch_op.drop_column('subscription_seats')
        batch_op.drop_column('paystack_authorization_code')
        batch_op.drop_column('paystack_customer_code')
