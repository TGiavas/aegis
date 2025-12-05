"""
User model - represents the 'users' table in the database.

This is a SQLAlchemy ORM model. ORM means "Object-Relational Mapping":
- You define a Python class
- SQLAlchemy maps it to a database table
- Each instance of the class represents a row in the table
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

# Import Project only for type checking (avoids circular import)
if TYPE_CHECKING:
    from app.models.project import Project


class User(Base):
    """
    User account model.
    
    Attributes:
        id: Primary key, auto-incremented
        email: Unique email address (used for login)
        password_hash: Bcrypt hash of the password (never store plain passwords!)
        role: Either 'USER' or 'ADMIN'
        created_at: When the account was created
    """
    
    # ==========================================================================
    # TABLE NAME
    # ==========================================================================
    # By default, SQLAlchemy would name this table 'user' (lowercase class name)
    # We explicitly set it to 'users' (plural) which is a common convention
    
    __tablename__ = "users"
    
    # ==========================================================================
    # COLUMNS
    # ==========================================================================
    # Each attribute with 'Mapped' type hint becomes a database column.
    # 'mapped_column' configures how the column behaves.
    
    # PRIMARY KEY
    # -----------
    # - Mapped[int]: This column stores an integer
    # - primary_key=True: This is the unique identifier for each row
    # - PostgreSQL will auto-generate values (1, 2, 3, ...)
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # EMAIL
    # -----
    # - Mapped[str]: This column stores a string
    # - String(255): Maximum 255 characters (standard for emails)
    # - unique=True: No two users can have the same email
    # - nullable=False: This field is required (NOT NULL in SQL)
    # - index=True: Creates a database index for faster lookups
    
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    
    # PASSWORD HASH
    # -------------
    # We NEVER store plain text passwords. Instead:
    # 1. User provides password "secret123"
    # 2. We hash it: bcrypt("secret123") → "$2b$12$LQv3..."
    # 3. We store the hash
    # 4. To verify: bcrypt.verify("secret123", stored_hash) → True/False
    #
    # String(255) is enough for bcrypt hashes (typically ~60 chars)
    
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    
    # ROLE
    # ----
    # Simple role-based access control.
    # - "USER": Regular user, can manage their own projects
    # - "ADMIN": Can do everything (future feature)
    #
    # server_default: PostgreSQL sets this default, not Python
    # This ensures the default works even for raw SQL inserts
    
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'USER'"),
    )
    
    # CREATED_AT
    # ----------
    # Timestamp when the user was created.
    # - timezone.utc: Always store in UTC (as per our spec)
    # - server_default: Let PostgreSQL set the default using now()
    #
    # Note: We use Optional[datetime] with a default because:
    # - When creating a new user in Python, created_at might not be set yet
    # - PostgreSQL will set it via server_default
    
    created_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=False,
        server_default=text("now()"),
    )
    
    # ==========================================================================
    # RELATIONSHIPS
    # ==========================================================================
    # A user can own many projects (one-to-many relationship)
    #
    # With this, you can do:
    #   user = get_user(1)
    #   for project in user.projects:
    #       print(project.name)
    #
    # list["Project"]: This is a collection (list) of Project objects
    # back_populates="owner": Keeps project.owner and user.projects in sync
    
    projects: Mapped[list["Project"]] = relationship(
        "Project",
        back_populates="owner",
    )
    
    # ==========================================================================
    # PYTHON REPRESENTATION
    # ==========================================================================
    # __repr__ is called when you print the object or see it in debugger
    # Useful for debugging: print(user) → <User id=1 email='alice@example.com'>
    
    def __repr__(self) -> str:
        return f"<User id={self.id} email='{self.email}'>"

