"""
Alembic environment configuration.

This file is run by Alembic whenever you execute a migration command.
It sets up the database connection and tells Alembic about our models.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy import create_engine

# =============================================================================
# IMPORT OUR APPLICATION CODE
# =============================================================================
# We need to import:
# 1. Our database Base (so Alembic knows the target schema)
# 2. All our models (so they're registered with Base)
# 3. Our settings (to get the database URL)

from app.core.config import settings
from app.core.db import Base

# Import all models so they register with Base.metadata
# Without these imports, Alembic won't see the tables!
from app.models.user import User
from app.models.project import Project
from app.models.api_key import ApiKey
from app.models.event import Event
from app.models.alert import Alert

# =============================================================================
# ALEMBIC CONFIG
# =============================================================================

# This is the Alembic Config object (from alembic.ini)
config = context.config

# Set up Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Tell Alembic what our target database schema looks like
# Base.metadata contains info about all tables (from our model imports above)
target_metadata = Base.metadata

# =============================================================================
# DATABASE URL
# =============================================================================
# Override the URL from alembic.ini with our config.py settings
# This ensures we use the same DATABASE_URL environment variable everywhere


def get_url() -> str:
    """Get database URL from our application settings."""
    return settings.database_url


# =============================================================================
# MIGRATION FUNCTIONS
# =============================================================================
# Alembic has two modes: "offline" and "online"
# - Offline: generates SQL without connecting to DB (for review/manual execution)
# - Online: connects to DB and runs migrations directly


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    
    This generates SQL statements without connecting to the database.
    Useful for:
    - Reviewing what SQL will be executed
    - Running migrations manually in production
    - Generating migration scripts for DBAs
    
    Usage: alembic upgrade head --sql > migration.sql
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    
    This connects to the database and runs migrations directly.
    This is the normal mode for development and most deployments.
    
    Usage: alembic upgrade head
    """
    # Create a database engine
    # Note: We use the synchronous create_engine here (not async)
    # because Alembic doesn't support async migrations natively
    connectable = create_engine(
        get_url(),
        poolclass=pool.NullPool,  # Don't pool connections for migrations
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


# =============================================================================
# RUN THE APPROPRIATE MODE
# =============================================================================

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

