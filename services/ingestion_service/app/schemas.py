"""
Pydantic schemas for event ingestion.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class EventIngestRequest(BaseModel):
    """
    Request body for ingesting an event.
    
    Example:
        {
            "source": "web-server-01",
            "event_type": "METRIC",
            "severity": "INFO",
            "latency_ms": 150,
            "payload": {"cpu": 45.2, "memory": 78.5}
        }
    """
    
    source: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Source of the event (server name, service name, etc.)",
        examples=["web-server-01", "api-gateway", "database-primary"],
    )
    
    event_type: str = Field(
        ...,
        description="Type of event",
        examples=["METRIC", "LOG", "TRACE"],
    )
    
    severity: str = Field(
        default="INFO",
        description="Event severity level",
        examples=["INFO", "WARN", "ERROR", "CRITICAL"],
    )
    
    latency_ms: Optional[int] = Field(
        default=None,
        ge=0,
        description="Optional latency in milliseconds",
        examples=[150, 2500],
    )
    
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional event data as JSON",
        examples=[{"cpu": 45.2, "memory": 78.5}],
    )


class EventIngestResponse(BaseModel):
    """
    Response after successfully ingesting an event.
    """
    
    id: int = Field(..., description="ID of the created event")
    project_id: int
    source: str
    event_type: str
    severity: str
    latency_ms: Optional[int]
    created_at: datetime
    message: str = Field(
        default="Event ingested successfully",
        description="Status message",
    )

