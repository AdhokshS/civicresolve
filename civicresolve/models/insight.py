from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field

from civicresolve.models.case import (
    StrictModel,
    WorkflowStage,
)
from civicresolve.models.rule import (
    RuleCategory,
    RuleSeverity,
)


class HistoricalResolutionStatus(str, Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"


class HistoricalExceptionRecord(StrictModel):
    """
    Synthetic historical exception occurrence used only for
    operational-pattern demonstration.
    """

    record_id: str

    case_id: str
    application_id: str

    occurred_at: datetime

    category: RuleCategory
    rule_id: str

    severity: RuleSeverity

    workflow_stage: WorkflowStage

    resolution_status: HistoricalResolutionStatus

    resolution_minutes: int | None = Field(
        default=None,
        ge=0,
    )

    synthetic: bool = True


class RecurringPatternInsight(StrictModel):
    """
    Deterministically detected recurring operational pattern.

    Frequency establishes recurrence only. It does not establish
    that every occurrence has the same root cause.
    """

    insight_id: str

    category: RuleCategory
    rule_id: str

    title: str
    description: str

    window_days: int = Field(
        ge=1
    )

    exception_count: int = Field(
        ge=1
    )

    affected_applications: int = Field(
        ge=1
    )

    resolved_count: int = Field(
        ge=0
    )

    open_count: int = Field(
        ge=0
    )

    median_resolution_minutes: float | None = None

    first_observed_at: datetime
    last_observed_at: datetime

    evidence_record_ids: list[str] = Field(
        default_factory=list
    )

    limitation: str

    synthetic: bool = True


class OperationalInsightSummary(StrictModel):
    as_of: datetime

    window_days: int = Field(
        ge=1
    )

    records_evaluated: int = Field(
        ge=0
    )

    recurring_patterns_detected: int = Field(
        ge=0
    )

    patterns: list[RecurringPatternInsight] = Field(
        default_factory=list
    )

    synthetic: bool = True