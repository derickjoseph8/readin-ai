"""Configuration settings for ReadIn AI backend."""

import os
import secrets
import sys
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# ENVIRONMENT CONFIGURATION
# =============================================================================

# Environment: development, staging, production
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"
IS_DEVELOPMENT = ENVIRONMENT == "development"
DEBUG = os.getenv("DEBUG", "false").lower() == "true" and not IS_PRODUCTION

# API Version
API_VERSION = "2.1.0"

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost:5432/readin_ai")

# Validate database URL in production
if IS_PRODUCTION and DATABASE_URL == "postgresql://localhost:5432/readin_ai":
    print("[CRITICAL] DATABASE_URL must be configured in production!")
    sys.exit(1)

# =============================================================================
# SECURITY CONFIGURATION
# =============================================================================

# JWT Settings - enforce strong secret
_jwt_secret_default = "dev-only-secret-" + secrets.token_hex(16) if IS_DEVELOPMENT else None
JWT_SECRET = os.getenv("JWT_SECRET", _jwt_secret_default)

# Validate JWT secret
if not JWT_SECRET:
    print("[CRITICAL] JWT_SECRET must be configured!")
    sys.exit(1)

if IS_PRODUCTION and len(JWT_SECRET) < 32:
    print("[CRITICAL] JWT_SECRET must be at least 32 characters in production!")
    sys.exit(1)

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_DAYS = int(os.getenv("ACCESS_TOKEN_EXPIRE_DAYS", "1"))
JWT_EXPIRATION_HOURS = ACCESS_TOKEN_EXPIRE_DAYS * 24  # For SSO compatibility

# Password requirements
PASSWORD_MIN_LENGTH = int(os.getenv("PASSWORD_MIN_LENGTH", "12"))
PASSWORD_REQUIRE_UPPERCASE = os.getenv("PASSWORD_REQUIRE_UPPERCASE", "true").lower() == "true"
PASSWORD_REQUIRE_LOWERCASE = os.getenv("PASSWORD_REQUIRE_LOWERCASE", "true").lower() == "true"
PASSWORD_REQUIRE_DIGIT = os.getenv("PASSWORD_REQUIRE_DIGIT", "true").lower() == "true"
PASSWORD_REQUIRE_SPECIAL = os.getenv("PASSWORD_REQUIRE_SPECIAL", "true").lower() == "true"

# =============================================================================
# CORS CONFIGURATION
# =============================================================================

# Allowed origins - comma-separated list
_default_origins = "http://localhost:3000,http://localhost:8000" if IS_DEVELOPMENT else ""
CORS_ALLOWED_ORIGINS = [
    origin.strip() for origin in os.getenv("CORS_ALLOWED_ORIGINS", _default_origins).split(",")
    if origin.strip()
]

# Production must have explicit origins
if IS_PRODUCTION and not CORS_ALLOWED_ORIGINS:
    print("[CRITICAL] CORS_ALLOWED_ORIGINS must be configured in production!")
    sys.exit(1)

# =============================================================================
# RATE LIMITING CONFIGURATION
# =============================================================================

RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
RATE_LIMIT_LOGIN = os.getenv("RATE_LIMIT_LOGIN", "5/minute")  # Login attempts
RATE_LIMIT_REGISTER = os.getenv("RATE_LIMIT_REGISTER", "3/minute")  # Registration
RATE_LIMIT_AI = os.getenv("RATE_LIMIT_AI", "10/minute")  # AI generation
RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "100/minute")  # General endpoints

# =============================================================================
# STRIPE CONFIGURATION
# =============================================================================

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_MONTHLY = os.getenv("STRIPE_PRICE_MONTHLY", "")

# =============================================================================
# EMAIL CONFIGURATION
# =============================================================================

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@getreadin.ai")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "ReadIn AI")

# =============================================================================
# EXTERNAL SERVICES
# =============================================================================

# Sentry for error tracking
SENTRY_DSN = os.getenv("SENTRY_DSN", "")

# Redis for caching (future)
REDIS_URL = os.getenv("REDIS_URL", "")

# =============================================================================
# SLACK INTEGRATION
# =============================================================================

SLACK_CLIENT_ID = os.getenv("SLACK_CLIENT_ID", "")
SLACK_CLIENT_SECRET = os.getenv("SLACK_CLIENT_SECRET", "")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET", "")

# =============================================================================
# MICROSOFT TEAMS INTEGRATION
# =============================================================================

TEAMS_CLIENT_ID = os.getenv("TEAMS_CLIENT_ID", "")
TEAMS_CLIENT_SECRET = os.getenv("TEAMS_CLIENT_SECRET", "")
TEAMS_TENANT_ID = os.getenv("TEAMS_TENANT_ID", "")  # Use "common" for multi-tenant

# =============================================================================
# VIDEO PLATFORM INTEGRATIONS (STEALTH MODE - Calendar sync only)
# =============================================================================

# Zoom - OAuth for calendar sync, NOT bot joining
ZOOM_CLIENT_ID = os.getenv("ZOOM_CLIENT_ID", "")
ZOOM_CLIENT_SECRET = os.getenv("ZOOM_CLIENT_SECRET", "")

# Google (for Meet detection via Calendar API)
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

# Cisco Webex - meeting schedule sync
WEBEX_CLIENT_ID = os.getenv("WEBEX_CLIENT_ID", "")
WEBEX_CLIENT_SECRET = os.getenv("WEBEX_CLIENT_SECRET", "")

# Apple Calendar - CalDAV-based integration
APPLE_CLIENT_ID = os.getenv("APPLE_CLIENT_ID", "")  # Sign in with Apple Service ID
APPLE_CLIENT_SECRET = os.getenv("APPLE_CLIENT_SECRET", "")  # Private key contents
APPLE_TEAM_ID = os.getenv("APPLE_TEAM_ID", "")
APPLE_KEY_ID = os.getenv("APPLE_KEY_ID", "")

# Calendly - scheduling integration
CALENDLY_CLIENT_ID = os.getenv("CALENDLY_CLIENT_ID", "")
CALENDLY_CLIENT_SECRET = os.getenv("CALENDLY_CLIENT_SECRET", "")
CALENDLY_WEBHOOK_SECRET = os.getenv("CALENDLY_WEBHOOK_SECRET", "")

# =============================================================================
# CRM INTEGRATIONS
# =============================================================================

# Salesforce CRM
SALESFORCE_CLIENT_ID = os.getenv("SALESFORCE_CLIENT_ID", "")
SALESFORCE_CLIENT_SECRET = os.getenv("SALESFORCE_CLIENT_SECRET", "")

# HubSpot CRM
HUBSPOT_CLIENT_ID = os.getenv("HUBSPOT_CLIENT_ID", "")
HUBSPOT_CLIENT_SECRET = os.getenv("HUBSPOT_CLIENT_SECRET", "")

# =============================================================================
# APP SETTINGS
# =============================================================================

APP_NAME = os.getenv("APP_NAME", "ReadIn AI")
APP_URL = os.getenv("APP_URL", "https://www.getreadin.us")
TRIAL_DAYS = int(os.getenv("TRIAL_DAYS", "7"))
TRIAL_DAILY_LIMIT = int(os.getenv("TRIAL_DAILY_LIMIT", "10"))

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG" if IS_DEVELOPMENT else "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "json" if IS_PRODUCTION else "console")
