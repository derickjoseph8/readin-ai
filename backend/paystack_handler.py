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
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from config import PAYSTACK_SECRET_KEY, PAYSTACK_PUBLIC_KEY, APP_URL
from models import User, Organization, PaymentHistory
from pricing_config import (
    Region, PlanType, get_pricing, calculate_billing,
    should_alert_sales, get_region_from_country
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

    Returns authorization URL for payment.
    """
    pricing = get_pricing(region, plan)
    billing = calculate_billing(region, seats, is_annual)

    # Calculate amount in kobo/cents (Paystack uses smallest currency unit)
    if is_annual:
        amount = int(billing["total_annual"] * 100)
    else:
        amount = int(billing["total_monthly"] * 100)

    customer_code = await get_or_create_customer(user, db)

    data = {
        "email": user.email,
        "amount": amount,
        "currency": "USD",
        "callback_url": success_url or f"{APP_URL}/dashboard/settings/billing?success=true",
        "metadata": {
            "user_id": str(user.id),
            "plan": plan.value,
            "region": region.value,
            "seats": seats,
            "is_annual": is_annual,
            "cancel_url": cancel_url or f"{APP_URL}/dashboard/settings/billing?cancelled=true",
        },
    }

    result = await _make_request("POST", "/transaction/initialize", data)

    return {
        "authorization_url": result.get("authorization_url"),
        "access_code": result.get("access_code"),
        "reference": result.get("reference"),
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
