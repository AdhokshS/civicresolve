from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd
import streamlit as st

from civicresolve.data.insight_history import (
    build_historical_exception_records,
)
from civicresolve.models.insight import (
    HistoricalExceptionRecord,
    OperationalInsightSummary,
)
from civicresolve.services.insight_service import (
    detect_recurring_patterns,
)

DEMO_INSIGHTS_AS_OF = datetime(
    2026,
    9,
    29,
    0,
    0,
    tzinfo=UTC,
)

DEMO_WINDOW_DAYS = 7

DEMO_MINIMUM_OCCURRENCES = 3


CATEGORY_LABELS = {
    "SYSTEM_INTEGRATION": "Integration failure",
    "POLICY": "Policy blocker",
    "OWNERSHIP_PROCESS": "Ownership gap",
    "DATA": "Data linkage",
}


def category_label(
    category: str,
) -> str:
    return CATEGORY_LABELS.get(
        category,
        category.replace(
            "_",
            " ",
        ).title(),
    )


def build_demo_operational_insights(
) -> tuple[
    list[HistoricalExceptionRecord],
    OperationalInsightSummary,
]:
    """
    Build the deterministic synthetic operational-insight snapshot
    used by the CivicResolve demonstration.
    """

    records = (
        build_historical_exception_records()
    )

    summary = detect_recurring_patterns(
        records,
        as_of=DEMO_INSIGHTS_AS_OF,
        window_days=DEMO_WINDOW_DAYS,
        minimum_occurrences=(
            DEMO_MINIMUM_OCCURRENCES
        ),
    )

    return records, summary


def build_category_summary_rows(
    records: list[HistoricalExceptionRecord],
    summary: OperationalInsightSummary,
) -> list[dict[str, object]]:
    """
    Build portfolio-level category counts for the insight window.
    """

    window_start = (
        summary.as_of
        - timedelta(
            days=summary.window_days
        )
    )

    window_records = [
        record
        for record in records
        if (
            window_start
            <= record.occurred_at
            <= summary.as_of
        )
    ]

    grouped: dict[
        str,
        dict[str, object],
    ] = {}

    for record in window_records:
        category = record.category.value

        if category not in grouped:
            grouped[category] = {
                "Pattern": (
                    category_label(
                        category
                    )
                ),
                "Exceptions": 0,
                "Open": 0,
                "Resolved": 0,
            }

        grouped[
            category
        ]["Exceptions"] = (
            int(
                grouped[
                    category
                ]["Exceptions"]
            )
            + 1
        )

        if (
            record.resolution_status.value
            == "OPEN"
        ):
            grouped[
                category
            ]["Open"] = (
                int(
                    grouped[
                        category
                    ]["Open"]
                )
                + 1
            )

        else:
            grouped[
                category
            ]["Resolved"] = (
                int(
                    grouped[
                        category
                    ]["Resolved"]
                )
                + 1
            )

    rows = list(
        grouped.values()
    )

    rows.sort(
        key=lambda row: (
            -int(
                row["Exceptions"]
            ),
            str(
                row["Pattern"]
            ),
        )
    )

    return rows


def render_operational_insights_panel(
) -> None:
    """
    Render the CivicResolve portfolio-level recurring-pattern view.

    The calculation is deterministic and uses synthetic history.
    """

    records, summary = (
        build_demo_operational_insights()
    )

    st.markdown(
        "## Operational signal"
    )

    st.caption(
        "CivicResolve can use resolved case history to surface "
        "repeat exception patterns without asking AI to invent trends."
    )

    if not summary.patterns:
        st.info(
            "No recurring exception pattern met the "
            "configured demonstration threshold."
        )
        return

    primary = summary.patterns[0]

    st.warning(
        
            f"{primary.title}: "
            f"{primary.exception_count} occurrences across "
            f"{primary.affected_applications} applications "
            f"in the last {primary.window_days} days."
        
    )

    metric_1, metric_2, metric_3, metric_4 = (
        st.columns(4)
    )

    metric_1.metric(
        "Occurrences",
        primary.exception_count,
    )

    metric_2.metric(
        "Affected applications",
        primary.affected_applications,
    )

    metric_3.metric(
        "Still open",
        primary.open_count,
    )

    resolution_value = (
        f"{primary.median_resolution_minutes:.0f} min"
        if (
            primary.median_resolution_minutes
            is not None
        )
        else "—"
    )

    metric_4.metric(
        "Median resolution",
        resolution_value,
    )

    with st.expander(
        "Inspect the 7-day operational pattern",
        expanded=False,
    ):
        st.markdown(
            "### Detected recurring pattern"
        )

        st.write(
            primary.description
        )

        st.markdown(
            "**Detection basis**"
        )

        st.write(
            
                f"The same deterministic rule "
                f"`{primary.rule_id}` was observed "
                f"{primary.exception_count} times inside the "
                f"{primary.window_days}-day analysis window."
            
        )

        st.markdown(
            "**Affected synthetic records**"
        )

        st.code(
            "\n".join(
                primary.evidence_record_ids
            ),
            language=None,
        )

        st.markdown(
            "### Exception distribution"
        )

        category_rows = (
            build_category_summary_rows(
                records,
                summary,
            )
        )

        st.dataframe(
            pd.DataFrame(
                category_rows
            ),
            use_container_width=True,
            hide_index=True,
        )

        st.markdown(
            "### Operational next question"
        )

        st.write(
            "Compare the affected payment/workflow cases to determine "
            "whether they share a common failure mechanism before "
            "changing automation, retry, or reconciliation behavior."
        )

        st.info(
            primary.limitation
        )

        st.caption(
            "Synthetic demonstration history only. "
            "These counts are not Neumo, agency, customer, "
            "or production performance metrics."
        )