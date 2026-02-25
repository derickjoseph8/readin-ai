"""Database initialization script for ReadIn AI.

Run this script to create all database tables.
Usage: python init_db.py
"""

import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import DATABASE_URL
from database import Base, engine, init_db
from models import User, DailyUsage

# Configure logging for CLI script
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


def main():
    logger.info("ReadIn AI - Database Initialization")
    logger.info("=" * 40)
    db_display = DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL
    logger.info(f"Database: {db_display}")
    logger.info("")

    try:
        # Create all tables
        logger.info("Creating database tables...")
        init_db()
        logger.info("  - users table")
        logger.info("  - daily_usage table")
        logger.info("")
        logger.info("Database initialized successfully!")

    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        logger.error("")
        logger.error("Troubleshooting:")
        logger.error("  1. Make sure PostgreSQL is running")
        logger.error("  2. Create the database: createdb readin_ai")
        logger.error("  3. Check DATABASE_URL in .env file")
        sys.exit(1)


if __name__ == "__main__":
    main()
