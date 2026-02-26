"""Alembic environment configuration for ReadIn AI.

This module configures Alembic to work with both SQLite (development)
and PostgreSQL (production) databases by loading the DATABASE_URL
from the application's config module.

Features:
- Automatic model import for autogenerate support
- SQLite and PostgreSQL compatibility
- Batch mode for SQLite ALTER TABLE limitations
- Proper connection handling for both sync and async contexts
"""

import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from alembic import context

# Add the backend directory to sys.path for imports
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

# Import application configuration and models
from config import DATABASE_URL
from database import Base

# Import all models to register them with Base.metadata
# This is required for autogenerate to detect model changes
import models  # noqa: F401

# Alembic Config object - provides access to alembic.ini values
config = context.config

# Set the SQLAlchemy URL from application config
# This overrides any value in alembic.ini
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Setup logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate support
# This tells Alembic what the "desired" schema should look like
target_metadata = Base.metadata

# =============================================================================
# CUSTOMIZATION OPTIONS
# =============================================================================

# Tables to exclude from autogenerate
# Add table names here if you have tables managed outside of SQLAlchemy
EXCLUDE_TABLES = set()

# Schema naming conventions (optional)
# Helps generate consistent constraint names across databases
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}


def include_object(object, name, type_, reflected, compare_to):
    """Filter objects for autogenerate.

    Determines which database objects should be included in migrations.

    Args:
        object: The SQLAlchemy schema object
        name: Name of the object
        type_: Type of object (table, column, index, etc.)
        reflected: True if the object was reflected from the database
        compare_to: The object being compared against (for autogenerate)

    Returns:
        bool: True to include the object, False to skip it
    """
    if type_ == "table" and name in EXCLUDE_TABLES:
        return False
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine,
    though an Engine is acceptable here as well. By skipping the Engine
    creation we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")

    # Determine if we're using SQLite
    is_sqlite = url.startswith("sqlite")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        # Enable batch mode for SQLite to handle ALTER TABLE limitations
        render_as_batch=is_sqlite,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate a
    connection with the context.
    """
    # Get the URL and determine database type
    url = config.get_main_option("sqlalchemy.url")
    is_sqlite = url.startswith("sqlite")

    # Configure SQLAlchemy engine
    # Use different settings for SQLite vs PostgreSQL
    if is_sqlite:
        connect_args = {"check_same_thread": False}
        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
            connect_args=connect_args,
        )
    else:
        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            # Enable batch mode for SQLite to handle ALTER TABLE limitations
            render_as_batch=is_sqlite,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# Execute the appropriate migration runner
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
