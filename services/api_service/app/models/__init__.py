"""
Database models package.

Import all models here so SQLAlchemy can resolve relationships.
Other modules can import from here: `from app.models import User, Project`
"""

from app.models.user import User
from app.models.project import Project
from app.models.api_key import ApiKey
from app.models.event import Event
from app.models.alert import Alert

# Export all models
__all__ = [
    "User",
    "Project",
    "ApiKey",
    "Event",
    "Alert",
]
