#!/usr/bin/env python3
"""
SQLite to PostgreSQL Migration Script for ReadIn AI

This script migrates data from SQLite to PostgreSQL.
Run this ONCE to transfer all data, then update DATABASE_URL to use PostgreSQL.

Usage:
    1. Install PostgreSQL and create database:
       sudo apt install postgresql postgresql-contrib
       sudo -u postgres psql -c "CREATE DATABASE readin_ai;"
       sudo -u postgres psql -c "CREATE USER readin WITH PASSWORD 'your_secure_password';"
       sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE readin_ai TO readin;"
       sudo -u postgres psql -c "ALTER USER readin CREATEDB;"

    2. Run migration:
       python migrate_to_postgres.py --sqlite-path ./readin_ai.db --postgres-url "postgresql://readin:password@localhost:5432/readin_ai"

    3. Update .env with new DATABASE_URL and restart the application
"""

import argparse
import sqlite3
from datetime import datetime
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
import json


def get_sqlite_tables(sqlite_conn):
    """Get list of tables from SQLite database."""
    cursor = sqlite_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    return [row[0] for row in cursor.fetchall()]


def get_table_columns(sqlite_conn, table_name):
    """Get column info for a table."""
    cursor = sqlite_conn.execute(f"PRAGMA table_info({table_name})")
    return [(row[1], row[2]) for row in cursor.fetchall()]  # (name, type)


def get_row_count(sqlite_conn, table_name):
    """Get row count for a table."""
    cursor = sqlite_conn.execute(f"SELECT COUNT(*) FROM {table_name}")
    return cursor.fetchone()[0]


def convert_value(value, col_type):
    """Convert SQLite value to PostgreSQL compatible format."""
    if value is None:
        return None

    col_type_upper = col_type.upper()

    # Handle JSON columns
    if col_type_upper == 'JSON':
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value

    # Handle boolean columns
    if col_type_upper == 'BOOLEAN':
        if isinstance(value, int):
            return bool(value)
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes')
        return bool(value)

    # Handle datetime columns
    if 'DATETIME' in col_type_upper or 'TIMESTAMP' in col_type_upper:
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                return value
        return value

    return value


def migrate_table(sqlite_conn, pg_engine, table_name, columns):
    """Migrate a single table from SQLite to PostgreSQL."""
    print(f"  Migrating table: {table_name}")

    # Get row count
    row_count = get_row_count(sqlite_conn, table_name)
    print(f"    Rows to migrate: {row_count}")

    if row_count == 0:
        print(f"    Skipping empty table")
        return 0

    # Get column names and types
    col_names = [c[0] for c in columns]
    col_types = {c[0]: c[1] for c in columns}

    # Read all data from SQLite
    cursor = sqlite_conn.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()

    # Clear PostgreSQL table first (to allow re-running migration)
    with pg_engine.connect() as conn:
        try:
            conn.execute(text(f"TRUNCATE TABLE {table_name} CASCADE"))
            conn.commit()
        except Exception as e:
            # Table might not exist yet or have no data
            conn.rollback()

    # Insert into PostgreSQL
    migrated = 0
    batch_size = 100

    with pg_engine.connect() as conn:
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]

            for row in batch:
                # Build insert statement
                values = {}
                for j, col_name in enumerate(col_names):
                    values[col_name] = convert_value(row[j], col_types.get(col_name, 'TEXT'))

                # Generate parameterized insert
                col_list = ', '.join(f'"{c}"' for c in col_names)
                param_list = ', '.join(f':{c}' for c in col_names)

                try:
                    conn.execute(
                        text(f'INSERT INTO "{table_name}" ({col_list}) VALUES ({param_list})'),
                        values
                    )
                    migrated += 1
                except Exception as e:
                    print(f"    Error inserting row: {e}")
                    print(f"    Row data: {values}")
                    continue

            conn.commit()
            print(f"    Progress: {min(i + batch_size, len(rows))}/{len(rows)}")

    # Reset sequence for tables with auto-increment
    with pg_engine.connect() as conn:
        try:
            conn.execute(text(f"""
                SELECT setval(pg_get_serial_sequence('"{table_name}"', 'id'),
                       COALESCE(MAX(id), 1)) FROM "{table_name}"
            """))
            conn.commit()
        except Exception:
            pass  # Table might not have id column or sequence

    print(f"    Migrated: {migrated}/{row_count}")
    return migrated


def create_postgres_schema(pg_engine):
    """Create PostgreSQL schema from models."""
    print("Creating PostgreSQL schema from models...")

    # Import models to register them with Base
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    # Temporarily override DATABASE_URL for model import
    os.environ['DATABASE_URL'] = str(pg_engine.url)

    from database import Base
    import models  # noqa: F401 - Import to register models

    # Create all tables
    Base.metadata.create_all(bind=pg_engine)
    print("Schema created successfully!")


def main():
    parser = argparse.ArgumentParser(description='Migrate SQLite to PostgreSQL')
    parser.add_argument('--sqlite-path', required=True, help='Path to SQLite database file')
    parser.add_argument('--postgres-url', required=True, help='PostgreSQL connection URL')
    parser.add_argument('--skip-schema', action='store_true', help='Skip schema creation')
    args = parser.parse_args()

    print("=" * 60)
    print("SQLite to PostgreSQL Migration")
    print("=" * 60)

    # Connect to SQLite
    print(f"\nConnecting to SQLite: {args.sqlite_path}")
    sqlite_conn = sqlite3.connect(args.sqlite_path)

    # Connect to PostgreSQL
    print(f"Connecting to PostgreSQL...")
    pg_engine = create_engine(args.postgres_url, pool_pre_ping=True)

    # Test PostgreSQL connection
    try:
        with pg_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("PostgreSQL connection successful!")
    except Exception as e:
        print(f"Failed to connect to PostgreSQL: {e}")
        return 1

    # Create schema
    if not args.skip_schema:
        create_postgres_schema(pg_engine)

    # Get tables from SQLite
    tables = get_sqlite_tables(sqlite_conn)
    print(f"\nFound {len(tables)} tables in SQLite:")
    for t in tables:
        print(f"  - {t}")

    # Define migration order (respecting foreign keys)
    migration_order = [
        'professions',
        'organizations',
        'users',
        'organization_invites',
        'daily_usage',
        'calendar_integrations',
        'meetings',
        'conversations',
        'topics',
        'conversation_topics',
        'user_learning_profiles',
        'action_items',
        'commitments',
        'meeting_summaries',
        'job_applications',
        'interviews',
        'participant_memories',
        'media_appearances',
        'email_notifications',
        'audit_logs',
        'pre_meeting_briefings',
        'roles',
        'user_roles',
        'sso_providers',
        'sso_sessions',
        'api_keys',
        'webhooks',
        'webhook_deliveries',
        'white_label_configs',
        'user_sessions',
        'in_app_notifications',
        'templates',
        'user_ai_preferences',
        'analytics_events',
        'support_teams',
        'team_members',
        'team_invites',
        'sla_configs',
        'support_tickets',
        'ticket_messages',
        'chat_sessions',
        'chat_messages',
        'agent_status',
        'admin_activity_logs',
    ]

    # Add any tables not in the order list
    remaining_tables = [t for t in tables if t not in migration_order]
    migration_order.extend(remaining_tables)

    # Migrate each table
    print("\nStarting migration...")
    total_migrated = 0

    for table_name in migration_order:
        if table_name not in tables:
            continue

        columns = get_table_columns(sqlite_conn, table_name)
        migrated = migrate_table(sqlite_conn, pg_engine, table_name, columns)
        total_migrated += migrated

    # Close connections
    sqlite_conn.close()
    pg_engine.dispose()

    print("\n" + "=" * 60)
    print(f"Migration complete! Total rows migrated: {total_migrated}")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Update your .env file with the PostgreSQL DATABASE_URL")
    print("2. Restart the application")
    print("3. Verify the data in PostgreSQL")
    print("4. Keep the SQLite backup in case of issues")

    return 0


if __name__ == "__main__":
    exit(main())
