"""Pydantic schemas for request/response validation."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


# Auth schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None


# User schemas
class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    subscription_status: str
    trial_days_remaining: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserStatus(BaseModel):
    """Status check response for desktop app."""
    is_active: bool
    subscription_status: str  # trial, active, cancelled, expired
    trial_days_remaining: int
    daily_usage: int
    daily_limit: Optional[int]  # None if unlimited (paid)
    can_use: bool  # Whether user can make another request


# Subscription schemas
class CreateCheckoutSession(BaseModel):
    price_id: Optional[str] = None


class CheckoutSessionResponse(BaseModel):
    checkout_url: str


class SubscriptionResponse(BaseModel):
    status: str
    current_period_end: Optional[datetime]
    cancel_at_period_end: bool


# Usage schemas
class UsageIncrement(BaseModel):
    """Increment usage count."""
    pass


class UsageResponse(BaseModel):
    date: str
    count: int
    limit: Optional[int]
    remaining: Optional[int]
