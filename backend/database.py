"""Database setup and session management - PostgreSQL/SQLite."""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from config import DATABASE_URL

# Database connection (supports both PostgreSQL and SQLite)
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # PostgreSQL with connection pooling for production performance
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,      # Check connection health before use
        pool_size=10,            # Base pool size
        max_overflow=20,         # Allow up to 30 total connections (10 + 20)
        pool_recycle=3600,       # Recycle connections after 1 hour
        pool_timeout=30,         # Wait up to 30s for connection from pool
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
