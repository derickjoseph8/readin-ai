#!/usr/bin/env python3
"""
Migration: Add company column to users table

Run this script to add the company column for individual users.
Usage: python migrations/add_company_column.py
"""

import sys
import sqlite3
from pathlib import Path

# Database path
DB_PATH = Path(__file__).parent.parent / "readin_ai.db"


def migrate():
    """Add company column to users table if it doesn't exist."""
    print("Adding company column to users table...")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]

        if "company" in columns:
            print("Column 'company' already exists. Skipping.")
            return True

        # Add the column
        cursor.execute("ALTER TABLE users ADD COLUMN company TEXT")
        conn.commit()
        print("Successfully added 'company' column to users table.")
        return True

    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
