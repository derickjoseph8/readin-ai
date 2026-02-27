"""
Pricing Configuration for ReadIn AI

Regional pricing with automatic geo-detection.
Enterprise pricing is hardcoded but hidden from public UI.
"""

from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass


class Region(str, Enum):
    GLOBAL = "global"      # Africa, UAE, Asia
    WESTERN = "western"    # Europe, North America


class PlanType(str, Enum):
    FREE = "free"
    INDIVIDUAL = "individual"
    STARTER = "starter"
    TEAM = "team"
    ENTERPRISE = "enterprise"


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
