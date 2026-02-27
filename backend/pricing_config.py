"""
Pricing Configuration for ReadIn AI

Regional pricing with automatic geo-detection.
Enterprise pricing is hardcoded but hidden from public UI.
"""

import os
import json
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta


class Region(str, Enum):
    GLOBAL = "global"      # Africa, UAE, Asia
    WESTERN = "western"    # Europe, North America


class PlanType(str, Enum):
    FREE = "free"
    INDIVIDUAL = "individual"
    STARTER = "starter"
    TEAM = "team"
    ENTERPRISE = "enterprise"


# =============================================================================
# TEST PRICING OVERRIDES (for testing payment flows)
# =============================================================================

# Load test pricing emails from environment variable (JSON format)
# Example: TEST_PRICING_EMAILS='{"email@example.com": {"individual_monthly": 0.99, "individual_annual": 9.90}}'
TEST_PRICING_EMAILS: Dict[str, Dict[str, float]] = {}
_test_pricing_env = os.getenv("TEST_PRICING_EMAILS", "")
if _test_pricing_env:
    try:
        TEST_PRICING_EMAILS = json.loads(_test_pricing_env)
    except json.JSONDecodeError:
        pass  # Invalid JSON, use empty dict


def get_test_pricing(email: str) -> Optional[Dict[str, float]]:
    """Get test pricing override for specific email."""
    return TEST_PRICING_EMAILS.get(email.lower())


# =============================================================================
# BILLING RULES
# =============================================================================

# Plans that have NO trial period - billed instantly
NO_TRIAL_PLANS = {PlanType.STARTER, PlanType.TEAM, PlanType.ENTERPRISE}

# Plans that get a trial period
TRIAL_PLANS = {PlanType.INDIVIDUAL}
TRIAL_DAYS = 7


# Countries in global pricing region
GLOBAL_COUNTRIES = {
    # Africa
    'KE', 'NG', 'ZA', 'GH', 'TZ', 'UG', 'RW', 'ET', 'EG', 'MA', 'DZ', 'TN',
    'SN', 'CI', 'CM', 'AO', 'MZ', 'ZW', 'BW', 'NA', 'MW', 'ZM', 'MU',
    # Middle East / UAE
    'AE', 'SA', 'QA', 'KW', 'BH', 'OM', 'JO', 'LB', 'IQ', 'IR', 'PK',
    # Asia
    'IN', 'BD', 'LK', 'NP', 'MM', 'TH', 'VN', 'ID', 'MY', 'PH', 'SG',
    'CN', 'JP', 'KR', 'TW', 'HK',
}


@dataclass
class PlanPricing:
    monthly: float
    annual: float  # Annual total (10 months - 2 months free)
    min_seats: int = 1
    max_seats: Optional[int] = None

    @property
    def annual_monthly(self) -> float:
        """Monthly price when billed annually."""
        return round(self.annual / 12, 2)

    @property
    def annual_savings(self) -> float:
        """Amount saved per year with annual billing."""
        return round((self.monthly * 12) - self.annual, 2)


# =============================================================================
# PRICING CONFIGURATION
# =============================================================================

PRICING = {
    Region.GLOBAL: {
        PlanType.FREE: PlanPricing(monthly=0, annual=0, min_seats=1, max_seats=1),
        PlanType.INDIVIDUAL: PlanPricing(monthly=19.99, annual=199.90, min_seats=1, max_seats=1),
        PlanType.STARTER: PlanPricing(monthly=14.99, annual=149.90, min_seats=3, max_seats=9),
        PlanType.TEAM: PlanPricing(monthly=12.99, annual=129.90, min_seats=10, max_seats=50),
        # Enterprise pricing - HIDDEN FROM UI but hardcoded for sales
        PlanType.ENTERPRISE: PlanPricing(monthly=9.99, annual=99.90, min_seats=50, max_seats=None),
    },
    Region.WESTERN: {
        PlanType.FREE: PlanPricing(monthly=0, annual=0, min_seats=1, max_seats=1),
        PlanType.INDIVIDUAL: PlanPricing(monthly=29.99, annual=299.90, min_seats=1, max_seats=1),
        PlanType.STARTER: PlanPricing(monthly=24.99, annual=249.90, min_seats=3, max_seats=9),
        PlanType.TEAM: PlanPricing(monthly=19.99, annual=199.90, min_seats=10, max_seats=50),
        # Enterprise pricing - HIDDEN FROM UI but hardcoded for sales
        PlanType.ENTERPRISE: PlanPricing(monthly=14.99, annual=149.90, min_seats=50, max_seats=None),
    },
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_region_from_country(country_code: str) -> Region:
    """Determine pricing region from country code."""
    return Region.GLOBAL if country_code.upper() in GLOBAL_COUNTRIES else Region.WESTERN


def get_plan_for_seats(seats: int) -> PlanType:
    """Determine plan type based on number of seats."""
    if seats <= 1:
        return PlanType.INDIVIDUAL
    elif seats <= 9:
        return PlanType.STARTER
    elif seats <= 50:
        return PlanType.TEAM
    else:
        return PlanType.ENTERPRISE


def get_pricing(region: Region, plan: PlanType) -> PlanPricing:
    """Get pricing for a specific region and plan."""
    return PRICING[region][plan]


def calculate_billing(
    region: Region,
    seats: int,
    is_annual: bool = False,
    plan_override: Optional[PlanType] = None
) -> Dict[str, Any]:
    """
    Calculate billing for a team.

    Args:
        region: Pricing region (global or western)
        seats: Number of seats
        is_annual: Whether annual billing
        plan_override: Override auto-detected plan (for enterprise custom pricing)

    Returns:
        Dict with billing details
    """
    plan = plan_override or get_plan_for_seats(seats)
    pricing = get_pricing(region, plan)

    # Enforce minimum seats
    effective_seats = max(seats, pricing.min_seats)

    price_per_user = pricing.annual_monthly if is_annual else pricing.monthly

    if plan == PlanType.INDIVIDUAL:
        total_monthly = pricing.monthly
        total_annual = pricing.annual
    else:
        total_monthly = price_per_user * effective_seats
        total_annual = pricing.annual * effective_seats if is_annual else total_monthly * 10

    return {
        "plan": plan.value,
        "region": region.value,
        "seats": effective_seats,
        "price_per_user": price_per_user,
        "total_monthly": round(total_monthly, 2),
        "total_annual": round(total_annual, 2),
        "is_annual": is_annual,
        "is_enterprise": plan == PlanType.ENTERPRISE,
        "requires_sales_contact": plan == PlanType.ENTERPRISE,
        "annual_savings": round((price_per_user * 12 - pricing.annual) * effective_seats, 2) if plan != PlanType.INDIVIDUAL else pricing.annual_savings,
    }


def should_alert_sales(current_seats: int, new_seats: int) -> bool:
    """
    Check if sales team should be alerted about potential enterprise upgrade.

    Alert when team grows to or past 51 seats.
    """
    return current_seats < 51 and new_seats >= 51


def get_enterprise_quote(region: Region, seats: int, is_annual: bool = True) -> Dict[str, Any]:
    """
    Generate enterprise quote for sales team.

    This is the actual pricing that sales can offer (hidden from public).
    """
    pricing = get_pricing(region, PlanType.ENTERPRISE)

    price_per_user = pricing.annual_monthly if is_annual else pricing.monthly
    total_monthly = price_per_user * seats
    total_annual = pricing.annual * seats

    return {
        "plan": "enterprise",
        "region": region.value,
        "seats": seats,
        "price_per_user": price_per_user,
        "total_monthly": round(total_monthly, 2),
        "total_annual": round(total_annual, 2),
        "is_annual": is_annual,
        # Sales can offer this as "negotiated" price
        "recommended_offer": {
            "price_per_user": price_per_user,
            "monthly_total": round(total_monthly, 2),
            "annual_total": round(total_annual, 2),
        },
        # Optional: show higher "list price" for negotiation
        "list_price": {
            "price_per_user": round(price_per_user * 1.3, 2),  # 30% markup
            "monthly_total": round(total_monthly * 1.3, 2),
            "annual_total": round(total_annual * 1.3, 2),
        },
    }


# =============================================================================
# PAYSTACK CONFIGURATION
# =============================================================================

# Paystack plan codes (to be set up in Paystack dashboard)
PAYSTACK_PLANS = {
    Region.GLOBAL: {
        PlanType.INDIVIDUAL: {
            "monthly": "PLN_global_individual_monthly",
            "annual": "PLN_global_individual_annual",
        },
        PlanType.STARTER: {
            "monthly": "PLN_global_starter_monthly",
            "annual": "PLN_global_starter_annual",
        },
        PlanType.TEAM: {
            "monthly": "PLN_global_team_monthly",
            "annual": "PLN_global_team_annual",
        },
        PlanType.ENTERPRISE: {
            "monthly": "PLN_global_enterprise_monthly",
            "annual": "PLN_global_enterprise_annual",
        },
    },
    Region.WESTERN: {
        PlanType.INDIVIDUAL: {
            "monthly": "PLN_western_individual_monthly",
            "annual": "PLN_western_individual_annual",
        },
        PlanType.STARTER: {
            "monthly": "PLN_western_starter_monthly",
            "annual": "PLN_western_starter_annual",
        },
        PlanType.TEAM: {
            "monthly": "PLN_western_team_monthly",
            "annual": "PLN_western_team_annual",
        },
        PlanType.ENTERPRISE: {
            "monthly": "PLN_western_enterprise_monthly",
            "annual": "PLN_western_enterprise_annual",
        },
    },
}


def get_paystack_plan_code(region: Region, plan: PlanType, is_annual: bool) -> str:
    """Get Paystack plan code for subscription."""
    interval = "annual" if is_annual else "monthly"
    return PAYSTACK_PLANS[region][plan][interval]


# =============================================================================
# BILLING CYCLE & PRORATION
# =============================================================================

def has_trial_period(plan: PlanType) -> bool:
    """Check if plan type has a trial period."""
    return plan in TRIAL_PLANS


def get_billing_start_date(plan: PlanType) -> datetime:
    """
    Get billing start date based on plan type.

    - Team/Starter/Enterprise: Billed instantly, today is billing cycle start
    - Individual: After trial period ends
    """
    now = datetime.utcnow()

    if plan in NO_TRIAL_PLANS:
        # No trial - billing starts immediately
        return now
    else:
        # Individual gets trial period
        return now + timedelta(days=TRIAL_DAYS)


def calculate_proration(
    region: Region,
    plan: PlanType,
    current_seats: int,
    new_seats: int,
    days_remaining_in_cycle: int,
    total_days_in_cycle: int = 30,
    is_annual: bool = False,
) -> Dict[str, Any]:
    """
    Calculate prorated amount when adding seats mid-cycle.

    Args:
        region: Pricing region
        plan: Plan type
        current_seats: Current number of seats
        new_seats: New total seats (must be > current_seats)
        days_remaining_in_cycle: Days left until next billing date
        total_days_in_cycle: Total days in billing cycle (30 for monthly, 365 for annual)
        is_annual: Whether annual billing

    Returns:
        Dict with proration details
    """
    if new_seats <= current_seats:
        return {
            "prorated_amount": 0,
            "additional_seats": 0,
            "message": "No additional seats to prorate",
        }

    pricing = get_pricing(region, plan)
    additional_seats = new_seats - current_seats

    # Get price per seat per cycle
    if is_annual:
        price_per_seat = pricing.annual
        total_days_in_cycle = 365
    else:
        price_per_seat = pricing.monthly
        total_days_in_cycle = 30

    # Calculate daily rate per seat
    daily_rate = price_per_seat / total_days_in_cycle

    # Prorated amount for additional seats
    prorated_amount = daily_rate * additional_seats * days_remaining_in_cycle

    return {
        "additional_seats": additional_seats,
        "days_remaining": days_remaining_in_cycle,
        "daily_rate_per_seat": round(daily_rate, 4),
        "prorated_amount": round(prorated_amount, 2),
        "next_cycle_amount": round(price_per_seat * new_seats, 2),
        "message": f"Prorated charge for {additional_seats} additional seat(s) for {days_remaining_in_cycle} days",
    }


def enforce_minimum_seats(plan: PlanType, requested_seats: int, region: Region) -> int:
    """
    Enforce minimum seats for billing.

    Returns the billable seat count (at least the plan minimum).
    """
    pricing = get_pricing(region, plan)
    return max(requested_seats, pricing.min_seats)


def calculate_billing_with_enforcement(
    region: Region,
    seats: int,
    is_annual: bool = False,
    plan_override: Optional[PlanType] = None,
    user_email: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Calculate billing with minimum seat enforcement and test pricing.

    Args:
        region: Pricing region
        seats: Requested number of seats
        is_annual: Whether annual billing
        plan_override: Override auto-detected plan
        user_email: User email for test pricing override

    Returns:
        Dict with billing details including enforced minimums
    """
    plan = plan_override or get_plan_for_seats(seats)
    pricing = get_pricing(region, plan)

    # Enforce minimum seats for billing
    billable_seats = enforce_minimum_seats(plan, seats, region)

    # Check for test pricing override
    test_pricing = get_test_pricing(user_email) if user_email else None

    if test_pricing and plan == PlanType.INDIVIDUAL:
        # Use test pricing for individual plan
        price_per_user = test_pricing.get("individual_annual" if is_annual else "individual_monthly", pricing.monthly)
        total_monthly = price_per_user
        total_annual = test_pricing.get("individual_annual", pricing.annual)
        is_test_pricing = True
    else:
        price_per_user = pricing.annual_monthly if is_annual else pricing.monthly
        is_test_pricing = False

        if plan == PlanType.INDIVIDUAL:
            total_monthly = pricing.monthly
            total_annual = pricing.annual
        else:
            total_monthly = price_per_user * billable_seats
            total_annual = pricing.annual * billable_seats if is_annual else total_monthly * 10

    return {
        "plan": plan.value,
        "region": region.value,
        "requested_seats": seats,
        "billable_seats": billable_seats,
        "minimum_seats": pricing.min_seats,
        "price_per_user": round(price_per_user, 2),
        "total_monthly": round(total_monthly, 2),
        "total_annual": round(total_annual, 2),
        "is_annual": is_annual,
        "is_enterprise": plan == PlanType.ENTERPRISE,
        "has_trial": has_trial_period(plan),
        "billing_starts": get_billing_start_date(plan).isoformat(),
        "is_test_pricing": is_test_pricing,
    }
