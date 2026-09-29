from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from statistics import median

from civicresolve.models.insight import (
    HistoricalExceptionRecord,
    HistoricalResolutionStatus,
    OperationalInsightSummary,
    RecurringPatternInsight,
)

PATTERN_TITLES = {
    "RULE-PAY-001": (
        "Recurring payment/workflow synchronization mismatch"
    ),
    "RULE-POL-001": (
        "Recurring required-document policy blocker"
    ),
    "RULE-OWN-001": (
        "Recurring workflow ownership gap"
    ),
    "RULE-DATA-001": (
        "Recurring payment/application reference mismatch"
    ),
}


PATTERN_DESCRIPTIONS = {
    "RULE-PAY-001": (
        "Multiple applications show successful payment records while "
        "the licensing workflow remains at the payment stage."
    ),
    "RULE-POL-001": (
        "Multiple applications are blocked by a required-document "
        "policy condition."
    ),
    "RULE-OWN-001": (
        "Multiple applications reach a workflow stage without an "
        "accountable downstream owner."
    ),
    "RULE-DATA-001": (
        "Multiple payment records contain application references "
        "that do not match the investigated application."
    ),
}


PATTERN_LIMITATION = (
    "Recurrence establishes an operational pattern only. "
    "It does not prove that every occurrence shares the same "
    "technical, policy, process, or data root cause."
)


def _normalize_as_of(
    as_of: datetime,
) -> datetime:
    if as_of.tzinfo is None:
        return as_of.replace(
            tzinfo=UTC
        )

    return as_of.astimezone(
        UTC
    )


def detect_recurring_patterns(
    records: list[HistoricalExceptionRecord],
    *,
    as_of: datetime,
    window_days: int = 7,
    minimum_occurrences: int = 3,
) -> OperationalInsightSummary:
    """
    Deterministically detect recurring exception-rule patterns.

    No language model is used in this calculation.
    """

    normalized_as_of = _normalize_as_of(
        as_of
    )

    window_start = (
        normalized_as_of
        - timedelta(
            days=window_days
        )
    )

    in_window = [
        record
        for record in records
        if (
            window_start
            <= record.occurred_at
            <= normalized_as_of
        )
    ]

    grouped: dict[
        tuple[str, str],
        list[HistoricalExceptionRecord],
    ] = defaultdict(list)

    for record in in_window:
        grouped[
            (
                record.category.value,
                record.rule_id,
            )
        ].append(
            record
        )

    patterns: list[
        RecurringPatternInsight
    ] = []

    for (
        _category_value,
        rule_id,
    ), group in grouped.items():
        if len(group) < minimum_occurrences:
            continue

        ordered = sorted(
            group,
            key=lambda item: (
                item.occurred_at
            ),
        )

        resolution_values = [
            record.resolution_minutes
            for record in ordered
            if (
                record.resolution_minutes
                is not None
            )
        ]

        median_resolution = (
            float(
                median(
                    resolution_values
                )
            )
            if resolution_values
            else None
        )

        resolved_count = sum(
            1
            for record in ordered
            if (
                record.resolution_status
                == HistoricalResolutionStatus.RESOLVED
            )
        )

        open_count = (
            len(ordered)
            - resolved_count
        )

        patterns.append(
            RecurringPatternInsight(
                insight_id=(
                    "INSIGHT-"
                    f"{rule_id}-"
                    f"{window_days}D"
                ),
                category=ordered[0].category,
                rule_id=rule_id,
                title=PATTERN_TITLES.get(
                    rule_id,
                    (
                        "Recurring operational "
                        "exception pattern"
                    ),
                ),
                description=(
                    PATTERN_DESCRIPTIONS.get(
                        rule_id,
                        (
                            "Multiple exceptions matched "
                            "the same deterministic rule."
                        ),
                    )
                ),
                window_days=window_days,
                exception_count=len(
                    ordered
                ),
                affected_applications=len(
                    {
                        record.application_id
                        for record in ordered
                    }
                ),
                resolved_count=resolved_count,
                open_count=open_count,
                median_resolution_minutes=(
                    median_resolution
                ),
                first_observed_at=(
                    ordered[0].occurred_at
                ),
                last_observed_at=(
                    ordered[-1].occurred_at
                ),
                evidence_record_ids=[
                    record.record_id
                    for record in ordered
                ],
                limitation=(
                    PATTERN_LIMITATION
                ),
                synthetic=True,
            )
        )

    patterns.sort(
        key=lambda pattern: (
            -pattern.exception_count,
            pattern.rule_id,
        )
    )

    return OperationalInsightSummary(
        as_of=normalized_as_of,
        window_days=window_days,
        records_evaluated=len(
            in_window
        ),
        recurring_patterns_detected=len(
            patterns
        ),
        patterns=patterns,
        synthetic=True,
    )