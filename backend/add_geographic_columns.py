#!/usr/bin/env python3
"""
Migration script to add geographic and industry columns to users table.
Run this on the server: python add_geographic_columns.py
"""

import sys
from sqlalchemy import text, inspect
from database import engine
from config import DATABASE_URL

def migrate():
    """Add country, city, and industry columns to users table."""
    print("Adding geographic columns to users table...")
    is_sqlite = DATABASE_URL.startswith("sqlite")

    with engine.connect() as conn:
        # Get existing columns
        inspector = inspect(engine)
        existing_columns = [col['name'] for col in inspector.get_columns('users')]

        # Add country column if not exists
        if 'country' not in existing_columns:
            print("  Adding 'country' column...")
            conn.execute(text("ALTER TABLE users ADD COLUMN country VARCHAR(100)"))
            print("  [OK] Added 'country' column")
        else:
            print("  [OK] 'country' column already exists")

        # Add city column if not exists
        if 'city' not in existing_columns:
            print("  Adding 'city' column...")
            conn.execute(text("ALTER TABLE users ADD COLUMN city VARCHAR(100)"))
            print("  [OK] Added 'city' column")
        else:
            print("  [OK] 'city' column already exists")

        # Add industry column if not exists
        if 'industry' not in existing_columns:
            print("  Adding 'industry' column...")
            conn.execute(text("ALTER TABLE users ADD COLUMN industry VARCHAR(100)"))
            print("  [OK] Added 'industry' column")
        else:
            print("  [OK] 'industry' column already exists")

        conn.commit()

    print("\nMigration completed successfully!")
    return True

if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)
