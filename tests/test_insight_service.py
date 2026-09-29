from datetime import UTC, datetime

from civicresolve.data.insight_history import (
    build_historical_exception_records,
)
from civicresolve.models.rule import (
    RuleCategory,
)
from civicresolve.services.insight_service import (
    detect_recurring_patterns,
)

AS_OF = datetime(
    2026,
    9,
    29,
    0,
    0,
    tzinfo=UTC,
)


def test_history_contains_synthetic_records():
    records = (
        build_historical_exception_records()
    )

    assert len(records) == 12

    assert all(
        record.synthetic
        for record in records
    )


def test_detects_recurring_integration_pattern():
    summary = detect_recurring_patterns(
        build_historical_exception_records(),
        as_of=AS_OF,
        window_days=7,
        minimum_occurrences=3,
    )

    assert (
        summary.recurring_patterns_detected
        == 1
    )

    pattern = summary.patterns[0]

    assert (
        pattern.category
        == RuleCategory.SYSTEM_INTEGRATION
    )

    assert (
        pattern.rule_id
        == "RULE-PAY-001"
    )

    assert (
        pattern.exception_count
        == 4
    )

    assert (
        pattern.affected_applications
        == 4
    )


def test_pattern_resolution_metrics_are_deterministic():
    summary = detect_recurring_patterns(
        build_historical_exception_records(),
        as_of=AS_OF,
        window_days=7,
        minimum_occurrences=3,
    )

    pattern = summary.patterns[0]

    assert (
        pattern.resolved_count
        == 3
    )

    assert (
        pattern.open_count
        == 1
    )

    assert (
        pattern.median_resolution_minutes
        == 55.0
    )


def test_two_occurrences_do_not_create_pattern():
    summary = detect_recurring_patterns(
        build_historical_exception_records(),
        as_of=AS_OF,
        window_days=7,
        minimum_occurrences=3,
    )

    rule_ids = {
        pattern.rule_id
        for pattern in summary.patterns
    }

    assert (
        "RULE-POL-001"
        not in rule_ids
    )

    assert (
        "RULE-OWN-001"
        not in rule_ids
    )

    assert (
        "RULE-DATA-001"
        not in rule_ids
    )


def test_old_records_are_outside_seven_day_window():
    summary = detect_recurring_patterns(
        build_historical_exception_records(),
        as_of=AS_OF,
        window_days=7,
        minimum_occurrences=1,
    )

    integration_pattern = next(
        pattern
        for pattern in summary.patterns
        if pattern.rule_id
        == "RULE-PAY-001"
    )

    assert (
        integration_pattern.exception_count
        == 4
    )

    assert (
        "HIST-011"
        not in integration_pattern
        .evidence_record_ids
    )


def test_insight_states_root_cause_limitation():
    summary = detect_recurring_patterns(
        build_historical_exception_records(),
        as_of=AS_OF,
        window_days=7,
        minimum_occurrences=3,
    )

    pattern = summary.patterns[0]

    assert (
        "does not prove"
        in pattern.limitation
    )

    assert (
        "same"
        in pattern.limitation
    )


def test_summary_is_explicitly_synthetic():
    summary = detect_recurring_patterns(
        build_historical_exception_records(),
        as_of=AS_OF,
    )

    assert summary.synthetic is True

    assert all(
        pattern.synthetic
        for pattern in summary.patterns
    )