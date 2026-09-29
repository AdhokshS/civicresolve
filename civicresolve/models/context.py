from __future__ import annotations

from pydantic import AwareDatetime, Field

from civicresolve.models.case import (
    CaseSeverity,
    CaseStatus,
    StrictModel,
    WorkflowPaymentState,
    WorkflowStage,
)
from civicresolve.models.evidence import (
    EvidenceItem,
    EvidenceReference,
)
from civicresolve.models.rule import RuleFinding


class CaseIdentity(StrictModel):
    """
    Stable identity information for an investigation context.
    """

    case_id: str
    application_id: str

    business_name: str
    license_type: str

    synthetic: bool = True


class WorkflowContext(StrictModel):
    """
    Deterministic representation of where the case currently sits
    in the expected licensing workflow.
    """

    expected_path: list[WorkflowStage] = Field(default_factory=list)

    stages_reached: list[WorkflowStage] = Field(default_factory=list)

    current_stage: WorkflowStage

    expected_next_stage: WorkflowStage | None = None

    payment_state: WorkflowPaymentState

    assigned_team: str | None = None
    assigned_role: str | None = None


class ConfirmedFact(StrictModel):
    """
    A factual statement derived directly from structured source records.

    Confirmed facts must cite the evidence record that supports them.
    """

    fact_id: str
    statement: str

    evidence: list[EvidenceReference] = Field(default_factory=list)


class TimelineEntry(StrictModel):
    """
    One observable event in the reconstructed case timeline.
    """

    event_id: str
    evidence_id: str

    occurred_at: AwareDatetime

    source_system: str
    event_type: str

    success: bool

    summary: str


class InvestigationContext(StrictModel):
    """
    Structured investigation packet used by CivicResolve.

    This is the boundary between deterministic context reconstruction
    and future AI-assisted reasoning.
    """

    context_version: str = "1.0"

    generated_at: AwareDatetime

    identity: CaseIdentity

    case_status: CaseStatus
    severity: CaseSeverity

    workflow: WorkflowContext

    confirmed_facts: list[ConfirmedFact] = Field(
        default_factory=list
    )

    deterministic_findings: list[RuleFinding] = Field(
        default_factory=list
    )

    evaluated_rule_count: int

    timeline: list[TimelineEntry] = Field(
        default_factory=list
    )

    evidence_catalog: list[EvidenceItem] = Field(
        default_factory=list
    )