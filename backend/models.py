"""SQLAlchemy database models."""

from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Date, ForeignKey
from sqlalchemy.orm import relationship

from database import Base
from config import TRIAL_DAYS


class User(Base):
    """User account model."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)

    # Stripe
    stripe_customer_id = Column(String, unique=True, nullable=True)

    # Subscription status
    subscription_status = Column(String, default="trial")  # trial, active, cancelled, expired
    subscription_id = Column(String, nullable=True)  # Stripe subscription ID
    subscription_end_date = Column(DateTime, nullable=True)

    # Trial
    trial_start_date = Column(DateTime, default=datetime.utcnow)
    trial_end_date = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=TRIAL_DAYS))

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Usage tracking
    usage = relationship("DailyUsage", back_populates="user")

    @property
    def is_trial(self) -> bool:
        return self.subscription_status == "trial"

    @property
    def is_active(self) -> bool:
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


class DailyUsage(Base):
    """Track daily AI response usage for trial users."""
    __tablename__ = "daily_usage"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    response_count = Column(Integer, default=0)

    user = relationship("User", back_populates="usage")
