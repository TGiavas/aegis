"""
Pydantic schemas for API key endpoints.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# =============================================================================
# REQUEST SCHEMAS
# =============================================================================


class ApiKeyCreateRequest(BaseModel):
    """
    Request body for POST /projects/{id}/api-keys
    
    Example:
        {
            "name": "Production Server"
        }
    """
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Friendly name for the API key",
        examples=["Production Server", "CI/CD Pipeline"],
    )


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================


class ApiKeyResponse(BaseModel):
    """
    API key info returned when listing keys.
    
    Note: Does NOT include the full key - only the prefix!
    
    Example:
        {
            "id": 1,
            "project_id": 1,
            "name": "Production Server",
            "key_prefix": "aegis_ab",
            "created_at": "2025-01-01T12:00:00Z",
            "revoked_at": null,
            "is_active": true
        }
    """
    
    id: int
    project_id: int
    name: str
    key_prefix: str
    created_at: datetime
    revoked_at: Optional[datetime]
    is_active: bool
    
    model_config = {"from_attributes": True}


class ApiKeyCreateResponse(BaseModel):
    """
    Response when creating a new API key.
    
    IMPORTANT: The full `key` is returned ONLY at creation time!
    Store it securely - it cannot be retrieved again.
    
    Example:
        {
            "id": 1,
            "project_id": 1,
            "name": "Production Server",
            "key": "aegis_ab12cd34ef56gh78ij90kl12mn34op56",
            "key_prefix": "aegis_ab",
            "created_at": "2025-01-01T12:00:00Z"
        }
    """
    
    id: int
    project_id: int
    name: str
    key: str = Field(
        ...,
        description="Full API key - SAVE THIS! It won't be shown again.",
    )
    key_prefix: str
    created_at: datetime


class ApiKeyListResponse(BaseModel):
    """
    List of API keys for a project.
    """
    
    items: list[ApiKeyResponse]
    total: int

