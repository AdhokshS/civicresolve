from __future__ import annotations

from enum import Enum

from pydantic import Field

from civicresolve.models.case import StrictModel


class AssessmentCategory(str, Enum):
    SYSTEM_INTEGRATION = "SYSTEM_INTEGRATION"
    POLICY = "POLICY"
    OWNERSHIP_PROCESS = "OWNERSHIP_PROCESS"
    DATA = "DATA"
    AMBIGUOUS = "AMBIGUOUS"


class RecommendedActionType(str, Enum):
    """
    Bounded action families that the AI may recommend for human review.

    These are recommendations only. None of them execute automatically.
    """

    INVESTIGATE_INTEGRATION_SYNC = (
        "INVESTIGATE_INTEGRATION_SYNC"
    )

    PREPARE_PAYMENT_STATE_RECONCILIATION = (
        "PREPARE_PAYMENT_STATE_RECONCILIATION"
    )

    REQUEST_UPDATED_DOCUMENT = (
        "REQUEST_UPDATED_DOCUMENT"
    )

    ROUTE_FOR_OWNER_ASSIGNMENT = (
        "ROUTE_FOR_OWNER_ASSIGNMENT"
    )

    RECONCILE_PAYMENT_REFERENCE = (
        "RECONCILE_PAYMENT_REFERENCE"
    )

    ESCALATE_FOR_HUMAN_INVESTIGATION = (
        "ESCALATE_FOR_HUMAN_INVESTIGATION"
    )

    NO_ACTION = "NO_ACTION"


class RecommendedOwnerRole(str, Enum):
    """
    Operational role families that can receive a recommended next step.

    These represent synthetic demo roles, not Neumo organizational roles.
    """

    LICENSING_OPERATIONS = "LICENSING_OPERATIONS"

    LICENSING_SUPERVISOR = "LICENSING_SUPERVISOR"

    APPLICANT_SERVICES = "APPLICANT_SERVICES"

    REVENUE_OPERATIONS = "REVENUE_OPERATIONS"

    PAYMENT_RECONCILIATION = "PAYMENT_RECONCILIATION"

    TECHNICAL_OPERATIONS = "TECHNICAL_OPERATIONS"

    HUMAN_REVIEW = "HUMAN_REVIEW"


class ModelAssessmentDraft(StrictModel):
    """
    Structured output that the local AI model is allowed to produce.

    This object is not yet an approved recommendation.

    CivicResolve must validate evidence references, action compatibility,
    and safety constraints before the draft can be presented to a human
    reviewer as a validated assessment.
    """

    likely_category: AssessmentCategory

    likely_cause: str

    alternative_hypotheses: list[str] = Field(
        default_factory=list
    )

    supporting_evidence_ids: list[str] = Field(
        default_factory=list
    )

    conflicting_evidence_ids: list[str] = Field(
        default_factory=list
    )

    missing_information: list[str] = Field(
        default_factory=list
    )

    recommended_action: RecommendedActionType

    recommended_action_rationale: str

    recommended_owner_role: RecommendedOwnerRole

    safety_constraints: list[str] = Field(
        default_factory=list
    )


class ConfidenceLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ValidatedAssessment(StrictModel):
    """
    CivicResolve assessment after deterministic post-model validation.

    Confidence is a system-calculated value rather than a free-form
    probability invented by the language model.
    """

    likely_category: AssessmentCategory

    likely_cause: str

    alternative_hypotheses: list[str] = Field(
        default_factory=list
    )

    supporting_evidence_ids: list[str] = Field(
        default_factory=list
    )

    conflicting_evidence_ids: list[str] = Field(
        default_factory=list
    )

    missing_information: list[str] = Field(
        default_factory=list
    )

    recommended_action: RecommendedActionType

    recommended_action_rationale: str

    recommended_owner_role: RecommendedOwnerRole

    safety_constraints: list[str] = Field(
        default_factory=list
    )

    confidence: ConfidenceLevel

    confidence_basis: list[str] = Field(
        default_factory=list
    )

    validation_warnings: list[str] = Field(
        default_factory=list
    )

    human_approval_required: bool = True