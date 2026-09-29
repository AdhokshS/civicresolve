from civicresolve.ui.insights import (
    build_category_summary_rows,
    build_demo_operational_insights,
)


def test_demo_insight_snapshot_detects_one_pattern():
    records, summary = (
        build_demo_operational_insights()
    )

    assert len(records) == 12

    assert (
        summary.records_evaluated
        == 10
    )

    assert (
        summary.recurring_patterns_detected
        == 1
    )


def test_primary_demo_pattern_has_expected_metrics():
    _, summary = (
        build_demo_operational_insights()
    )

    pattern = summary.patterns[0]

    assert (
        pattern.exception_count
        == 4
    )

    assert (
        pattern.affected_applications
        == 4
    )

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


def test_category_summary_represents_seven_day_window():
    records, summary = (
        build_demo_operational_insights()
    )

    rows = build_category_summary_rows(
        records,
        summary,
    )

    by_pattern = {
        row["Pattern"]: row
        for row in rows
    }

    assert (
        by_pattern[
            "Integration failure"
        ]["Exceptions"]
        == 4
    )

    assert (
        by_pattern[
            "Policy blocker"
        ]["Exceptions"]
        == 2
    )

    assert (
        by_pattern[
            "Ownership gap"
        ]["Exceptions"]
        == 2
    )

    assert (
        by_pattern[
            "Data linkage"
        ]["Exceptions"]
        == 2
    )


def test_category_summary_totals_match_records_evaluated():
    records, summary = (
        build_demo_operational_insights()
    )

    rows = build_category_summary_rows(
        records,
        summary,
    )

    total = sum(
        int(
            row["Exceptions"]
        )
        for row in rows
    )

    assert (
        total
        == summary.records_evaluated
    )