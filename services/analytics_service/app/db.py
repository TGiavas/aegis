"""
Database connection for analytics service.

We need to:
- Read events (for analysis)
- Read existing alerts (to avoid duplicates)
- Create new alerts
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime, Boolean, text
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
# MODELS
# =============================================================================


class Alert(Base):
    """
    Alert model - we CREATE these when thresholds are exceeded.
    """
    __tablename__ = "alerts"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column()  # FK exists in DB
    rule_name: Mapped[str] = mapped_column(String(50))
    message: Mapped[str] = mapped_column(Text)
    level: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class AlertRule(Base):
    """
    AlertRule model - READ-ONLY mirror of the API service model.
    
    We read rules from the database to evaluate events.
    Rules are managed via the API service.
    """
    __tablename__ = "alert_rules"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    project_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    field: Mapped[str] = mapped_column(String(50))
    operator: Mapped[str] = mapped_column(String(10))
    value: Mapped[str] = mapped_column(String(255))
    alert_level: Mapped[str] = mapped_column(String(20))
    message_template: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    
    @property
    def is_global(self) -> bool:
        """Check if this is a global rule (applies to all projects)."""
        return self.project_id is None


# =============================================================================
# DEPENDENCY
# =============================================================================


async def get_db() -> AsyncSession:
    """Get database session."""
    async with AsyncSessionLocal() as session:
        yield session

