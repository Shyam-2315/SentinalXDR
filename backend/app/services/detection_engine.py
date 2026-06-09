import re
from datetime import UTC, datetime
from typing import Any

from app.models.alert import Alert
from app.models.detection import ConditionOperator, DetectionResult, DetectionRule
from app.models.event import Event
from app.repositories.alerts import AlertRepository
from app.repositories.detections import DetectionResultRepository, DetectionRuleRepository


def validate_rule_conditions(conditions: dict[str, Any]) -> None:
    all_conditions = conditions.get("all")
    if not isinstance(all_conditions, list) or not all_conditions:
        raise ValueError("conditions must include a non-empty 'all' list")

    for condition in all_conditions:
        if not isinstance(condition, dict):
            raise ValueError("each condition must be an object")
        field = condition.get("field")
        operator = condition.get("operator")
        if not isinstance(field, str) or not field:
            raise ValueError("condition field must be a non-empty string")
        if operator not in {item.value for item in ConditionOperator}:
            raise ValueError("condition operator is not supported")
        if "value" not in condition:
            raise ValueError("condition value is required")
        if operator == ConditionOperator.REGEX:
            try:
                re.compile(str(condition["value"]))
            except re.error as exc:
                raise ValueError("condition regex is invalid") from exc
        if operator == ConditionOperator.IN and not isinstance(condition["value"], list):
            raise ValueError("'in' condition value must be a list")


def get_field_value(event: Event, field_path: str) -> Any:
    parts = field_path.split(".")
    if not parts:
        return None

    if parts[0] == "raw_event":
        current: Any = event.raw_event
        parts = parts[1:]
    elif parts[0] == "normalized_fields":
        current = event.normalized_fields
        parts = parts[1:]
    else:
        return None

    for part in parts:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def compare_value(actual: Any, operator: str, expected: Any) -> bool:
    if actual is None:
        return False

    if operator == ConditionOperator.EQUALS:
        return actual == expected
    if operator == ConditionOperator.CONTAINS:
        return str(expected).lower() in str(actual).lower()
    if operator == ConditionOperator.REGEX:
        try:
            return re.search(str(expected), str(actual), flags=re.IGNORECASE) is not None
        except re.error:
            return False
    if operator == ConditionOperator.IN:
        return actual in expected if isinstance(expected, list) else False

    try:
        actual_number = float(actual)
        expected_number = float(expected)
    except (TypeError, ValueError):
        return False

    if operator == ConditionOperator.GT:
        return actual_number > expected_number
    if operator == ConditionOperator.GTE:
        return actual_number >= expected_number
    if operator == ConditionOperator.LT:
        return actual_number < expected_number
    if operator == ConditionOperator.LTE:
        return actual_number <= expected_number
    return False


def match_rule(event: Event, rule: DetectionRule) -> dict[str, Any] | None:
    if not rule.enabled or event.source != rule.source or event.event_type != rule.event_type:
        return None

    try:
        validate_rule_conditions(rule.conditions)
    except ValueError:
        return None

    matched_fields: dict[str, Any] = {}
    for condition in rule.conditions["all"]:
        field = condition["field"]
        actual = get_field_value(event, field)
        if not compare_value(actual, condition["operator"], condition["value"]):
            return None
        matched_fields[field] = actual
    return matched_fields


class DetectionEngine:
    def __init__(
        self,
        rules: DetectionRuleRepository,
        results: DetectionResultRepository,
        alerts: AlertRepository,
    ) -> None:
        self.rules = rules
        self.results = results
        self.alerts = alerts

    async def evaluate_events(
        self,
        events: list[Event],
    ) -> tuple[list[DetectionResult], list[Alert]]:
        created_results: list[DetectionResult] = []
        created_alerts: list[Alert] = []
        for event in events:
            rules = await self.rules.list_enabled_for_organization(event.organization_id)
            for rule in rules:
                matched_fields = match_rule(event, rule)
                if matched_fields is None:
                    continue
                result = await self.results.create(
                    event=event,
                    rule=rule,
                    matched_fields=matched_fields,
                )
                alert = await self.alerts.create_from_detection_result(result, tags=rule.tags)
                created_results.append(result)
                created_alerts.append(alert)
        return created_results, created_alerts


def now_utc() -> datetime:
    return datetime.now(UTC)
