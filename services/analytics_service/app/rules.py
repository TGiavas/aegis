"""
Alert rules for analytics service.

Rules are now loaded from the database and evaluated dynamically.
Each rule defines:
- A condition to check (field, operator, value)
- The alert level if triggered
- A message template with placeholders

Rules are evaluated for each incoming event.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AlertRule


@dataclass
class AlertTrigger:
    """Result when a rule triggers an alert."""
    rule_name: str
    level: str  # LOW, MEDIUM, HIGH, CRITICAL
    message: str


# =============================================================================
# RULE FETCHING
# =============================================================================


async def get_effective_rules(
    db: AsyncSession,
    project_id: int,
) -> list[AlertRule]:
    """
    Fetch effective rules for a project.
    
    Returns global rules + project-specific overrides.
    Project rules override global rules with the same name.
    
    Args:
        db: Database session
        project_id: The project to get rules for
        
    Returns:
        List of effective AlertRule objects
    """
    # Get all enabled global rules and project-specific rules
    query = (
        select(AlertRule)
        .where(
            AlertRule.enabled == True,  # noqa: E712
            or_(
                AlertRule.project_id.is_(None),
                AlertRule.project_id == project_id,
            )
        )
        .order_by(AlertRule.name)
    )
    result = await db.execute(query)
    all_rules = result.scalars().all()
    
    # Dedupe: project rules override global rules with same name
    rules_by_name: dict[str, AlertRule] = {}
    for rule in all_rules:
        if rule.name not in rules_by_name:
            rules_by_name[rule.name] = rule
        elif rule.project_id is not None:
            # Project rule overrides global rule
            rules_by_name[rule.name] = rule
    
    return list(rules_by_name.values())


# =============================================================================
# RULE EVALUATION
# =============================================================================


def _cast_value(value: str, target_type: type) -> Any:
    """
    Cast a string value to the target type.
    
    Args:
        value: String value from the rule
        target_type: Type to cast to (based on event field type)
        
    Returns:
        Cast value, or original string if cast fails
    """
    if target_type == int:
        try:
            return int(value)
        except ValueError:
            return value
    elif target_type == float:
        try:
            return float(value)
        except ValueError:
            return value
    elif target_type == bool:
        return value.lower() in ("true", "1", "yes")
    return value


def _compare(event_value: Any, operator: str, rule_value: str) -> bool:
    """
    Compare an event field value against a rule value using the specified operator.
    
    Args:
        event_value: Value from the event
        operator: Comparison operator (==, !=, >, <, >=, <=)
        rule_value: Value from the rule (as string)
        
    Returns:
        True if the comparison matches, False otherwise
    """
    if event_value is None:
        return False
    
    # Cast rule value to match event value type
    typed_rule_value = _cast_value(rule_value, type(event_value))
    
    if operator == "==":
        return event_value == typed_rule_value
    elif operator == "!=":
        return event_value != typed_rule_value
    elif operator == ">":
        try:
            return event_value > typed_rule_value
        except TypeError:
            return False
    elif operator == "<":
        try:
            return event_value < typed_rule_value
        except TypeError:
            return False
    elif operator == ">=":
        try:
            return event_value >= typed_rule_value
        except TypeError:
            return False
    elif operator == "<=":
        try:
            return event_value <= typed_rule_value
        except TypeError:
            return False
    
    return False


def _format_message(template: str, event: Dict[str, Any]) -> str:
    """
    Format a message template with event values.
    
    Supports placeholders like {source}, {event_type}, {severity}, {latency_ms}.
    Unknown placeholders are left as-is.
    
    Args:
        template: Message template with {placeholder} syntax
        event: Event data dictionary
        
    Returns:
        Formatted message string
    """
    try:
        # Use safe formatting that ignores missing keys
        return template.format_map(SafeDict(event))
    except Exception:
        return template


class SafeDict(dict):
    """Dict subclass that returns placeholder for missing keys."""
    
    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"


def evaluate_rule(rule: AlertRule, event: Dict[str, Any]) -> Optional[AlertTrigger]:
    """
    Evaluate a single rule against an event.
    
    Args:
        rule: The AlertRule to evaluate
        event: Event data dictionary
        
    Returns:
        AlertTrigger if the rule matches, None otherwise
    """
    # Get the event field value
    event_value = event.get(rule.field)
    
    # Compare using the rule's operator
    if _compare(event_value, rule.operator, rule.value):
        return AlertTrigger(
            rule_name=rule.name,
            level=rule.alert_level,
            message=_format_message(rule.message_template, event),
        )
    
    return None


async def evaluate_event(
    db: AsyncSession,
    event: Dict[str, Any],
) -> list[AlertTrigger]:
    """
    Evaluate all effective rules against an event.
    
    Fetches rules from the database and evaluates them dynamically.
    
    Args:
        db: Database session
        event: Event data dictionary (must include project_id)
        
    Returns:
        List of triggered alerts (may be empty)
    """
    project_id = event.get("project_id")
    if project_id is None:
        print("⚠️  Event missing project_id, skipping rule evaluation")
        return []
    
    # Fetch effective rules for this project
    rules = await get_effective_rules(db, project_id)
    
    # Evaluate each rule
    triggers = []
    for rule in rules:
        result = evaluate_rule(rule, event)
        if result:
            triggers.append(result)
    
    return triggers
