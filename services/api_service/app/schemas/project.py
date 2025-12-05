"""
Pydantic schemas for project endpoints.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# =============================================================================
# REQUEST SCHEMAS
# =============================================================================


class ProjectCreateRequest(BaseModel):
    """
    Request body for POST /projects
    
    Example:
        {
            "name": "my-web-app",
            "description": "Production monitoring for web application"
        }
    """
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique project name",
        examples=["my-web-app"],
    )
    
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional project description",
        examples=["Production monitoring for web application"],
    )


class ProjectUpdateRequest(BaseModel):
    """
    Request body for PATCH /projects/{id}
    
    All fields are optional — only provided fields are updated.
    
    Example:
        {
            "description": "Updated description"
        }
    """
    
    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="New project name",
    )
    
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="New project description",
    )


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================


class ProjectResponse(BaseModel):
    """
    Project information returned from API.
    
    Example:
        {
            "id": 1,
            "name": "my-web-app",
            "description": "Production monitoring",
            "owner_id": 1,
            "created_at": "2025-01-01T12:00:00Z"
        }
    """
    
    id: int
    name: str
    description: Optional[str]
    owner_id: int
    created_at: datetime
    
    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    """
    Paginated list of projects.
    
    Example:
        {
            "items": [...],
            "total": 10,
            "page": 1,
            "size": 20
        }
    """
    
    items: list[ProjectResponse]
    total: int
    page: int
    size: int

