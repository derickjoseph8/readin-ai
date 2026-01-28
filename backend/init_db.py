"""Database initialization script for ReadIn AI.

Run this script to create all database tables.
Usage: python init_db.py
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import DATABASE_URL
from database import Base, engine, init_db
from models import User, DailyUsage


def main():
    print("ReadIn AI - Database Initialization")
    print("=" * 40)
    print(f"Database: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL}")
    print()

    try:
        # Create all tables
        print("Creating database tables...")
        init_db()
        print("  - users table")
        print("  - daily_usage table")
        print()
        print("Database initialized successfully!")

    except Exception as e:
        print(f"Error initializing database: {e}")
        print()
        print("Troubleshooting:")
        print("  1. Make sure PostgreSQL is running")
        print("  2. Create the database: createdb readin_ai")
        print("  3. Check DATABASE_URL in .env file")
        sys.exit(1)


if __name__ == "__main__":
    main()
