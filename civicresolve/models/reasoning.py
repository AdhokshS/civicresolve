from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import AwareDatetime, Field

from civicresolve.models.case import StrictModel
from civicresolve.models.rule import (
    RuleCategory,
    RuleSeverity,
)


class ConfidenceLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ReasoningFact(StrictModel):
    """
    Confirmed factual statement supplied to the AI reasoning layer.

    Facts are already grounded in source evidence before the model
    receives them.
    """

    fact_id: str
    statement: str

    evidence_ids: list[str] = Field(
        default_factory=list
    )


class ReasoningFinding(StrictModel):
    """
    Deterministic finding supplied to the AI.

    The model must treat this as an observed rule result rather than
    reinterpret it as unquestioned root-cause certainty.
    """

    finding_code: str

    category: RuleCategory
    severity: RuleSeverity

    observed_condition: str
    limitation: str

    evidence_ids: list[str] = Field(
        default_factory=list
    )


class ReasoningTimelineEntry(StrictModel):
    """
    Chronological event supplied to the AI reasoning layer.
    """

    occurred_at: AwareDatetime

    event_type: str
    source_system: str

    success: bool
    summary: str

    evidence_id: str


class ReasoningEvidence(StrictModel):
    """
    Reduced evidence representation exposed to the AI.

    Only fields already normalized by CivicResolve are included.
    """

    evidence_id: str

    source_system: str
    evidence_type: str

    summary: str

    fields: dict[str, Any] = Field(
        default_factory=dict
    )


class ReasoningGuardrails(StrictModel):
    """
    Explicit behavioral boundaries for AI-assisted reasoning.
    """

    human_approval_required: bool = True

    may_make_final_government_decision: bool = False
    may_bypass_policy: bool = False
    may_execute_workflow_action: bool = False
    may_reassign_payment: bool = False

    prohibited_actions: list[str] = Field(
        default_factory=list
    )

    required_behaviors: list[str] = Field(
        default_factory=list
    )


class ReasoningTask(StrictModel):
    """
    The bounded analytical task supplied to the AI.
    """

    objective: str

    questions: list[str] = Field(
        default_factory=list
    )

    permitted_outputs: list[str] = Field(
        default_factory=list
    )


class ReasoningPacket(StrictModel):
    """
    Controlled input packet for CivicResolve's future local AI model.

    This packet intentionally excludes unnecessary applicant identity
    information and contains only the context required for exception
    investigation.
    """

    packet_version: str = "1.0"

    case_id: str
    application_id: str

    current_stage: str
    expected_next_stage: str | None

    confirmed_facts: list[ReasoningFact] = Field(
        default_factory=list
    )

    deterministic_findings: list[ReasoningFinding] = Field(
        default_factory=list
    )

    timeline: list[ReasoningTimelineEntry] = Field(
        default_factory=list
    )

    evidence: list[ReasoningEvidence] = Field(
        default_factory=list
    )

    task: ReasoningTask

    guardrails: ReasoningGuardrails