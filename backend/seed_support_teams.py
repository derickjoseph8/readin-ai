"""
Seed the default support teams for chat routing.
Run this once to create sales, billing, and technical support teams.
"""

from database import SessionLocal
from models import SupportTeam


DEFAULT_TEAMS = [
    {
        "name": "Sales",
        "slug": "sales",
        "description": "Sales inquiries, pricing questions, demos, and enterprise deals",
        "color": "#10B981",  # Green
        "accepts_tickets": True,
        "accepts_chat": True
    },
    {
        "name": "Billing",
        "slug": "billing",
        "description": "Payment issues, refunds, invoices, and subscription management",
        "color": "#F59E0B",  # Amber
        "accepts_tickets": True,
        "accepts_chat": True
    },
    {
        "name": "Technical Support",
        "slug": "technical-support",
        "description": "Technical issues, bugs, troubleshooting, and feature questions",
        "color": "#3B82F6",  # Blue
        "accepts_tickets": True,
        "accepts_chat": True
    }
]


def seed_support_teams():
    """Create default support teams if they don't exist."""
    db = SessionLocal()

    try:
        for team_data in DEFAULT_TEAMS:
            # Check if team already exists
            existing = db.query(SupportTeam).filter(
                SupportTeam.slug == team_data["slug"]
            ).first()

            if existing:
                print(f"Team '{team_data['name']}' already exists (ID: {existing.id})")
            else:
                team = SupportTeam(**team_data)
                db.add(team)
                db.flush()
                print(f"Created team: {team_data['name']} (ID: {team.id})")

        db.commit()
        print("\nSupport teams ready!")

        # List all teams
        print("\nAll support teams:")
        teams = db.query(SupportTeam).filter(SupportTeam.is_active == True).all()
        for t in teams:
            print(f"  - {t.name} ({t.slug}): {t.description}")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_support_teams()
