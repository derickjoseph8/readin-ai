"""Test script to verify ReadIn AI backend setup.

Run this after setting up the backend to verify everything is configured correctly.
Usage: python test_setup.py
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()


def test_database():
    """Test database connection."""
    print("\n1. Testing Database Connection...")
    try:
        from database import engine
        from sqlalchemy import text

        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        print("   [PASS] Database connected successfully")
        return True
    except Exception as e:
        print(f"   [FAIL] Database error: {e}")
        return False


def test_tables():
    """Test database tables exist."""
    print("\n2. Testing Database Tables...")
    try:
        from database import engine
        from sqlalchemy import inspect

        inspector = inspect(engine)
        tables = inspector.get_table_names()

        if "users" in tables:
            print("   [PASS] Users table exists")
        else:
            print("   [FAIL] Users table not found - run init_db.py")
            return False

        if "daily_usage" in tables:
            print("   [PASS] Daily usage table exists")
        else:
            print("   [FAIL] Daily usage table not found - run init_db.py")
            return False

        return True
    except Exception as e:
        print(f"   [FAIL] Table check error: {e}")
        return False


def test_jwt():
    """Test JWT configuration."""
    print("\n3. Testing JWT Configuration...")
    try:
        from config import JWT_SECRET
        from auth import create_access_token, decode_token

        if JWT_SECRET == "your-super-secret-key-change-this-to-random-string":
            print("   [WARN] Using default JWT_SECRET - change this in production!")
        elif len(JWT_SECRET) < 32:
            print("   [WARN] JWT_SECRET is short - use at least 32 characters")
        else:
            print("   [PASS] JWT_SECRET configured")

        # Test token creation
        token = create_access_token(user_id=1)
        decoded = decode_token(token)
        if decoded == 1:
            print("   [PASS] Token creation and decoding works")
            return True
        else:
            print("   [FAIL] Token decode returned wrong user_id")
            return False
    except Exception as e:
        print(f"   [FAIL] JWT error: {e}")
        return False


def test_stripe():
    """Test Stripe configuration."""
    print("\n4. Testing Stripe Configuration...")
    try:
        from config import STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_PRICE_MONTHLY
        import stripe

        if not STRIPE_SECRET_KEY:
            print("   [FAIL] STRIPE_SECRET_KEY not set")
            return False

        stripe.api_key = STRIPE_SECRET_KEY

        # Test API connection
        try:
            account = stripe.Account.retrieve()
            is_test = STRIPE_SECRET_KEY.startswith("sk_test")
            mode = "TEST" if is_test else "LIVE"
            print(f"   [PASS] Stripe connected ({mode} mode)")
        except stripe.error.AuthenticationError:
            print("   [FAIL] Invalid Stripe API key")
            return False

        # Check webhook secret
        if STRIPE_WEBHOOK_SECRET:
            print("   [PASS] Webhook secret configured")
        else:
            print("   [WARN] STRIPE_WEBHOOK_SECRET not set - webhooks won't work")

        # Check price ID
        if STRIPE_PRICE_MONTHLY:
            try:
                price = stripe.Price.retrieve(STRIPE_PRICE_MONTHLY)
                amount = price.unit_amount / 100
                print(f"   [PASS] Price configured: ${amount}/{price.recurring.interval}")
            except stripe.error.InvalidRequestError:
                print(f"   [FAIL] Invalid price ID: {STRIPE_PRICE_MONTHLY}")
                return False
        else:
            print("   [WARN] STRIPE_PRICE_MONTHLY not set - run setup_stripe.py")

        return True
    except Exception as e:
        print(f"   [FAIL] Stripe error: {e}")
        return False


def test_api():
    """Test API endpoints."""
    print("\n5. Testing API Endpoints...")
    try:
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)

        # Health check
        response = client.get("/health")
        if response.status_code == 200:
            print("   [PASS] Health endpoint works")
        else:
            print(f"   [FAIL] Health endpoint returned {response.status_code}")
            return False

        # Docs
        response = client.get("/docs")
        if response.status_code == 200:
            print("   [PASS] API docs available at /docs")
        else:
            print("   [WARN] API docs not available")

        return True
    except Exception as e:
        print(f"   [FAIL] API error: {e}")
        return False


def main():
    print("=" * 50)
    print("  ReadIn AI Backend - Setup Verification")
    print("=" * 50)

    results = []

    results.append(("Database", test_database()))
    results.append(("Tables", test_tables()))
    results.append(("JWT", test_jwt()))
    results.append(("Stripe", test_stripe()))
    results.append(("API", test_api()))

    print("\n" + "=" * 50)
    print("  Summary")
    print("=" * 50)

    all_passed = True
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {name}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("  All tests passed! Backend is ready.")
        print("  Start the server with: uvicorn main:app --reload")
    else:
        print("  Some tests failed. Please fix the issues above.")

    print("=" * 50)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
