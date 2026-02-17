"""
Payment and subscription management routes.

Provides API endpoints for:
- Creating checkout sessions
- Managing subscriptions
- Billing portal access
- Webhook handling
- Invoice history
"""

import stripe
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from auth import get_current_user
from models import User, PaymentHistory
from config import (
    STRIPE_SECRET_KEY,
    STRIPE_WEBHOOK_SECRET,
    STRIPE_PRICE_MONTHLY,
    APP_URL,
)
from stripe_handler import (
    create_checkout_session,
    create_billing_portal_session,
    handle_checkout_completed,
    handle_subscription_updated,
    handle_subscription_deleted,
    create_customer,
)

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])

# Initialize Stripe
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


# =============================================================================
# SCHEMAS
# =============================================================================

class CheckoutRequest(BaseModel):
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class CheckoutResponse(BaseModel):
    checkout_url: str


class PortalResponse(BaseModel):
    portal_url: str


class SubscriptionStatus(BaseModel):
    status: str
    plan: Optional[str] = None
    current_period_end: Optional[str] = None
    cancel_at_period_end: bool = False
    trial_ends_at: Optional[str] = None


class Invoice(BaseModel):
    id: str
    number: Optional[str]
    amount_due: int
    amount_paid: int
    currency: str
    status: str
    created: str
    invoice_pdf: Optional[str]
    hosted_invoice_url: Optional[str]


class PaymentMethod(BaseModel):
    id: str
    type: str
    card_brand: Optional[str]
    card_last4: Optional[str]
    card_exp_month: Optional[int]
    card_exp_year: Optional[int]
    is_default: bool


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _check_stripe_configured():
    """Check if Stripe is properly configured."""
    if not STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=503,
            detail="Payment system not configured"
        )


# =============================================================================
# CHECKOUT & SUBSCRIPTION ENDPOINTS
# =============================================================================

@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout(
    request: CheckoutRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a Stripe checkout session for subscription."""
    _check_stripe_configured()

    if user.subscription_status == "active":
        raise HTTPException(
            status_code=400,
            detail="You already have an active subscription"
        )

    success_url = request.success_url or f"{APP_URL}/dashboard/settings/billing?success=true"
    cancel_url = request.cancel_url or f"{APP_URL}/dashboard/settings/billing?cancelled=true"

    checkout_url = create_checkout_session(user, db, success_url, cancel_url)

    return CheckoutResponse(checkout_url=checkout_url)


@router.post("/portal", response_model=PortalResponse)
def get_billing_portal(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a link to the Stripe billing portal."""
    _check_stripe_configured()

    if not user.stripe_customer_id:
        raise HTTPException(
            status_code=400,
            detail="No billing account found"
        )

    return_url = f"{APP_URL}/dashboard/settings/billing"
    portal_url = create_billing_portal_session(user, return_url)

    return PortalResponse(portal_url=portal_url)


@router.get("/subscription", response_model=SubscriptionStatus)
def get_subscription_status(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current subscription status."""
    status = SubscriptionStatus(
        status=user.subscription_status or "none",
        cancel_at_period_end=False,
    )

    # Get trial info
    if user.trial_ends_at:
        status.trial_ends_at = user.trial_ends_at.isoformat()

    # Get subscription details from Stripe if active
    if user.subscription_id and STRIPE_SECRET_KEY:
        try:
            subscription = stripe.Subscription.retrieve(user.subscription_id)
            status.status = subscription.status
            status.current_period_end = datetime.fromtimestamp(
                subscription.current_period_end
            ).isoformat()
            status.cancel_at_period_end = subscription.cancel_at_period_end
            status.plan = "premium"
        except stripe.error.StripeError:
            pass

    return status


@router.post("/subscription/cancel")
def cancel_subscription(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel subscription at period end."""
    _check_stripe_configured()

    if not user.subscription_id:
        raise HTTPException(
            status_code=400,
            detail="No active subscription found"
        )

    try:
        subscription = stripe.Subscription.modify(
            user.subscription_id,
            cancel_at_period_end=True
        )

        return {
            "message": "Subscription will be cancelled at period end",
            "cancel_at": datetime.fromtimestamp(subscription.current_period_end).isoformat()
        }
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/subscription/reactivate")
def reactivate_subscription(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reactivate a cancelled subscription."""
    _check_stripe_configured()

    if not user.subscription_id:
        raise HTTPException(
            status_code=400,
            detail="No subscription found"
        )

    try:
        subscription = stripe.Subscription.modify(
            user.subscription_id,
            cancel_at_period_end=False
        )

        return {
            "message": "Subscription reactivated",
            "status": subscription.status
        }
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# INVOICE ENDPOINTS
# =============================================================================

@router.get("/invoices", response_model=List[Invoice])
def get_invoices(
    limit: int = 10,
    user: User = Depends(get_current_user),
):
    """Get user's invoice history."""
    _check_stripe_configured()

    if not user.stripe_customer_id:
        return []

    try:
        invoices = stripe.Invoice.list(
            customer=user.stripe_customer_id,
            limit=min(limit, 100)
        )

        return [
            Invoice(
                id=inv.id,
                number=inv.number,
                amount_due=inv.amount_due,
                amount_paid=inv.amount_paid,
                currency=inv.currency,
                status=inv.status,
                created=datetime.fromtimestamp(inv.created).isoformat(),
                invoice_pdf=inv.invoice_pdf,
                hosted_invoice_url=inv.hosted_invoice_url,
            )
            for inv in invoices.data
        ]
    except stripe.error.StripeError:
        return []


@router.get("/invoices/{invoice_id}")
def get_invoice(
    invoice_id: str,
    user: User = Depends(get_current_user),
):
    """Get a specific invoice."""
    _check_stripe_configured()

    try:
        invoice = stripe.Invoice.retrieve(invoice_id)

        # Verify invoice belongs to user
        if invoice.customer != user.stripe_customer_id:
            raise HTTPException(status_code=404, detail="Invoice not found")

        return Invoice(
            id=invoice.id,
            number=invoice.number,
            amount_due=invoice.amount_due,
            amount_paid=invoice.amount_paid,
            currency=invoice.currency,
            status=invoice.status,
            created=datetime.fromtimestamp(invoice.created).isoformat(),
            invoice_pdf=invoice.invoice_pdf,
            hosted_invoice_url=invoice.hosted_invoice_url,
        )
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# PAYMENT METHOD ENDPOINTS
# =============================================================================

@router.get("/payment-methods", response_model=List[PaymentMethod])
def get_payment_methods(
    user: User = Depends(get_current_user),
):
    """Get user's saved payment methods."""
    _check_stripe_configured()

    if not user.stripe_customer_id:
        return []

    try:
        methods = stripe.PaymentMethod.list(
            customer=user.stripe_customer_id,
            type="card"
        )

        # Get default payment method
        customer = stripe.Customer.retrieve(user.stripe_customer_id)
        default_method = customer.invoice_settings.default_payment_method

        return [
            PaymentMethod(
                id=pm.id,
                type=pm.type,
                card_brand=pm.card.brand if pm.card else None,
                card_last4=pm.card.last4 if pm.card else None,
                card_exp_month=pm.card.exp_month if pm.card else None,
                card_exp_year=pm.card.exp_year if pm.card else None,
                is_default=pm.id == default_method,
            )
            for pm in methods.data
        ]
    except stripe.error.StripeError:
        return []


@router.post("/payment-methods/{method_id}/default")
def set_default_payment_method(
    method_id: str,
    user: User = Depends(get_current_user),
):
    """Set a payment method as default."""
    _check_stripe_configured()

    if not user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No billing account found")

    try:
        stripe.Customer.modify(
            user.stripe_customer_id,
            invoice_settings={"default_payment_method": method_id}
        )

        return {"message": "Default payment method updated"}
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/payment-methods/{method_id}")
def delete_payment_method(
    method_id: str,
    user: User = Depends(get_current_user),
):
    """Delete a payment method."""
    _check_stripe_configured()

    try:
        # Verify method belongs to user
        method = stripe.PaymentMethod.retrieve(method_id)
        if method.customer != user.stripe_customer_id:
            raise HTTPException(status_code=404, detail="Payment method not found")

        stripe.PaymentMethod.detach(method_id)

        return {"message": "Payment method removed"}
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# WEBHOOK ENDPOINT
# =============================================================================

@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
):
    """Handle Stripe webhook events."""
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Webhook not configured")

    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle different event types
    event_type = event["type"]
    event_data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        handle_checkout_completed(event_data, db)

    elif event_type == "customer.subscription.updated":
        handle_subscription_updated(event_data, db)

    elif event_type == "customer.subscription.deleted":
        handle_subscription_deleted(event_data, db)

    elif event_type == "invoice.paid":
        # Log successful payment
        _log_payment(db, event_data, "paid")

    elif event_type == "invoice.payment_failed":
        # Log failed payment
        _log_payment(db, event_data, "failed")

    return {"status": "success"}


def _log_payment(db: Session, invoice: dict, status: str):
    """Log a payment event."""
    customer_id = invoice.get("customer")
    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()

    if user:
        payment = PaymentHistory(
            user_id=user.id,
            stripe_invoice_id=invoice.get("id"),
            amount=invoice.get("amount_paid", 0),
            currency=invoice.get("currency", "usd"),
            status=status,
            description=f"Subscription payment - {invoice.get('number', 'N/A')}",
        )
        db.add(payment)
        db.commit()


# =============================================================================
# PRICING INFO ENDPOINT
# =============================================================================

@router.get("/pricing")
def get_pricing():
    """Get current pricing information."""
    return {
        "plans": [
            {
                "id": "free",
                "name": "Free Trial",
                "price": 0,
                "currency": "usd",
                "interval": None,
                "features": [
                    "7-day free trial",
                    f"Up to 10 AI responses per day",
                    "Basic meeting summaries",
                    "Email support",
                ],
            },
            {
                "id": "premium",
                "name": "Premium",
                "price": 1000,  # $10.00 in cents
                "currency": "usd",
                "interval": "month",
                "features": [
                    "Unlimited AI responses",
                    "Advanced meeting summaries",
                    "Action item tracking",
                    "Calendar integration",
                    "Team collaboration",
                    "Priority support",
                    "Export reports (PDF/CSV)",
                ],
            },
        ]
    }
