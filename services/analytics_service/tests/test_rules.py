"""
Tests for alert rule evaluation logic.

Tests the core rule evaluation functions without requiring a database connection.
"""

import pytest
from unittest.mock import MagicMock

from app.rules import (
    AlertTrigger,
    _cast_value,
    _compare,
    _format_message,
    evaluate_rule,
    SafeDict,
)
from app.db import AlertRule


# =============================================================================
# TEST _cast_value
# =============================================================================


class TestCastValue:
    """Tests for the _cast_value helper function."""

    def test_cast_to_int(self):
        """Should cast string to int when target type is int."""
        assert _cast_value("42", int) == 42
        assert _cast_value("0", int) == 0
        assert _cast_value("-10", int) == -10

    def test_cast_to_int_invalid(self):
        """Should return original string if cast to int fails."""
        assert _cast_value("not_a_number", int) == "not_a_number"
        assert _cast_value("3.14", int) == "3.14"  # float string doesn't cast to int

    def test_cast_to_float(self):
        """Should cast string to float when target type is float."""
        assert _cast_value("3.14", float) == 3.14
        assert _cast_value("42", float) == 42.0
        assert _cast_value("-0.5", float) == -0.5

    def test_cast_to_float_invalid(self):
        """Should return original string if cast to float fails."""
        assert _cast_value("not_a_number", float) == "not_a_number"

    def test_cast_to_bool(self):
        """Should cast string to bool when target type is bool."""
        assert _cast_value("true", bool) is True
        assert _cast_value("True", bool) is True
        assert _cast_value("1", bool) is True
        assert _cast_value("yes", bool) is True
        assert _cast_value("false", bool) is False
        assert _cast_value("0", bool) is False
        assert _cast_value("no", bool) is False

    def test_cast_to_string(self):
        """Should return original string when target type is str."""
        assert _cast_value("hello", str) == "hello"


# =============================================================================
# TEST _compare
# =============================================================================


class TestCompare:
    """Tests for the _compare helper function."""

    # Equality operators
    def test_equals_string(self):
        """== operator should work with strings."""
        assert _compare("CRITICAL", "==", "CRITICAL") is True
        assert _compare("ERROR", "==", "CRITICAL") is False

    def test_equals_int(self):
        """== operator should work with integers."""
        assert _compare(5000, "==", "5000") is True
        assert _compare(1000, "==", "5000") is False

    def test_not_equals(self):
        """!= operator should work correctly."""
        assert _compare("ERROR", "!=", "CRITICAL") is True
        assert _compare("CRITICAL", "!=", "CRITICAL") is False

    # Comparison operators with numbers
    def test_greater_than(self):
        """> operator should work with numbers."""
        assert _compare(6000, ">", "5000") is True
        assert _compare(5000, ">", "5000") is False
        assert _compare(4000, ">", "5000") is False

    def test_less_than(self):
        """< operator should work with numbers."""
        assert _compare(4000, "<", "5000") is True
        assert _compare(5000, "<", "5000") is False
        assert _compare(6000, "<", "5000") is False

    def test_greater_than_or_equal(self):
        """>= operator should work with numbers."""
        assert _compare(6000, ">=", "5000") is True
        assert _compare(5000, ">=", "5000") is True
        assert _compare(4000, ">=", "5000") is False

    def test_less_than_or_equal(self):
        """<= operator should work with numbers."""
        assert _compare(4000, "<=", "5000") is True
        assert _compare(5000, "<=", "5000") is True
        assert _compare(6000, "<=", "5000") is False

    # Edge cases
    def test_none_event_value(self):
        """Should return False when event value is None."""
        assert _compare(None, "==", "CRITICAL") is False
        assert _compare(None, ">", "5000") is False

    def test_invalid_operator(self):
        """Should return False for unknown operators."""
        assert _compare("value", "??", "value") is False

    def test_type_mismatch_comparison(self):
        """Should handle type mismatches gracefully."""
        # String can't be compared with > to an int
        assert _compare("hello", ">", "5000") is False


# =============================================================================
# TEST _format_message
# =============================================================================


class TestFormatMessage:
    """Tests for the _format_message helper function."""

    def test_simple_substitution(self):
        """Should substitute simple placeholders."""
        template = "Event from {source}"
        event = {"source": "api-gateway"}
        
        result = _format_message(template, event)
        
        assert result == "Event from api-gateway"

    def test_multiple_placeholders(self):
        """Should substitute multiple placeholders."""
        template = "Critical event from {source}: {event_type}"
        event = {"source": "api-gateway", "event_type": "request_failed"}
        
        result = _format_message(template, event)
        
        assert result == "Critical event from api-gateway: request_failed"

    def test_missing_placeholder(self):
        """Should leave missing placeholders as-is."""
        template = "Event from {source}: {unknown_field}"
        event = {"source": "api-gateway"}
        
        result = _format_message(template, event)
        
        assert result == "Event from api-gateway: {unknown_field}"

    def test_numeric_value(self):
        """Should handle numeric values in placeholders."""
        template = "High latency: {latency_ms}ms"
        event = {"latency_ms": 5500}
        
        result = _format_message(template, event)
        
        assert result == "High latency: 5500ms"

    def test_no_placeholders(self):
        """Should return template as-is if no placeholders."""
        template = "Static message"
        event = {"source": "api-gateway"}
        
        result = _format_message(template, event)
        
        assert result == "Static message"


# =============================================================================
# TEST SafeDict
# =============================================================================


class TestSafeDict:
    """Tests for the SafeDict helper class."""

    def test_existing_key(self):
        """Should return value for existing keys."""
        d = SafeDict({"key": "value"})
        assert d["key"] == "value"

    def test_missing_key(self):
        """Should return placeholder string for missing keys."""
        d = SafeDict({"key": "value"})
        assert d["missing"] == "{missing}"


# =============================================================================
# TEST evaluate_rule
# =============================================================================


class TestEvaluateRule:
    """Tests for the evaluate_rule function."""

    def _make_rule(
        self,
        name: str = "test_rule",
        field: str = "severity",
        operator: str = "==",
        value: str = "CRITICAL",
        alert_level: str = "HIGH",
        message_template: str = "Alert: {event_type}",
    ) -> AlertRule:
        """Helper to create a mock AlertRule."""
        rule = MagicMock(spec=AlertRule)
        rule.name = name
        rule.field = field
        rule.operator = operator
        rule.value = value
        rule.alert_level = alert_level
        rule.message_template = message_template
        return rule

    def test_rule_matches(self):
        """Should return AlertTrigger when rule matches."""
        rule = self._make_rule(
            name="critical_event",
            field="severity",
            operator="==",
            value="CRITICAL",
            alert_level="HIGH",
            message_template="Critical from {source}",
        )
        event = {
            "severity": "CRITICAL",
            "source": "api-gateway",
            "event_type": "request_failed",
        }
        
        result = evaluate_rule(rule, event)
        
        assert result is not None
        assert isinstance(result, AlertTrigger)
        assert result.rule_name == "critical_event"
        assert result.level == "HIGH"
        assert result.message == "Critical from api-gateway"

    def test_rule_does_not_match(self):
        """Should return None when rule doesn't match."""
        rule = self._make_rule(
            field="severity",
            operator="==",
            value="CRITICAL",
        )
        event = {"severity": "ERROR"}
        
        result = evaluate_rule(rule, event)
        
        assert result is None

    def test_numeric_comparison_rule(self):
        """Should handle numeric comparison rules."""
        rule = self._make_rule(
            name="high_latency",
            field="latency_ms",
            operator=">",
            value="5000",
            alert_level="MEDIUM",
            message_template="High latency: {latency_ms}ms",
        )
        
        # Event with high latency - should trigger
        event_high = {"latency_ms": 6000}
        result_high = evaluate_rule(rule, event_high)
        assert result_high is not None
        assert result_high.rule_name == "high_latency"
        
        # Event with normal latency - should not trigger
        event_normal = {"latency_ms": 1000}
        result_normal = evaluate_rule(rule, event_normal)
        assert result_normal is None

    def test_missing_field_in_event(self):
        """Should not trigger when event is missing the field."""
        rule = self._make_rule(
            field="severity",
            operator="==",
            value="CRITICAL",
        )
        event = {"source": "api-gateway"}  # No severity field
        
        result = evaluate_rule(rule, event)
        
        assert result is None


# =============================================================================
# INTEGRATION-STYLE TESTS (simulating full rule evaluation)
# =============================================================================


class TestRuleEvaluationScenarios:
    """End-to-end scenarios for rule evaluation."""

    def _make_rule(self, **kwargs) -> AlertRule:
        """Helper to create a mock AlertRule with defaults."""
        defaults = {
            "name": "test_rule",
            "field": "severity",
            "operator": "==",
            "value": "CRITICAL",
            "alert_level": "HIGH",
            "message_template": "Alert triggered",
        }
        defaults.update(kwargs)
        
        rule = MagicMock(spec=AlertRule)
        for key, value in defaults.items():
            setattr(rule, key, value)
        return rule

    def test_critical_event_rule(self):
        """Test the critical_event rule behavior."""
        rule = self._make_rule(
            name="critical_event",
            field="severity",
            operator="==",
            value="CRITICAL",
            alert_level="HIGH",
            message_template="Critical event from {source}: {event_type}",
        )
        
        event = {
            "severity": "CRITICAL",
            "source": "payment-service",
            "event_type": "payment_failed",
        }
        
        result = evaluate_rule(rule, event)
        
        assert result is not None
        assert result.rule_name == "critical_event"
        assert result.level == "HIGH"
        assert result.message == "Critical event from payment-service: payment_failed"

    def test_high_latency_rule(self):
        """Test the high_latency rule behavior."""
        rule = self._make_rule(
            name="high_latency",
            field="latency_ms",
            operator=">",
            value="5000",
            alert_level="MEDIUM",
            message_template="High latency detected: {latency_ms}ms from {source}",
        )
        
        event = {
            "latency_ms": 7500,
            "source": "api-gateway",
            "event_type": "request_slow",
        }
        
        result = evaluate_rule(rule, event)
        
        assert result is not None
        assert result.rule_name == "high_latency"
        assert result.level == "MEDIUM"
        assert result.message == "High latency detected: 7500ms from api-gateway"

    def test_error_event_rule(self):
        """Test the error_event rule behavior."""
        rule = self._make_rule(
            name="error_event",
            field="severity",
            operator="==",
            value="ERROR",
            alert_level="MEDIUM",
            message_template="Error event from {source}: {event_type}",
        )
        
        event = {
            "severity": "ERROR",
            "source": "auth-service",
            "event_type": "login_failed",
        }
        
        result = evaluate_rule(rule, event)
        
        assert result is not None
        assert result.rule_name == "error_event"
        assert result.level == "MEDIUM"
        assert result.message == "Error event from auth-service: login_failed"

    def test_info_event_does_not_trigger(self):
        """INFO events should not trigger error or critical rules."""
        critical_rule = self._make_rule(
            name="critical_event",
            field="severity",
            operator="==",
            value="CRITICAL",
        )
        error_rule = self._make_rule(
            name="error_event",
            field="severity",
            operator="==",
            value="ERROR",
        )
        
        event = {"severity": "INFO", "source": "api-gateway"}
        
        assert evaluate_rule(critical_rule, event) is None
        assert evaluate_rule(error_rule, event) is None

