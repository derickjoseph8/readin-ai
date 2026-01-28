"""Configuration settings for ReadIn AI backend."""

import os
from dotenv import load_dotenv

load_dotenv()

# Database (PostgreSQL)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost:5432/readin_ai")

# JWT Settings
JWT_SECRET = os.getenv("JWT_SECRET", "change-this-secret-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_DAYS = int(os.getenv("ACCESS_TOKEN_EXPIRE_DAYS", "30"))

# Stripe
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_MONTHLY = os.getenv("STRIPE_PRICE_MONTHLY", "")

# App Settings
TRIAL_DAYS = int(os.getenv("TRIAL_DAYS", "7"))
TRIAL_DAILY_LIMIT = int(os.getenv("TRIAL_DAILY_LIMIT", "10"))
APP_NAME = os.getenv("APP_NAME", "ReadIn AI")
