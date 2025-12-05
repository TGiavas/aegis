"""
Alert rules for analytics service.

Each rule defines:
- A condition to check
- The alert level if triggered
- The message to display

Rules are evaluated for each incoming event.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from app.config import settings


@dataclass
class AlertTrigger:
    """Result when a rule triggers an alert."""
    rule_name: str
    level: str  # LOW, MEDIUM, HIGH, CRITICAL
    message: str


def check_critical_error(event: Dict[str, Any]) -> Optional[AlertTrigger]:
    """
    Rule: Immediate alert on CRITICAL severity events.
    
    Any event with severity=CRITICAL triggers a HIGH alert immediately.
    """
    if event.get("severity") == "CRITICAL":
        return AlertTrigger(
            rule_name="critical_event",
            level="HIGH",
            message=f"Critical event from {event.get('source')}: {event.get('event_type')}",
        )
    return None


def check_high_latency(event: Dict[str, Any]) -> Optional[AlertTrigger]:
    """
    Rule: Alert on high latency events.
    
    If latency_ms exceeds the threshold, trigger a MEDIUM alert.
    """
    latency = event.get("latency_ms")
    if latency and latency > settings.high_latency_threshold_ms:
        return AlertTrigger(
            rule_name="high_latency",
            level="MEDIUM",
            message=f"High latency detected: {latency}ms from {event.get('source')}",
        )
    return None


def check_error_event(event: Dict[str, Any]) -> Optional[AlertTrigger]:
    """
    Rule: Alert on ERROR severity events.
    
    ERROR events trigger a MEDIUM alert.
    """
    if event.get("severity") == "ERROR":
        return AlertTrigger(
            rule_name="error_event",
            level="MEDIUM",
            message=f"Error event from {event.get('source')}: {event.get('event_type')}",
        )
    return None


# =============================================================================
# RULE EVALUATION
# =============================================================================

# List of all rules to check
ALL_RULES = [
    check_critical_error,
    check_high_latency,
    check_error_event,
]


def evaluate_event(event: Dict[str, Any]) -> list[AlertTrigger]:
    """
    Evaluate all rules against an event.
    
    Returns a list of triggered alerts (may be empty).
    """
    triggers = []
    
    for rule_fn in ALL_RULES:
        result = rule_fn(event)
        if result:
            triggers.append(result)
    
    return triggers

