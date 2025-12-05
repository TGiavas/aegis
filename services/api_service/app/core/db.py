"""
Database connection and session management.

SQLAlchemy 2.0 async pattern:
- Engine: manages the connection pool
- SessionLocal: factory for creating database sessions
- Base: parent class for all our ORM models
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


# =============================================================================
# DATABASE ENGINE
# =============================================================================
# The engine is the starting point for any SQLAlchemy application.
# It maintains a pool of connections to the database.
#
# - create_async_engine: creates an async-capable engine (for use with await)
# - echo=settings.debug: when True, logs all SQL statements (useful for debugging)
# - pool_pre_ping=True: tests connections before using them (handles stale connections)

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
)


# =============================================================================
# SESSION FACTORY
# =============================================================================
# A session represents a "conversation" with the database.
# It tracks changes to objects and commits them as a transaction.
#
# - async_sessionmaker: factory that creates AsyncSession instances
# - bind=engine: sessions use our engine's connection pool
# - expire_on_commit=False: objects remain usable after commit
#   (without this, accessing attributes after commit would trigger a refresh)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# =============================================================================
# BASE MODEL CLASS
# =============================================================================
# All our database models (User, Project, Event, etc.) will inherit from this.
# SQLAlchemy uses this to:
# - Track all models in one registry
# - Generate database tables from model definitions
# - Handle relationships between models

class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


# =============================================================================
# DEPENDENCY: GET DATABASE SESSION
# =============================================================================
# This is a FastAPI dependency that provides a database session to route handlers.
# 
# How it works:
# 1. When a request comes in, FastAPI calls this function
# 2. `async with` opens a session
# 3. `yield` gives the session to the route handler
# 4. After the route finishes, the `async with` block closes the session
#
# This pattern ensures sessions are always properly closed, even if errors occur.

async def get_db() -> AsyncSession:
    """
    Dependency that provides a database session.
    
    Usage in a route:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            # use db here
    """
    async with AsyncSessionLocal() as session:
        yield session

