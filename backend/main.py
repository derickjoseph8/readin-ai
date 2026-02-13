"""ReadIn AI Backend API - Authentication, Subscriptions, Usage Tracking, ML Intelligence."""

import os
from datetime import date, datetime
from typing import Optional

import stripe
from fastapi import FastAPI, Depends, HTTPException, status, Request, Header
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session

from config import (
    STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_PRICE_MONTHLY,
    TRIAL_DAILY_LIMIT, APP_NAME, API_VERSION, IS_PRODUCTION, IS_DEVELOPMENT,
    CORS_ALLOWED_ORIGINS, SENTRY_DSN, ENVIRONMENT
)
from database import get_db, init_db
from models import User, DailyUsage, Profession, UserLearningProfile
from schemas import (
    UserCreate, UserLogin, Token, UserResponse, UserStatus, UserUpdate,
    UserEmailPreferences, CreateCheckoutSession, CheckoutSessionResponse, UsageResponse,
    PasswordChangeRequest
)
from auth import (
    hash_password, verify_password, create_access_token, get_current_user
)
from stripe_handler import (
    create_checkout_session, create_billing_portal_session,
    handle_checkout_completed, handle_subscription_updated,
    handle_subscription_deleted
)

# Import route modules
from routes import (
    professions_router, organizations_router, meetings_router,
    conversations_router, tasks_router, briefings_router, interviews_router,
    gdpr_router, metrics_router, analytics_router, calendar_router,
    sso_router, api_keys_router, webhooks_router, white_label_router
)
from routes.contact import router as contact_router

# Import scheduler
from services.scheduler import start_scheduler, stop_scheduler

# Import middleware
from middleware.rate_limiter import limiter, rate_limit_login, rate_limit_register
from middleware.security import SecurityHeadersMiddleware
from middleware.request_context import RequestContextMiddleware, get_request_id
from middleware.error_handler import ErrorHandlerMiddleware, create_error_response, ErrorTypes

# Initialize Sentry for error tracking (production)
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            environment=ENVIRONMENT,
            traces_sample_rate=0.1 if IS_PRODUCTION else 1.0,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
            ],
        )
        print("[OK] Sentry error tracking initialized")
    except ImportError:
        print("[WARNING] sentry-sdk not installed, skipping Sentry initialization")

# Initialize FastAPI
app = FastAPI(
    title=f"{APP_NAME} API",
    version=API_VERSION,
    description="Backend API for ReadIn AI - Meeting Intelligence Platform with ML-powered learning",
    docs_url="/docs" if IS_DEVELOPMENT else None,  # Disable docs in production
    redoc_url="/redoc" if IS_DEVELOPMENT else None,
    openapi_url="/openapi.json" if IS_DEVELOPMENT else None,
)

# Initialize rate limiter state
app.state.limiter = limiter

# Initialize Stripe
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY
else:
    print("[WARNING] STRIPE_SECRET_KEY not configured. Payment features disabled.")

# =============================================================================
# MIDDLEWARE STACK (order matters - last added runs first)
# =============================================================================

# 1. Error handler (outermost - catches all errors)
app.add_middleware(ErrorHandlerMiddleware)

# 2. Request context (request ID, timing)
app.add_middleware(RequestContextMiddleware)

# 3. Security headers
app.add_middleware(SecurityHeadersMiddleware)

# 4. CORS - configured based on environment
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS if CORS_ALLOWED_ORIGINS else ["*"],
    allow_credentials=True if CORS_ALLOWED_ORIGINS else False,  # Only allow credentials with explicit origins
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Request-ID",
        "X-Requested-With",
        "Accept",
        "Origin",
    ],
    expose_headers=["X-Request-ID", "X-Response-Time"],
    max_age=600,  # Cache preflight for 10 minutes
)

# =============================================================================
# EXCEPTION HANDLERS
# =============================================================================

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded errors."""
    return JSONResponse(
        status_code=429,
        content={
            "error": True,
            "type": ErrorTypes.RATE_LIMIT,
            "message": "Too many requests. Please slow down and try again.",
            "retry_after": exc.detail,
            "request_id": get_request_id(),
        },
        headers={"Retry-After": str(60)},  # Retry after 60 seconds
    )

# =============================================================================
# ROUTE MODULES
# =============================================================================

# Include route modules with /api/v1 prefix for versioning
API_V1_PREFIX = "/api/v1"

app.include_router(professions_router, prefix=API_V1_PREFIX)
app.include_router(organizations_router, prefix=API_V1_PREFIX)
app.include_router(meetings_router, prefix=API_V1_PREFIX)
app.include_router(conversations_router, prefix=API_V1_PREFIX)
app.include_router(tasks_router, prefix=API_V1_PREFIX)
app.include_router(briefings_router, prefix=API_V1_PREFIX)
app.include_router(interviews_router, prefix=API_V1_PREFIX)
app.include_router(gdpr_router, prefix=API_V1_PREFIX)
app.include_router(metrics_router, prefix=API_V1_PREFIX)
app.include_router(analytics_router)  # Already has /api/v1 prefix
app.include_router(calendar_router, prefix=API_V1_PREFIX)
app.include_router(sso_router, prefix=API_V1_PREFIX)
app.include_router(api_keys_router, prefix=API_V1_PREFIX)
app.include_router(webhooks_router, prefix=API_V1_PREFIX)
app.include_router(white_label_router, prefix=API_V1_PREFIX)
app.include_router(contact_router)

# Also include at root for backward compatibility (deprecated)
app.include_router(professions_router, tags=["Deprecated - Use /api/v1"])
app.include_router(organizations_router, tags=["Deprecated - Use /api/v1"])
app.include_router(meetings_router, tags=["Deprecated - Use /api/v1"])
app.include_router(conversations_router, tags=["Deprecated - Use /api/v1"])
app.include_router(tasks_router, tags=["Deprecated - Use /api/v1"])
app.include_router(briefings_router, tags=["Deprecated - Use /api/v1"])
app.include_router(interviews_router, tags=["Deprecated - Use /api/v1"])


@app.on_event("startup")
def startup():
    """Initialize database and verify configuration on startup."""
    print()
    print("=" * 60)
    print(f"  {APP_NAME} Backend v{API_VERSION}")
    print(f"  Environment: {ENVIRONMENT}")
    print("=" * 60)

    # Initialize database
    try:
        init_db()
        print("  [OK] Database connected")
    except Exception as e:
        print(f"  [ERROR] Database connection failed: {e}")
        raise

    # Verify Stripe configuration
    if STRIPE_SECRET_KEY:
        try:
            stripe.Account.retrieve()
            print("  [OK] Stripe configured")
        except stripe.error.AuthenticationError:
            print("  [WARNING] Invalid Stripe API key")
    else:
        print("  [WARNING] Stripe not configured")

    if STRIPE_WEBHOOK_SECRET:
        print("  [OK] Stripe webhook secret configured")
    else:
        print("  [WARNING] Stripe webhook secret not configured")

    if STRIPE_PRICE_MONTHLY:
        print(f"  [OK] Stripe price ID: {STRIPE_PRICE_MONTHLY[:20]}...")
    else:
        print("  [WARNING] Stripe price ID not configured")

    # Start background scheduler
    try:
        start_scheduler()
        print("  [OK] Background scheduler started")
    except Exception as e:
        print(f"  [WARNING] Scheduler failed to start: {e}")

    # Security status
    print()
    print("  Security Configuration:")
    print(f"    CORS Origins: {len(CORS_ALLOWED_ORIGINS)} configured" if CORS_ALLOWED_ORIGINS else "    CORS Origins: Open (dev mode)")
    print(f"    Rate Limiting: Enabled")
    print(f"    API Docs: {'Disabled' if IS_PRODUCTION else 'http://localhost:8000/docs'}")
    if SENTRY_DSN:
        print("    Error Tracking: Sentry enabled")

    print()
    print(f"  Trial: {TRIAL_DAILY_LIMIT} responses/day for 14 days")
    print("  Premium: $29.99/month - Unlimited responses")
    print("=" * 60)
    print()


@app.on_event("shutdown")
def shutdown():
    """Clean up resources on shutdown."""
    print("Shutting down...")
    try:
        stop_scheduler()
        print("  [OK] Scheduler stopped")
    except Exception as e:
        print(f"  [WARNING] Error stopping scheduler: {e}")


# ============== Auth Endpoints ==============

@app.post("/auth/register", response_model=Token)
@app.post("/api/v1/auth/register", response_model=Token)
@limiter.limit("3/minute")  # Strict rate limit on registration
def register(request: Request, user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user.

    IMPORTANT: profession_id is required for personalized AI responses.
    ML will first use stored knowledge for the profession,
    then learn the user's personal patterns over time.

    Rate limited to 3 registrations per minute per IP.
    """
    # Check if email exists
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Validate profession if provided
    profession = None
    if user_data.profession_id:
        profession = db.query(Profession).filter(
            Profession.id == user_data.profession_id,
            Profession.is_active == True
        ).first()
        if not profession:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid profession selected"
            )

    # Create user
    user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name,
        profession_id=user_data.profession_id,
        specialization=user_data.specialization,
        preferred_language=user_data.preferred_language or "en",
        subscription_status="trial"
    )
    db.add(user)
    db.flush()

    # Create empty learning profile for ML to populate
    learning_profile = UserLearningProfile(user_id=user.id)
    db.add(learning_profile)

    db.commit()
    db.refresh(user)

    # Return token
    token = create_access_token(user.id)
    return Token(access_token=token)


@app.post("/auth/login", response_model=Token)
@app.post("/api/v1/auth/login", response_model=Token)
@limiter.limit("5/minute")  # Strict rate limit to prevent brute force
def login(request: Request, credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Login and get access token.

    Rate limited to 5 attempts per minute per IP to prevent brute force attacks.
    """
    user = db.query(User).filter(User.email == credentials.email).first()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    token = create_access_token(user.id)
    return Token(access_token=token)


@app.post("/api/v1/auth/change-password")
@limiter.limit("3/minute")
def change_password(
    request: Request,
    data: PasswordChangeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change user password.

    Requires current password verification.
    Rate limited to 3 attempts per minute.
    """
    # Verify current password
    if not verify_password(data.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Update password (schema already validates new_password)
    user.hashed_password = hash_password(data.new_password)
    db.commit()

    return {"message": "Password changed successfully"}


# ============== Language Endpoints ==============

@app.get("/api/v1/languages")
def get_supported_languages():
    """Get list of supported languages for AI responses."""
    from services.language_service import get_supported_languages
    languages = get_supported_languages()
    return {
        "languages": [
            {
                "code": code,
                "name": info["name"],
                "native_name": info["native_name"]
            }
            for code, info in languages.items()
        ],
        "default": "en"
    }


# ============== User Endpoints ==============

@app.get("/user/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get current user info with profession and organization details."""
    profession_name = user.profession.name if user.profession else None
    organization_name = user.organization.name if user.organization else None

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        profession_id=user.profession_id,
        profession_name=profession_name,
        specialization=user.specialization,
        organization_id=user.organization_id,
        organization_name=organization_name,
        role_in_org=user.role_in_org,
        subscription_status=user.subscription_status,
        trial_days_remaining=user.trial_days_remaining,
        is_active=user.is_active,
        email_notifications_enabled=user.email_notifications_enabled,
        email_summary_enabled=user.email_summary_enabled,
        email_reminders_enabled=user.email_reminders_enabled,
        preferred_language=user.preferred_language or "en",
        created_at=user.created_at
    )


@app.patch("/user/me", response_model=UserResponse)
def update_me(
    data: UserUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user profile."""
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.profession_id is not None:
        # Validate profession
        profession = db.query(Profession).filter(
            Profession.id == data.profession_id,
            Profession.is_active == True
        ).first()
        if not profession:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid profession"
            )
        user.profession_id = data.profession_id
    if data.specialization is not None:
        user.specialization = data.specialization
    if data.years_experience is not None:
        user.years_experience = data.years_experience
    if data.preferred_language is not None:
        user.preferred_language = data.preferred_language

    db.commit()
    db.refresh(user)

    profession_name = user.profession.name if user.profession else None
    organization_name = user.organization.name if user.organization else None

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        profession_id=user.profession_id,
        profession_name=profession_name,
        specialization=user.specialization,
        organization_id=user.organization_id,
        organization_name=organization_name,
        role_in_org=user.role_in_org,
        subscription_status=user.subscription_status,
        trial_days_remaining=user.trial_days_remaining,
        is_active=user.is_active,
        email_notifications_enabled=user.email_notifications_enabled,
        email_summary_enabled=user.email_summary_enabled,
        email_reminders_enabled=user.email_reminders_enabled,
        preferred_language=user.preferred_language or "en",
        created_at=user.created_at
    )


@app.patch("/user/me/email-preferences")
def update_email_preferences(
    data: UserEmailPreferences,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update email notification preferences."""
    if data.email_notifications_enabled is not None:
        user.email_notifications_enabled = data.email_notifications_enabled
    if data.email_summary_enabled is not None:
        user.email_summary_enabled = data.email_summary_enabled
    if data.email_reminders_enabled is not None:
        user.email_reminders_enabled = data.email_reminders_enabled

    db.commit()

    return {
        "email_notifications_enabled": user.email_notifications_enabled,
        "email_summary_enabled": user.email_summary_enabled,
        "email_reminders_enabled": user.email_reminders_enabled
    }


@app.get("/user/status", response_model=UserStatus)
def get_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get user status for desktop app - subscription, usage, and context info."""
    today = date.today()

    # Get today's usage
    usage = db.query(DailyUsage).filter(
        DailyUsage.user_id == user.id,
        DailyUsage.date == today
    ).first()

    daily_count = usage.response_count if usage else 0

    # Determine limits
    if user.subscription_status == "active":
        daily_limit = None  # Unlimited
        can_use = True
    elif user.is_trial:
        daily_limit = TRIAL_DAILY_LIMIT
        can_use = daily_count < TRIAL_DAILY_LIMIT
    else:
        daily_limit = 0
        can_use = False

    profession_name = user.profession.name if user.profession else None
    organization_name = user.organization.name if user.organization else None

    return UserStatus(
        is_active=user.is_active,
        subscription_status=user.subscription_status,
        trial_days_remaining=user.trial_days_remaining,
        daily_usage=daily_count,
        daily_limit=daily_limit,
        can_use=can_use,
        profession_name=profession_name,
        organization_name=organization_name
    )


# ============== Usage Tracking ==============

@app.post("/usage/increment", response_model=UsageResponse)
def increment_usage(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Increment daily usage count. Called by desktop app after each AI response."""
    today = date.today()

    # Get or create today's usage record
    usage = db.query(DailyUsage).filter(
        DailyUsage.user_id == user.id,
        DailyUsage.date == today
    ).first()

    if not usage:
        usage = DailyUsage(user_id=user.id, date=today, response_count=0)
        db.add(usage)

    # Check limit for trial users
    if user.subscription_status != "active" and user.is_trial:
        if usage.response_count >= TRIAL_DAILY_LIMIT:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Daily limit of {TRIAL_DAILY_LIMIT} responses reached. Upgrade for unlimited access."
            )

    # Increment
    usage.response_count += 1
    db.commit()

    # Calculate remaining
    if user.subscription_status == "active":
        limit = None
        remaining = None
    else:
        limit = TRIAL_DAILY_LIMIT
        remaining = max(0, TRIAL_DAILY_LIMIT - usage.response_count)

    return UsageResponse(
        date=str(today),
        count=usage.response_count,
        limit=limit,
        remaining=remaining
    )


# ============== Subscription Endpoints ==============

@app.post("/subscription/create-checkout", response_model=CheckoutSessionResponse)
def create_checkout(
    data: CreateCheckoutSession,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create Stripe checkout session for subscription."""
    price_id = data.price_id or STRIPE_PRICE_MONTHLY

    checkout_url = create_checkout_session(
        user=user,
        db=db,
        success_url="https://www.getreadin.us/success?session_id={CHECKOUT_SESSION_ID}",
        cancel_url="https://www.getreadin.us/pricing"
    )

    return CheckoutSessionResponse(checkout_url=checkout_url)


@app.post("/subscription/manage")
def manage_subscription(user: User = Depends(get_current_user)):
    """Get Stripe billing portal URL to manage subscription."""
    portal_url = create_billing_portal_session(
        user=user,
        return_url="https://www.getreadin.us/account"
    )
    return {"portal_url": portal_url}


@app.get("/subscription/status")
def subscription_status(user: User = Depends(get_current_user)):
    """Get current subscription status."""
    return {
        "status": user.subscription_status,
        "subscription_id": user.subscription_id,
        "end_date": user.subscription_end_date.isoformat() if user.subscription_end_date else None,
        "is_active": user.is_active
    }


# ============== Stripe Webhooks ==============

@app.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature"),
    db: Session = Depends(get_db)
):
    """Handle Stripe webhook events."""
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle events
    if event["type"] == "checkout.session.completed":
        handle_checkout_completed(event["data"]["object"], db)

    elif event["type"] == "customer.subscription.updated":
        handle_subscription_updated(event["data"]["object"], db)

    elif event["type"] == "customer.subscription.deleted":
        handle_subscription_deleted(event["data"]["object"], db)

    return {"status": "ok"}


# ============== Prometheus Metrics ==============

@app.get("/metrics/prometheus")
def root_prometheus_metrics(db: Session = Depends(get_db)):
    """
    Prometheus metrics endpoint at root level.
    Returns metrics in Prometheus text format for scraping.
    """
    from fastapi.responses import Response
    from middleware.logging_middleware import (
        get_prometheus_metrics,
        get_prometheus_content_type,
        set_active_users,
    )
    from sqlalchemy import func

    # Update active users gauge
    try:
        active_user_count = db.query(func.count(User.id)).filter(
            User.subscription_status.in_(["trial", "active"])
        ).scalar() or 0
        set_active_users(active_user_count)
    except Exception:
        pass

    return Response(
        content=get_prometheus_metrics(),
        media_type=get_prometheus_content_type()
    )


# ============== Root Endpoint ==============

@app.get("/")
def root():
    """Root endpoint - API information."""
    return {
        "app": APP_NAME,
        "version": API_VERSION,
        "docs": "/docs",
        "health": "/health",
        "api": "/api/v1"
    }


# ============== Health Check ==============

@app.get("/health")
@app.get("/api/v1/health")
def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint with detailed status.

    Returns status of all system components:
    - Database connectivity
    - External services (Stripe, etc.)
    - Application version and environment
    """
    checks = {}

    # Check database
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {str(e)[:50]}"

    # Check Stripe (if configured)
    if STRIPE_SECRET_KEY:
        try:
            stripe.Account.retrieve()
            checks["stripe"] = "healthy"
        except Exception:
            checks["stripe"] = "unhealthy"
    else:
        checks["stripe"] = "not_configured"

    # Determine overall status
    unhealthy_services = [k for k, v in checks.items() if "unhealthy" in str(v)]
    overall_status = "unhealthy" if unhealthy_services else "healthy"

    return {
        "status": overall_status,
        "app": APP_NAME,
        "version": API_VERSION,
        "environment": ENVIRONMENT,
        "checks": checks,
        "request_id": get_request_id(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
