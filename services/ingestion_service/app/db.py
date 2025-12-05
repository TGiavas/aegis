"""
Database connection for ingestion service.

We share the same database as api_service, but define only
the models we need for event ingestion.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import String, Integer, DateTime, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import settings


# =============================================================================
# ENGINE & SESSION
# =============================================================================

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


# =============================================================================
# MODELS (minimal definitions for what ingestion_service needs)
# =============================================================================


class ApiKey(Base):
    """
    API key model - we only need to READ these for authentication.
    
    Note: This must match the table created by api_service's migrations.
    We omit ForeignKey since we don't define Project model here.
    """
    __tablename__ = "api_keys"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column()  # FK exists in DB, not needed in ORM
    key_hash: Mapped[str] = mapped_column(String(255))
    key_prefix: Mapped[str] = mapped_column(String(8))
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    @property
    def is_active(self) -> bool:
        return self.revoked_at is None


class Event(Base):
    """
    Event model - we INSERT these when events are received.
    """
    __tablename__ = "events"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column()  # FK exists in DB, not needed in ORM
    source: Mapped[str] = mapped_column(String(100))
    event_type: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(20))
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    payload: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
    )


# =============================================================================
# DEPENDENCY
# =============================================================================


async def get_db() -> AsyncSession:
    """Dependency for getting database sessions."""
    async with AsyncSessionLocal() as session:
        yield session

