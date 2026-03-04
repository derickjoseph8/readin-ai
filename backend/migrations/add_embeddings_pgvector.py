#!/usr/bin/env python3
"""
Migration: Add pgvector extension and embedding columns for semantic search

This migration:
1. Enables the pgvector extension (PostgreSQL only)
2. Adds embedding column to meetings table
3. Adds embedding column to conversations table
4. Creates indexes for vector similarity search

Requirements:
- PostgreSQL with pgvector extension installed
- For local development: CREATE EXTENSION vector; (as superuser)

Usage: python migrations/add_embeddings_pgvector.py
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from config import DATABASE_URL

# Embedding dimension for all-MiniLM-L6-v2 model
EMBEDDING_DIMENSION = 384


def is_postgresql():
    """Check if we're using PostgreSQL."""
    return DATABASE_URL.startswith("postgresql")


def migrate_postgresql():
    """Run PostgreSQL-specific migration with pgvector."""
    print("Running PostgreSQL migration with pgvector...")

    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # Start transaction
        trans = conn.begin()

        try:
            # 1. Enable pgvector extension
            print("  Enabling pgvector extension...")
            try:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                print("  [OK] pgvector extension enabled")
            except Exception as e:
                print(f"  [WARNING] Could not enable pgvector: {e}")
                print("  You may need to run: CREATE EXTENSION vector; as a superuser")

            # 2. Check if embedding column exists in meetings table
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'meetings' AND column_name = 'embedding'
            """))
            if not result.fetchone():
                print("  Adding embedding column to meetings table...")
                conn.execute(text(f"""
                    ALTER TABLE meetings
                    ADD COLUMN embedding vector({EMBEDDING_DIMENSION})
                """))
                print("  [OK] Added embedding column to meetings")
            else:
                print("  [SKIP] meetings.embedding column already exists")

            # 3. Check if embedding column exists in conversations table
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'conversations' AND column_name = 'embedding'
            """))
            if not result.fetchone():
                print("  Adding embedding column to conversations table...")
                conn.execute(text(f"""
                    ALTER TABLE conversations
                    ADD COLUMN embedding vector({EMBEDDING_DIMENSION})
                """))
                print("  [OK] Added embedding column to conversations")
            else:
                print("  [SKIP] conversations.embedding column already exists")

            # 4. Create index for meetings embeddings (IVFFlat for approximate search)
            result = conn.execute(text("""
                SELECT indexname FROM pg_indexes
                WHERE tablename = 'meetings' AND indexname = 'ix_meetings_embedding'
            """))
            if not result.fetchone():
                print("  Creating vector index on meetings.embedding...")
                # Use IVFFlat index for better performance with many rows
                # lists = sqrt(n) where n is expected number of rows
                conn.execute(text("""
                    CREATE INDEX ix_meetings_embedding
                    ON meetings USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100)
                """))
                print("  [OK] Created vector index on meetings.embedding")
            else:
                print("  [SKIP] meetings embedding index already exists")

            # 5. Create index for conversations embeddings
            result = conn.execute(text("""
                SELECT indexname FROM pg_indexes
                WHERE tablename = 'conversations' AND indexname = 'ix_conversations_embedding'
            """))
            if not result.fetchone():
                print("  Creating vector index on conversations.embedding...")
                conn.execute(text("""
                    CREATE INDEX ix_conversations_embedding
                    ON conversations USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100)
                """))
                print("  [OK] Created vector index on conversations.embedding")
            else:
                print("  [SKIP] conversations embedding index already exists")

            # Commit transaction
            trans.commit()
            print("\nPostgreSQL migration completed successfully!")
            return True

        except Exception as e:
            trans.rollback()
            print(f"\n[ERROR] Migration failed: {e}")
            return False


def migrate_sqlite():
    """Run SQLite migration (stores embeddings as JSON)."""
    print("Running SQLite migration...")
    print("Note: SQLite will store embeddings as JSON text. Semantic search will use in-memory comparison.")

    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

    with engine.connect() as conn:
        trans = conn.begin()

        try:
            # Check and add embedding column to meetings
            result = conn.execute(text("PRAGMA table_info(meetings)"))
            columns = [row[1] for row in result.fetchall()]

            if "embedding" not in columns:
                print("  Adding embedding column to meetings table...")
                conn.execute(text("ALTER TABLE meetings ADD COLUMN embedding TEXT"))
                print("  [OK] Added embedding column to meetings")
            else:
                print("  [SKIP] meetings.embedding column already exists")

            # Check and add embedding column to conversations
            result = conn.execute(text("PRAGMA table_info(conversations)"))
            columns = [row[1] for row in result.fetchall()]

            if "embedding" not in columns:
                print("  Adding embedding column to conversations table...")
                conn.execute(text("ALTER TABLE conversations ADD COLUMN embedding TEXT"))
                print("  [OK] Added embedding column to conversations")
            else:
                print("  [SKIP] conversations.embedding column already exists")

            trans.commit()
            print("\nSQLite migration completed successfully!")
            return True

        except Exception as e:
            trans.rollback()
            print(f"\n[ERROR] Migration failed: {e}")
            return False


def migrate():
    """Run the appropriate migration based on database type."""
    print("=" * 60)
    print("  Semantic Search Embeddings Migration")
    print("=" * 60)
    print(f"Database URL: {DATABASE_URL[:50]}...")
    print()

    if is_postgresql():
        return migrate_postgresql()
    else:
        return migrate_sqlite()


if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
