"""
Pydantic schemas for alert endpoints.

Alerts are created by the analytics_service, but viewed/resolved through api_service.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================


class AlertResponse(BaseModel):
    """
    Alert data returned from API.
    
    Example:
        {
            "id": 1,
            "project_id": 1,
            "rule_name": "error_spike",
            "message": "Error rate exceeded 10% in the last 5 minutes",
            "level": "HIGH",
            "created_at": "2025-01-01T12:00:00Z",
            "resolved_at": null
        }
    """
    
    id: int
    project_id: int
    rule_name: str
    message: str
    level: str  # LOW, MEDIUM, HIGH, CRITICAL
    created_at: datetime
    resolved_at: Optional[datetime]
    
    model_config = {"from_attributes": True}


class AlertListResponse(BaseModel):
    """
    Paginated list of alerts.
    """
    
    items: list[AlertResponse]
    total: int
    page: int
    size: int

