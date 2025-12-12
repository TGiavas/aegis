"""
Pydantic schemas for alert rule endpoints.

Alert rules define conditions that trigger alerts when events match them.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# =============================================================================
# SHARED FIELDS
# =============================================================================


class AlertRuleBase(BaseModel):
    """
    Base fields shared by create/update/response schemas.
    """
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Unique rule identifier (e.g., 'critical_error', 'high_latency')",
        examples=["critical_error", "high_latency", "error_event"],
    )
    
    field: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Event field to check (e.g., 'severity', 'latency_ms')",
        examples=["severity", "latency_ms", "event_type", "source"],
    )
    
    operator: str = Field(
        ...,
        pattern=r"^(==|!=|>|<|>=|<=)$",
        description="Comparison operator",
        examples=["==", ">", ">="],
    )
    
    value: str = Field(
        ...,
        max_length=255,
        description="Value to compare against (stored as string)",
        examples=["CRITICAL", "5000", "api-gateway"],
    )
    
    alert_level: str = Field(
        ...,
        pattern=r"^(LOW|MEDIUM|HIGH|CRITICAL)$",
        description="Severity level for triggered alerts",
        examples=["HIGH", "MEDIUM"],
    )
    
    message_template: str = Field(
        ...,
        min_length=1,
        description="Message template with placeholders like {source}, {event_type}",
        examples=["Critical event from {source}: {event_type}"],
    )
    
    enabled: bool = Field(
        default=True,
        description="Whether this rule is active",
    )


# =============================================================================
# REQUEST SCHEMAS
# =============================================================================


class AlertRuleCreate(AlertRuleBase):
    """
    Schema for creating a new alert rule.
    
    Example:
        {
            "name": "critical_error",
            "field": "severity",
            "operator": "==",
            "value": "CRITICAL",
            "alert_level": "HIGH",
            "message_template": "Critical event from {source}: {event_type}",
            "enabled": true
        }
    """
    pass


class AlertRuleUpdate(BaseModel):
    """
    Schema for updating an existing alert rule.
    All fields are optional - only provided fields will be updated.
    
    Example:
        {
            "enabled": false
        }
    """
    
    field: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=50,
        description="Event field to check",
    )
    
    operator: Optional[str] = Field(
        default=None,
        pattern=r"^(==|!=|>|<|>=|<=)$",
        description="Comparison operator",
    )
    
    value: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Value to compare against",
    )
    
    alert_level: Optional[str] = Field(
        default=None,
        pattern=r"^(LOW|MEDIUM|HIGH|CRITICAL)$",
        description="Severity level for triggered alerts",
    )
    
    message_template: Optional[str] = Field(
        default=None,
        min_length=1,
        description="Message template with placeholders",
    )
    
    enabled: Optional[bool] = Field(
        default=None,
        description="Whether this rule is active",
    )


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================


class AlertRuleResponse(BaseModel):
    """
    Alert rule data returned from API.
    
    Example:
        {
            "id": 1,
            "name": "critical_error",
            "project_id": null,
            "field": "severity",
            "operator": "==",
            "value": "CRITICAL",
            "alert_level": "HIGH",
            "message_template": "Critical event from {source}: {event_type}",
            "enabled": true,
            "created_at": "2025-01-01T12:00:00Z",
            "updated_at": "2025-01-01T12:00:00Z"
        }
    """
    
    id: int
    name: str
    project_id: Optional[int]
    field: str
    operator: str
    value: str
    alert_level: str
    message_template: str
    enabled: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class AlertRuleListResponse(BaseModel):
    """
    List of alert rules (no pagination - rules are typically few).
    """
    
    items: list[AlertRuleResponse]
    total: int

