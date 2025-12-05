"""
Pydantic schemas for event endpoints.

Events are created by the ingestion_service, but viewed through the api_service.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================


class EventResponse(BaseModel):
    """
    Event data returned from API.
    
    Example:
        {
            "id": 1,
            "project_id": 1,
            "source": "web-server-01",
            "event_type": "METRIC",
            "severity": "INFO",
            "latency_ms": 150,
            "payload": {"cpu": 45.2, "memory": 78.5},
            "created_at": "2025-01-01T12:00:00Z"
        }
    """
    
    id: int
    project_id: int
    source: str
    event_type: str
    severity: str
    latency_ms: Optional[int]
    payload: Dict[str, Any]
    created_at: datetime
    
    model_config = {"from_attributes": True}


class EventListResponse(BaseModel):
    """
    Paginated list of events with filtering info.
    """
    
    items: list[EventResponse]
    total: int
    page: int
    size: int


# =============================================================================
# QUERY PARAMETERS (not a schema, but useful to document)
# =============================================================================
# Events can be filtered by:
# - severity: INFO, WARN, ERROR, CRITICAL
# - event_type: METRIC, LOG, TRACE
# - source: string match
# - created_after: datetime
# - created_before: datetime

