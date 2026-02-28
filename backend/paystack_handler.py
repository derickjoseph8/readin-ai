"""
Paystack Payment Handler for ReadIn AI

Handles all Paystack payment operations including:
- Subscription creation
- Payment verification
- Webhook handling
- Customer management
"""

import hmac
import hashlib
import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from config import PAYSTACK_SECRET_KEY, PAYSTACK_PUBLIC_KEY, APP_URL
from models import User, Organization, PaymentHistory
from pricing_config import (
    Region, PlanType, get_pricing, calculate_billing,
    should_alert_sales, get_region_from_country,
    calculate_billing_with_enforcement, enforce_minimum_seats,
    has_trial_period, get_billing_start_date, calculate_proration,
    get_test_pricing, NO_TRIAL_PLANS
)


PAYSTACK_BASE_URL = "https://api.paystack.co"


class PaystackError(Exception):
    """Custom exception for Paystack errors."""
    pass


def _get_headers() -> Dict[str, str]:
    """Get headers for Paystack API requests."""
    return {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }


async def _make_request(
    method: str,
    endpoint: str,
    data: Optional[Dict] = None
) -> Dict[str, Any]:
    """Make request to Paystack API."""
    url = f"{PAYSTACK_BASE_URL}{endpoint}"

    async with httpx.AsyncClient() as client:
        if method == "GET":
            response = await client.get(url, headers=_get_headers())
        elif method == "POST":
            response = await client.post(url, headers=_get_headers(), json=data)
        else:
            raise ValueError(f"Unsupported method: {method}")

        result = response.json()

        if not result.get("status"):
            raise PaystackError(result.get("message", "Unknown Paystack error"))

        return result.get("data", {})


# =============================================================================
# CUSTOMER MANAGEMENT
# =============================================================================

async def create_customer(user: User, db: Session) -> str:
    """Create a Paystack customer for a user."""
    data = {
        "email": user.email,
        "first_name": user.full_name.split()[0] if user.full_name else "",
        "last_name": " ".join(user.full_name.split()[1:]) if user.full_name and len(user.full_name.split()) > 1 else "",
        "metadata": {
            "user_id": str(user.id),
        }
    }

    result = await _make_request("POST", "/customer", data)
    customer_code = result.get("customer_code")

    # Store customer code
    user.paystack_customer_code = customer_code
    db.commit()

    return customer_code


async def get_or_create_customer(user: User, db: Session) -> str:
    """Get existing customer or create new one."""
    if user.paystack_customer_code:
        return user.paystack_customer_code
    return await create_customer(user, db)


# =============================================================================
# SUBSCRIPTION MANAGEMENT
# =============================================================================

async def initialize_transaction(
    user: User,
    plan: PlanType,
    region: Region,
    is_annual: bool,
    seats: int,
    db: Session,
    success_url: Optional[str] = None,
    cancel_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Initialize a Paystack transaction for subscription.

    - Enforces minimum seats for billing
    - Applies test pricing for authorized test emails
    - Team/Starter/Enterprise: Billed instantly (no trial)
    - Individual: May have trial period

    Returns authorization URL for payment.
    """
    # Calculate billing with enforcement and test pricing
    billing = calculate_billing_with_enforcement(
        region=region,
        seats=seats,
        is_annual=is_annual,
        plan_override=plan,
        user_email=user.email,
    )

    # Use billable seats (enforced minimum)
    billable_seats = billing["billable_seats"]

    # Calculate amount in kobo/cents (Paystack uses smallest currency unit)
    if is_annual:
        amount = int(billing["total_annual"] * 100)
    else:
        amount = int(billing["total_monthly"] * 100)

    customer_code = await get_or_create_customer(user, db)

    # Determine if instant billing (no trial)
    instant_billing = plan in NO_TRIAL_PLANS
    billing_start = get_billing_start_date(plan)

    data = {
        "email": user.email,
        "amount": amount,
        "currency": "USD",
        "callback_url": success_url or f"{APP_URL}/dashboard/settings/billing?success=true",
        "metadata": {
            "user_id": str(user.id),
            "plan": plan.value,
            "region": region.value,
            "requested_seats": seats,
            "billable_seats": billable_seats,
            "is_annual": is_annual,
            "instant_billing": instant_billing,
            "billing_cycle_start": billing_start.isoformat(),
            "is_test_pricing": billing.get("is_test_pricing", False),
            "cancel_url": cancel_url or f"{APP_URL}/dashboard/settings/billing?cancelled=true",
        },
    }

    result = await _make_request("POST", "/transaction/initialize", data)

    return {
        "authorization_url": result.get("authorization_url"),
        "access_code": result.get("access_code"),
        "reference": result.get("reference"),
        "billing_details": {
            "plan": plan.value,
            "billable_seats": billable_seats,
            "amount": billing["total_monthly"] if not is_annual else billing["total_annual"],
            "currency": "USD",
            "instant_billing": instant_billing,
            "has_trial": billing.get("has_trial", False),
            "is_test_pricing": billing.get("is_test_pricing", False),
        },
    }


async def verify_transaction(reference: str) -> Dict[str, Any]:
    """Verify a Paystack transaction."""
    return await _make_request("GET", f"/transaction/verify/{reference}")


async def create_subscription(
    user: User,
    plan: PlanType,
    region: Region,
    is_annual: bool,
    seats: int,
    authorization_code: str,
    db: Session,
) -> Dict[str, Any]:
    """Create a recurring subscription."""
    pricing = get_pricing(region, plan)
    billing = calculate_billing(region, seats, is_annual)

    # Amount per billing cycle
    if is_annual:
        amount = int(billing["total_annual"] * 100)
        interval = "annually"
    else:
        amount = int(billing["total_monthly"] * 100)
        interval = "monthly"

    # Create plan if not exists (or use pre-created plan codes)
    plan_code = f"PLN_{region.value}_{plan.value}_{seats}seats_{'annual' if is_annual else 'monthly'}"

    # Create subscription
    data = {
        "customer": user.paystack_customer_code,
        "plan": plan_code,
        "authorization": authorization_code,
    }

    try:
        result = await _make_request("POST", "/subscription", data)

        # Update user subscription info
        user.subscription_id = result.get("subscription_code")
        user.subscription_status = "active"
        user.subscription_plan = plan.value
        user.subscription_seats = seats
        user.subscription_region = region.value
        user.subscription_is_annual = is_annual
        db.commit()

        return result
    except PaystackError:
        # If plan doesn't exist, create it first
        await _create_plan(plan_code, billing, is_annual)
        return await create_subscription(user, plan, region, is_annual, seats, authorization_code, db)


async def _create_plan(
    plan_code: str,
    billing: Dict[str, Any],
    is_annual: bool,
) -> Dict[str, Any]:
    """Create a Paystack plan."""
    if is_annual:
        amount = int(billing["total_annual"] * 100)
        interval = "annually"
    else:
        amount = int(billing["total_monthly"] * 100)
        interval = "monthly"

    data = {
        "name": f"ReadIn AI - {billing['plan'].title()} ({billing['seats']} seats)",
        "amount": amount,
        "interval": interval,
        "currency": "USD",
    }

    return await _make_request("POST", "/plan", data)


async def cancel_subscription(user: User, db: Session) -> Dict[str, Any]:
    """Cancel a user's subscription."""
    if not user.subscription_id:
        raise PaystackError("No active subscription")

    data = {
        "code": user.subscription_id,
        "token": user.paystack_customer_code,
    }

    result = await _make_request("POST", "/subscription/disable", data)

    user.subscription_status = "cancelled"
    db.commit()

    return result


async def add_seats_with_proration(
    user: User,
    new_total_seats: int,
    db: Session,
) -> Dict[str, Any]:
    """
    Add seats to an existing subscription with prorated billing.

    Charges immediately for the prorated amount of additional seats
    for the remaining days in the current billing cycle.
    """
    if not user.subscription_id:
        raise PaystackError("No active subscription")

    current_seats = user.subscription_seats or 1
    if new_total_seats <= current_seats:
        raise PaystackError("New seat count must be greater than current seats")

    # Get user's region and plan
    region = get_region_from_country(user.country_code or "US")
    plan = PlanType(user.subscription_plan) if user.subscription_plan else PlanType.STARTER
    is_annual = user.subscription_is_annual or False

    # Calculate days remaining in billing cycle
    if user.subscription_billing_cycle_start:
        cycle_start = user.subscription_billing_cycle_start
        if is_annual:
            next_billing = cycle_start.replace(year=cycle_start.year + 1)
            total_days = 365
        else:
            # Monthly: add 30 days
            next_billing = cycle_start + timedelta(days=30)
            total_days = 30

        days_remaining = (next_billing - datetime.utcnow()).days
        days_remaining = max(0, days_remaining)  # Don't go negative
    else:
        # Default to full cycle if no start date
        days_remaining = 30 if not is_annual else 365
        total_days = days_remaining

    # Calculate proration
    proration = calculate_proration(
        region=region,
        plan=plan,
        current_seats=current_seats,
        new_seats=new_total_seats,
        days_remaining_in_cycle=days_remaining,
        total_days_in_cycle=total_days,
        is_annual=is_annual,
    )

    if proration["prorated_amount"] <= 0:
        # Update seats without charge (end of cycle)
        user.subscription_seats = new_total_seats
        db.commit()
        return {
            "charged": False,
            "message": "Seats updated, will take effect next billing cycle",
            "new_seats": new_total_seats,
        }

    # Charge prorated amount immediately
    amount_in_cents = int(proration["prorated_amount"] * 100)

    if not user.paystack_authorization_code:
        raise PaystackError("No saved payment method for automatic charge")

    # Charge using saved authorization
    charge_data = {
        "authorization_code": user.paystack_authorization_code,
        "email": user.email,
        "amount": amount_in_cents,
        "currency": "USD",
        "metadata": {
            "user_id": str(user.id),
            "type": "seat_proration",
            "previous_seats": current_seats,
            "new_seats": new_total_seats,
            "additional_seats": proration["additional_seats"],
            "days_remaining": days_remaining,
        },
    }

    result = await _make_request("POST", "/transaction/charge_authorization", charge_data)

    # Update user's seat count
    user.subscription_seats = new_total_seats
    db.commit()

    # Log the prorated payment
    payment = PaymentHistory(
        user_id=user.id,
        paystack_reference=result.get("reference"),
        amount=proration["prorated_amount"],
        currency="USD",
        status="paid",
        description=f"Prorated charge: {proration['additional_seats']} additional seats for {days_remaining} days",
    )
    db.add(payment)
    db.commit()

    return {
        "charged": True,
        "prorated_amount": proration["prorated_amount"],
        "additional_seats": proration["additional_seats"],
        "new_total_seats": new_total_seats,
        "reference": result.get("reference"),
        "next_cycle_amount": proration["next_cycle_amount"],
    }


# =============================================================================
# WEBHOOK HANDLING
# =============================================================================

def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Verify Paystack webhook signature."""
    if not PAYSTACK_SECRET_KEY:
        return False

    expected = hmac.new(
        PAYSTACK_SECRET_KEY.encode(),
        payload,
        hashlib.sha512
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


async def handle_webhook_event(event: Dict[str, Any], db: Session) -> None:
    """Handle Paystack webhook events."""
    event_type = event.get("event")
    data = event.get("data", {})

    if event_type == "charge.success":
        await _handle_charge_success(data, db)

    elif event_type == "subscription.create":
        await _handle_subscription_created(data, db)

    elif event_type == "subscription.disable":
        await _handle_subscription_disabled(data, db)

    elif event_type == "invoice.create":
        await _handle_invoice_created(data, db)

    elif event_type == "invoice.payment_failed":
        await _handle_payment_failed(data, db)


async def _handle_charge_success(data: Dict[str, Any], db: Session) -> None:
    """Handle successful charge."""
    metadata = data.get("metadata", {})
    user_id = metadata.get("user_id")

    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            # Log payment
            payment = PaymentHistory(
                user_id=user.id,
                paystack_reference=data.get("reference"),
                amount=data.get("amount", 0) / 100,  # Convert from kobo
                currency=data.get("currency", "USD"),
                status="paid",
                description=f"Subscription payment - {metadata.get('plan', 'Premium')}",
            )
            db.add(payment)

            # Update subscription status
            user.subscription_status = "active"

            # Store authorization for future charges
            auth = data.get("authorization", {})
            if auth.get("reusable"):
                user.paystack_authorization_code = auth.get("authorization_code")

            db.commit()


async def _handle_subscription_created(data: Dict[str, Any], db: Session) -> None:
    """Handle subscription creation."""
    customer_code = data.get("customer", {}).get("customer_code")
    user = db.query(User).filter(User.paystack_customer_code == customer_code).first()

    if user:
        user.subscription_id = data.get("subscription_code")
        user.subscription_status = "active"
        db.commit()


async def _handle_subscription_disabled(data: Dict[str, Any], db: Session) -> None:
    """Handle subscription cancellation."""
    subscription_code = data.get("subscription_code")
    user = db.query(User).filter(User.subscription_id == subscription_code).first()

    if user:
        user.subscription_status = "cancelled"
        db.commit()


async def _handle_invoice_created(data: Dict[str, Any], db: Session) -> None:
    """Handle invoice creation (upcoming payment)."""
    pass  # Can be used to send payment reminders


async def _handle_payment_failed(data: Dict[str, Any], db: Session) -> None:
    """Handle failed payment."""
    subscription = data.get("subscription", {})
    subscription_code = subscription.get("subscription_code")

    user = db.query(User).filter(User.subscription_id == subscription_code).first()

    if user:
        # Log failed payment
        payment = PaymentHistory(
            user_id=user.id,
            paystack_reference=data.get("reference"),
            amount=data.get("amount", 0) / 100,
            currency="USD",
            status="failed",
            description="Subscription payment failed",
        )
        db.add(payment)

        # Update status if multiple failures
        user.subscription_status = "past_due"
        db.commit()


# =============================================================================
# ENTERPRISE ALERTS
# =============================================================================

async def check_and_alert_enterprise(
    organization_id: str,
    current_seats: int,
    new_seats: int,
    db: Session,
) -> Optional[Dict[str, Any]]:
    """
    Check if organization is reaching enterprise threshold and alert sales.

    Returns alert details if threshold crossed.
    """
    if should_alert_sales(current_seats, new_seats):
        org = db.query(Organization).filter(Organization.id == organization_id).first()

        if org:
            # Get region for pricing quote
            admin = db.query(User).filter(User.id == org.owner_id).first()
            region = get_region_from_country(admin.country_code or "US") if admin else Region.WESTERN

            from pricing_config import get_enterprise_quote
            quote = get_enterprise_quote(region, new_seats)

            # TODO: Send email to sales team
            # await send_enterprise_alert_email(org, quote)

            return {
                "alert": "enterprise_threshold",
                "organization": org.name,
                "organization_id": str(org.id),
                "current_seats": current_seats,
                "new_seats": new_seats,
                "quote": quote,
            }

    return None
