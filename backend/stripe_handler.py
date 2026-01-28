"""Stripe payment and subscription handling."""

from datetime import datetime
from typing import Optional

import stripe
from fastapi import HTTPException
from sqlalchemy.orm import Session

from config import STRIPE_SECRET_KEY, STRIPE_PRICE_MONTHLY
from models import User

# Initialize Stripe
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


def _check_stripe_configured():
    """Verify Stripe is configured before making API calls."""
    if not STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=503,
            detail="Payment system not configured. Please contact support."
        )
    if not STRIPE_PRICE_MONTHLY:
        raise HTTPException(
            status_code=503,
            detail="Subscription pricing not configured. Please contact support."
        )


def create_customer(user: User) -> str:
    """Create a Stripe customer for a user."""
    if user.stripe_customer_id:
        return user.stripe_customer_id

    customer = stripe.Customer.create(
        email=user.email,
        name=user.full_name,
        metadata={"user_id": str(user.id)}
    )
    return customer.id


def create_checkout_session(user: User, db: Session, success_url: str, cancel_url: str) -> str:
    """Create a Stripe checkout session for subscription."""
    _check_stripe_configured()

    # Ensure user has a Stripe customer ID
    if not user.stripe_customer_id:
        customer_id = create_customer(user)
        user.stripe_customer_id = customer_id
        db.commit()

    # Create checkout session
    session = stripe.checkout.Session.create(
        customer=user.stripe_customer_id,
        payment_method_types=["card"],
        line_items=[{
            "price": STRIPE_PRICE_MONTHLY,
            "quantity": 1,
        }],
        mode="subscription",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"user_id": str(user.id)},
        subscription_data={
            "metadata": {"user_id": str(user.id)}
        }
    )
    return session.url


def create_billing_portal_session(user: User, return_url: str) -> str:
    """Create a Stripe billing portal session for managing subscription."""
    _check_stripe_configured()

    if not user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No subscription found")

    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=return_url,
    )
    return session.url


def handle_checkout_completed(session: dict, db: Session):
    """Handle successful checkout - activate subscription."""
    user_id = session.get("metadata", {}).get("user_id")
    if not user_id:
        return

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        return

    subscription_id = session.get("subscription")
    if subscription_id:
        # Get subscription details
        subscription = stripe.Subscription.retrieve(subscription_id)
        user.subscription_status = "active"
        user.subscription_id = subscription_id
        user.subscription_end_date = datetime.fromtimestamp(subscription.current_period_end)
        db.commit()


def handle_subscription_updated(subscription: dict, db: Session):
    """Handle subscription updates (renewal, cancellation, etc.)."""
    user_id = subscription.get("metadata", {}).get("user_id")
    if not user_id:
        # Try to find by customer ID
        customer_id = subscription.get("customer")
        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
    else:
        user = db.query(User).filter(User.id == int(user_id)).first()

    if not user:
        return

    status = subscription.get("status")
    if status == "active":
        user.subscription_status = "active"
        user.subscription_end_date = datetime.fromtimestamp(subscription["current_period_end"])
    elif status in ("canceled", "unpaid", "past_due"):
        user.subscription_status = "cancelled"
    elif status == "incomplete_expired":
        user.subscription_status = "expired"

    user.subscription_id = subscription.get("id")
    db.commit()


def handle_subscription_deleted(subscription: dict, db: Session):
    """Handle subscription cancellation/deletion."""
    customer_id = subscription.get("customer")
    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()

    if user:
        user.subscription_status = "expired"
        user.subscription_id = None
        db.commit()
