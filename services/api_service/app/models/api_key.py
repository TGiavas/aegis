"""
ApiKey model - represents the 'api_keys' table in the database.

API keys are used to authenticate event ingestion requests.
Each project can have multiple API keys (e.g., one per environment or service).

Security design:
- The full key is shown ONLY ONCE at creation time
- We store only the hash (like passwords)
- We store a prefix (e.g., "aegis_ab") for identification in the UI
- Keys can be revoked (soft delete via revoked_at timestamp)
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from app.models.project import Project


class ApiKey(Base):
    """
    API key for authenticating ingestion requests.
    
    Attributes:
        id: Primary key
        project_id: Which project this key belongs to
        key_hash: Bcrypt hash of the full key (never store plain keys!)
        key_prefix: First 8 chars of key for identification (e.g., "aegis_ab")
        name: Human-friendly name (e.g., "production-server")
        created_at: When the key was created
        revoked_at: When the key was revoked (NULL if still active)
    """
    
    __tablename__ = "api_keys"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # FOREIGN KEY TO PROJECT
    # ----------------------
    # Each API key belongs to one project.
    # When you use this key to send events, they go to this project.
    
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id"),
        nullable=False,
        index=True,
    )
    
    # KEY HASH
    # --------
    # Just like passwords, we never store the actual key.
    # Format: bcrypt hash of "aegis_<random32chars>"
    #
    # Why hash?
    # - If database is compromised, attacker can't use the keys
    # - Same security principle as password storage
    
    key_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    
    # KEY PREFIX
    # ----------
    # The first 8 characters of the key (e.g., "aegis_ab")
    # Used in the UI to help users identify which key is which.
    #
    # Example:
    #   Full key:   aegis_ab3f9c2d8e1a4b7c6d5e0f9a8b7c6d5e
    #   Prefix:     aegis_ab
    #   Displayed:  aegis_ab••••••••••••••••••••••••••••
    
    key_prefix: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
    )
    
    # HUMAN-FRIENDLY NAME
    # -------------------
    # Helps users remember what each key is for.
    # Examples: "production-backend", "staging-server", "ci-pipeline"
    
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    
    created_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=False,
        server_default=text("now()"),
    )
    
    # REVOKED_AT (SOFT DELETE)
    # ------------------------
    # Instead of deleting keys, we "revoke" them by setting this timestamp.
    # 
    # Why soft delete?
    # - Audit trail: We know when and that a key was revoked
    # - Recovery: Could potentially un-revoke if needed
    # - References: Other tables might reference this key
    #
    # NULL = key is active
    # timestamp = key was revoked at this time
    
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        default=None,
    )
    
    # ==========================================================================
    # RELATIONSHIPS
    # ==========================================================================
    
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="api_keys",
    )
    
    # ==========================================================================
    # HELPER PROPERTIES
    # ==========================================================================
    
    @property
    def is_active(self) -> bool:
        """Check if this API key is still active (not revoked)."""
        return self.revoked_at is None
    
    def __repr__(self) -> str:
        status = "active" if self.is_active else "revoked"
        return f"<ApiKey id={self.id} name='{self.name}' {status}>"

