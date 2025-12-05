"""
Event model - represents the 'events' table in the database.

Events are the core data unit in Aegis. They represent:
- Metrics (CPU usage, memory, latency)
- Logs (error messages, info logs)
- Traces (request spans, transactions)

Events flow: External System → Ingestion Service → Analytics Service → Database
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from app.models.project import Project


class Event(Base):
    """
    Event model - a single event from a monitored system.
    
    Attributes:
        id: Primary key
        project_id: Which project this event belongs to
        source: Where the event came from (e.g., "api-server-1", "sensor-42")
        event_type: Category of event ("METRIC", "LOG", "TRACE")
        severity: Importance level ("INFO", "WARN", "ERROR")
        latency_ms: Response time in milliseconds (for metrics)
        payload: Flexible JSON data with event details
        created_at: When the event was recorded
    """
    
    __tablename__ = "events"
    
    # ==========================================================================
    # TABLE ARGUMENTS (indexes)
    # ==========================================================================
    # We define composite indexes here for query performance.
    # These indexes speed up common queries.
    
    __table_args__ = (
        # Index for: "Get all events for a project, sorted by time"
        # Used in: GET /events?project_id=1
        Index("ix_events_project_created", "project_id", "created_at"),
        
        # Index for: "Get events of a specific severity for a project"
        # Used in: GET /events?project_id=1&severity=ERROR
        # Also used by: Error spike rule (counting ERROR events)
        Index("ix_events_project_severity_created", "project_id", "severity", "created_at"),
    )
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id"),
        nullable=False,
        # No single-column index here - we use composite indexes above
    )
    
    # SOURCE
    # ------
    # Identifies where the event came from within your system.
    # Examples:
    #   - "api-server-1" (specific server)
    #   - "payment-processor" (service name)
    #   - "sensor-42" (IoT device)
    
    source: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    
    # EVENT TYPE
    # ----------
    # Categorizes what kind of event this is.
    # Common types:
    #   - "METRIC": Numerical measurement (CPU, memory, latency)
    #   - "LOG": Text log entry
    #   - "TRACE": Distributed tracing span
    
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    
    # SEVERITY
    # --------
    # How important/serious is this event?
    #   - "INFO": Normal operation, informational
    #   - "WARN": Something unusual, worth noting
    #   - "ERROR": Something went wrong, needs attention
    #
    # The error spike rule counts ERROR events to detect problems.
    
    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    
    # LATENCY (optional)
    # ------------------
    # Response time in milliseconds.
    # Only relevant for metric events that measure timing.
    #
    # Examples:
    #   - API response time: 250 ms
    #   - Database query: 45 ms
    #   - External API call: 1200 ms (would trigger high_latency rule!)
    #
    # NULL means this event doesn't have latency data.
    
    latency_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    
    # PAYLOAD (JSONB)
    # ---------------
    # Flexible JSON field for any additional event data.
    # JSONB is PostgreSQL's binary JSON - efficient storage and querying.
    #
    # Examples:
    #   {"cpu": 0.85, "memory": 0.9}           # Metric
    #   {"message": "User login failed"}       # Log
    #   {"trace_id": "abc123", "span": "db"}   # Trace
    #
    # Benefits of JSONB:
    #   - Schema-less: Different events can have different fields
    #   - Queryable: Can query inside the JSON (WHERE payload->>'cpu' > 0.8)
    #   - Indexable: Can create indexes on JSON paths
    
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),  # Default to empty object
    )
    
    created_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=False,
        server_default=text("now()"),
    )
    
    # ==========================================================================
    # RELATIONSHIPS
    # ==========================================================================
    
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="events",
    )
    
    def __repr__(self) -> str:
        return f"<Event id={self.id} type='{self.event_type}' severity='{self.severity}'>"

