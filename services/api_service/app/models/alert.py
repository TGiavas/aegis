"""
Alert model - represents the 'alerts' table in the database.

Alerts are created by the Analytics Service when rules detect problems:
- Error Spike Rule: Too many ERROR events in a short time
- High Latency Rule: An event with latency > 1000ms

Alerts have a lifecycle:
1. Created (when rule triggers)
2. Open (needs attention)
3. Resolved (user marked it as handled)
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from app.models.project import Project


class Alert(Base):
    """
    Alert model - notification that something needs attention.
    
    Attributes:
        id: Primary key
        project_id: Which project this alert belongs to
        rule_name: Which rule created this alert ("error_spike", "high_latency")
        message: Human-readable description of what happened
        level: Severity ("LOW", "MEDIUM", "HIGH")
        created_at: When the alert was created
        resolved_at: When the alert was resolved (NULL if still open)
    """
    
    __tablename__ = "alerts"
    
    __table_args__ = (
        # Index for: "Get all alerts for a project, sorted by time"
        # Used in: GET /alerts?project_id=1
        Index("ix_alerts_project_created", "project_id", "created_at"),
        
        # Index for: "Get open (unresolved) alerts for a project"
        # Used in: GET /alerts?project_id=1&only_open=true
        Index("ix_alerts_project_resolved", "project_id", "resolved_at"),
        
        # Index for: "Check if duplicate alert exists" (used by analytics service)
        # Prevents creating multiple error_spike alerts for the same incident
        Index("ix_alerts_project_rule_resolved", "project_id", "rule_name", "resolved_at"),
    )
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id"),
        nullable=False,
    )
    
    # RULE NAME
    # ---------
    # Identifies which rule created this alert.
    # Currently supported:
    #   - "error_spike": 5+ ERROR events in 5 minutes
    #   - "high_latency": Single event with latency > 1000ms
    #
    # Stored as string (not enum) for flexibility to add new rules.
    
    rule_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    
    # MESSAGE
    # -------
    # Human-readable description of what triggered the alert.
    # Examples:
    #   - "High error rate detected: 7 errors in the last 5 minutes."
    #   - "High latency event detected: 1523 ms from source 'api-server-1'."
    #
    # Using Text (not String) for unlimited length.
    
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    
    # LEVEL (SEVERITY)
    # ----------------
    # How urgent is this alert?
    #   - "LOW": Informational, no immediate action needed
    #   - "MEDIUM": Worth investigating soon
    #   - "HIGH": Needs immediate attention
    #
    # Current rules:
    #   - error_spike → HIGH (indicates systemic problem)
    #   - high_latency → MEDIUM (single slow request)
    
    level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    
    created_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=False,
        server_default=text("now()"),
    )
    
    # RESOLVED_AT
    # -----------
    # When a user marks the alert as "handled" or "resolved".
    # 
    # NULL = alert is still open, needs attention
    # timestamp = alert was resolved at this time
    #
    # This is similar to the soft-delete pattern in ApiKey,
    # but here it represents a state transition, not deletion.
    
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        default=None,
    )
    
    # ==========================================================================
    # RELATIONSHIPS
    # ==========================================================================
    
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="alerts",
    )
    
    # ==========================================================================
    # HELPER PROPERTIES
    # ==========================================================================
    
    @property
    def is_resolved(self) -> bool:
        """Check if this alert has been resolved."""
        return self.resolved_at is not None
    
    @property
    def is_open(self) -> bool:
        """Check if this alert is still open (not resolved)."""
        return self.resolved_at is None
    
    def __repr__(self) -> str:
        status = "resolved" if self.is_resolved else "open"
        return f"<Alert id={self.id} rule='{self.rule_name}' level='{self.level}' {status}>"


