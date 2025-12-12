"""
AlertRule model - represents the 'alert_rules' table in the database.

Alert rules define conditions that trigger alerts when events match them.
Rules can be:
- Global (project_id = NULL): Apply to all projects
- Project-specific (project_id set): Override global rules for that project

Rules with the same name at project level override global rules.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Index, String, Text, Boolean, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from app.models.project import Project


class AlertRule(Base):
    """
    AlertRule model - defines conditions for triggering alerts.
    
    Attributes:
        id: Primary key
        name: Unique rule identifier (e.g., "critical_error", "high_latency")
        project_id: Optional FK to projects (NULL = global rule)
        field: Event field to check (e.g., "severity", "latency_ms")
        operator: Comparison operator ("==", "!=", ">", "<", ">=", "<=")
        value: Value to compare against (stored as string)
        alert_level: Severity level for triggered alerts (LOW, MEDIUM, HIGH, CRITICAL)
        message_template: Message template with placeholders like {source}, {event_type}
        enabled: Whether this rule is active
        created_at: When the rule was created
        updated_at: When the rule was last modified
    """
    
    __tablename__ = "alert_rules"
    
    __table_args__ = (
        # Unique constraint: same name can exist once globally (project_id=NULL)
        # and once per project
        Index(
            "uq_alert_rules_name_project",
            "name",
            "project_id",
            unique=True,
            postgresql_where=text("project_id IS NOT NULL"),
        ),
        # For global rules (project_id IS NULL), name must be unique
        Index(
            "uq_alert_rules_name_global",
            "name",
            unique=True,
            postgresql_where=text("project_id IS NULL"),
        ),
        # Index for fetching rules by project
        Index("ix_alert_rules_project_id", "project_id"),
    )
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # RULE NAME
    # ---------
    # Unique identifier for the rule type.
    # Examples: "critical_error", "high_latency", "error_event"
    # Used to match project overrides with global rules.
    
    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    
    # PROJECT ID (Optional)
    # ---------------------
    # NULL = global rule (applies to all projects)
    # Set = project-specific override
    
    project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("projects.id"),
        nullable=True,
    )
    
    # FIELD
    # -----
    # The event field to check against.
    # Examples: "severity", "latency_ms", "event_type", "source"
    
    field: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    
    # OPERATOR
    # --------
    # Comparison operator to use.
    # Supported: "==", "!=", ">", "<", ">=", "<="
    
    operator: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )
    
    # VALUE
    # -----
    # The value to compare against.
    # Stored as string, cast to appropriate type during evaluation.
    # Examples: "CRITICAL", "5000", "api-gateway"
    
    value: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    
    # ALERT LEVEL
    # -----------
    # Severity of the alert when this rule triggers.
    # Values: "LOW", "MEDIUM", "HIGH", "CRITICAL"
    
    alert_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    
    # MESSAGE TEMPLATE
    # ----------------
    # Template for the alert message.
    # Supports placeholders: {source}, {event_type}, {severity}, {field_value}
    # Example: "Critical event from {source}: {event_type}"
    
    message_template: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    
    # ENABLED
    # -------
    # Whether this rule should be evaluated.
    # Allows disabling rules without deleting them.
    
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )
    
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=text("now()"),
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=text("now()"),
        onupdate=datetime.utcnow,
    )
    
    # ==========================================================================
    # RELATIONSHIPS
    # ==========================================================================
    
    project: Mapped[Optional["Project"]] = relationship(
        "Project",
        back_populates="alert_rules",
    )
    
    # ==========================================================================
    # HELPER PROPERTIES
    # ==========================================================================
    
    @property
    def is_global(self) -> bool:
        """Check if this is a global rule (applies to all projects)."""
        return self.project_id is None
    
    def __repr__(self) -> str:
        scope = "global" if self.is_global else f"project={self.project_id}"
        status = "enabled" if self.enabled else "disabled"
        return f"<AlertRule id={self.id} name='{self.name}' {scope} {status}>"

