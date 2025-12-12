"""
Project model - represents the 'projects' table in the database.

A project is a container for events and alerts. Think of it like:
- A separate application being monitored
- A microservice
- A specific environment (prod, staging)

Each project belongs to one user (the owner).
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

# =============================================================================
# TYPE CHECKING IMPORTS
# =============================================================================
# TYPE_CHECKING is a special constant that is:
# - True when type checkers (mypy, pyright) analyze the code
# - False at runtime
#
# We use it to import User only for type hints, avoiding circular imports.
# At runtime, the string "User" in relationship() is resolved lazily.

if TYPE_CHECKING:
    from app.models.alert import Alert
    from app.models.alert_rule import AlertRule
    from app.models.api_key import ApiKey
    from app.models.event import Event
    from app.models.user import User


class Project(Base):
    """
    Project model - container for events and alerts.
    
    Attributes:
        id: Primary key
        name: Unique project name (e.g., "payment-service-prod")
        description: Optional longer description
        owner_id: Foreign key to the user who owns this project
        owner: Relationship to access the User object
        created_at: When the project was created
    """
    
    __tablename__ = "projects"
    
    # ==========================================================================
    # COLUMNS
    # ==========================================================================
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # PROJECT NAME
    # ------------
    # - Must be unique across all projects
    # - Used in API calls and as identifier
    # - Example: "api-gateway", "user-service", "frontend-app"
    
    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    
    # DESCRIPTION
    # -----------
    # - Optional longer description of what this project monitors
    # - Text type allows unlimited length (unlike String(n))
    # - Optional[str] means it can be None
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    # OWNER (FOREIGN KEY)
    # -------------------
    # This links projects to users. The "owner_id" column stores the user's id.
    #
    # ForeignKey("users.id"):
    # - Creates a database constraint
    # - PostgreSQL will reject inserts if owner_id doesn't exist in users table
    # - Format is "table_name.column_name"
    
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,  # Index for faster queries by owner
    )
    
    created_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=False,
        server_default=text("now()"),
    )
    
    # ==========================================================================
    # RELATIONSHIPS
    # ==========================================================================
    # Relationships let you navigate between related objects in Python.
    # They don't create database columns - they use existing foreign keys.
    #
    # With this relationship, you can do:
    #   project = get_project(1)
    #   print(project.owner.email)  # Access the User object directly!
    #
    # "User" as a string: SQLAlchemy resolves this at runtime (avoids circular imports)
    # back_populates="projects": If User has a 'projects' attribute, keep them in sync
    
    owner: Mapped["User"] = relationship(
        "User",
        back_populates="projects",
    )
    
    # A project can have many API keys
    api_keys: Mapped[list["ApiKey"]] = relationship(
        "ApiKey",
        back_populates="project",
    )
    
    # A project can have many events
    events: Mapped[list["Event"]] = relationship(
        "Event",
        back_populates="project",
    )
    
    # A project can have many alerts
    alerts: Mapped[list["Alert"]] = relationship(
        "Alert",
        back_populates="project",
    )
    
    # A project can have custom alert rules (overrides for global rules)
    alert_rules: Mapped[list["AlertRule"]] = relationship(
        "AlertRule",
        back_populates="project",
    )
    
    def __repr__(self) -> str:
        return f"<Project id={self.id} name='{self.name}'>"

