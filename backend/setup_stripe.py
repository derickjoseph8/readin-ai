"""Stripe product and price setup script for ReadIn AI.

This script creates the necessary Stripe product and price for the subscription.
Run this once after setting up your Stripe account.

Usage: python setup_stripe.py
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

import stripe

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

PRODUCT_NAME = "ReadIn AI Premium"
PRODUCT_DESCRIPTION = "Unlimited AI-powered responses for live conversations"
MONTHLY_PRICE = 1000  # $10.00 in cents


def create_product():
    """Create or get the ReadIn AI product."""
    # Check if product already exists
    products = stripe.Product.list(limit=100)
    for product in products.data:
        if product.name == PRODUCT_NAME:
            print(f"Product already exists: {product.id}")
            return product

    # Create new product
    product = stripe.Product.create(
        name=PRODUCT_NAME,
        description=PRODUCT_DESCRIPTION,
        metadata={"app": "readin_ai"}
    )
    print(f"Created product: {product.id}")
    return product


def create_price(product_id: str):
    """Create or get the monthly subscription price."""
    # Check if price already exists for this product
    prices = stripe.Price.list(product=product_id, limit=100)
    for price in prices.data:
        if price.unit_amount == MONTHLY_PRICE and price.recurring and price.recurring.interval == "month":
            print(f"Monthly price already exists: {price.id}")
            return price

    # Create new price
    price = stripe.Price.create(
        product=product_id,
        unit_amount=MONTHLY_PRICE,
        currency="usd",
        recurring={"interval": "month"},
        metadata={"app": "readin_ai", "plan": "monthly"}
    )
    print(f"Created monthly price: {price.id}")
    return price


def main():
    print("ReadIn AI - Stripe Setup")
    print("=" * 40)

    if not stripe.api_key:
        print("ERROR: STRIPE_SECRET_KEY not set in .env file")
        sys.exit(1)

    # Check if using test mode
    is_test = stripe.api_key.startswith("sk_test")
    print(f"Mode: {'TEST' if is_test else 'LIVE'}")
    print()

    try:
        # Create product
        print("Setting up product...")
        product = create_product()

        # Create monthly price
        print("\nSetting up monthly price ($10/month)...")
        price = create_price(product.id)

        print("\n" + "=" * 40)
        print("Setup complete!")
        print()
        print("Add this to your backend/.env file:")
        print(f"  STRIPE_PRICE_MONTHLY={price.id}")
        print()

        if is_test:
            print("NOTE: You're using TEST mode. For production:")
            print("  1. Switch to live Stripe keys")
            print("  2. Run this script again to create live products")

    except stripe.error.AuthenticationError:
        print("ERROR: Invalid Stripe API key")
        sys.exit(1)
    except stripe.error.StripeError as e:
        print(f"Stripe error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
