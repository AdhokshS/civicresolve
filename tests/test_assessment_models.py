import pytest
from pydantic import ValidationError

from civicresolve.models.assessment import (
    AssessmentCategory,
    ConfidenceLevel,
    ModelAssessmentDraft,
    RecommendedActionType,
    RecommendedOwnerRole,
    ValidatedAssessment,
)


def test_model_assessment_draft_accepts_bounded_action():
    assessment = ModelAssessmentDraft(
        likely_category=AssessmentCategory.SYSTEM_INTEGRATION,
        likely_cause=(
            "A failed synchronization attempt likely prevented "
            "the confirmed payment state from reaching the workflow."
        ),
        alternative_hypotheses=[
            "A delayed asynchronous update may still be pending."
        ],
        supporting_evidence_ids=[
            "EVD-PAY-88219",
            "EVD-WF-1047",
            "EVD-EVT-91372",
        ],
        conflicting_evidence_ids=[],
        missing_information=[],
        recommended_action=(
            RecommendedActionType.INVESTIGATE_INTEGRATION_SYNC
        ),
        recommended_action_rationale=(
            "Review the failed synchronization event and determine "
            "whether payment-state reconciliation should be prepared "
            "for human authorization."
        ),
        recommended_owner_role=(
            RecommendedOwnerRole.TECHNICAL_OPERATIONS
        ),
        safety_constraints=[
            "Human approval is required before workflow state changes."
        ],
    )

    assert (
        assessment.likely_category
        == AssessmentCategory.SYSTEM_INTEGRATION
    )

    assert (
        assessment.recommended_action
        == RecommendedActionType.INVESTIGATE_INTEGRATION_SYNC
    )


def test_model_assessment_rejects_invented_action():
    with pytest.raises(ValidationError):
        ModelAssessmentDraft(
            likely_category="SYSTEM_INTEGRATION",
            likely_cause="Possible synchronization failure.",
            alternative_hypotheses=[],
            supporting_evidence_ids=[
                "EVD-PAY-88219",
            ],
            conflicting_evidence_ids=[],
            missing_information=[],
            recommended_action="REFUND_PAYMENT",
            recommended_action_rationale=(
                "Refund the payment."
            ),
            recommended_owner_role="TECHNICAL_OPERATIONS",
            safety_constraints=[],
        )


def test_model_assessment_rejects_invented_category():
    with pytest.raises(ValidationError):
        ModelAssessmentDraft(
            likely_category="NETWORK_GLITCH",
            likely_cause="Possible synchronization failure.",
            alternative_hypotheses=[],
            supporting_evidence_ids=[],
            conflicting_evidence_ids=[],
            missing_information=[],
            recommended_action="ESCALATE_FOR_HUMAN_INVESTIGATION",
            recommended_action_rationale=(
                "Human investigation is required."
            ),
            recommended_owner_role="HUMAN_REVIEW",
            safety_constraints=[],
        )


def test_model_assessment_rejects_invented_owner_role():
    with pytest.raises(ValidationError):
        ModelAssessmentDraft(
            likely_category="SYSTEM_INTEGRATION",
            likely_cause="Possible synchronization failure.",
            alternative_hypotheses=[],
            supporting_evidence_ids=[],
            conflicting_evidence_ids=[],
            missing_information=[],
            recommended_action="INVESTIGATE_INTEGRATION_SYNC",
            recommended_action_rationale=(
                "Review integration logs."
            ),
            recommended_owner_role="DATABASE_ADMINISTRATOR",
            safety_constraints=[],
        )


def test_validated_assessment_contains_system_confidence():
    assessment = ValidatedAssessment(
        likely_category=AssessmentCategory.SYSTEM_INTEGRATION,
        likely_cause=(
            "A failed synchronization attempt likely prevented "
            "the confirmed payment state from reaching the workflow."
        ),
        alternative_hypotheses=[],
        supporting_evidence_ids=[
            "EVD-PAY-88219",
            "EVD-WF-1047",
            "EVD-EVT-91372",
        ],
        conflicting_evidence_ids=[],
        missing_information=[],
        recommended_action=(
            RecommendedActionType.INVESTIGATE_INTEGRATION_SYNC
        ),
        recommended_action_rationale=(
            "Review the integration failure before preparing "
            "any workflow reconciliation."
        ),
        recommended_owner_role=(
            RecommendedOwnerRole.TECHNICAL_OPERATIONS
        ),
        safety_constraints=[
            "Human authorization is required."
        ],
        confidence=ConfidenceLevel.HIGH,
        confidence_basis=[
            "A deterministic state mismatch was detected.",
            "A failed integration event corroborates the mismatch.",
            "No conflicting evidence is present.",
        ],
        validation_warnings=[],
        human_approval_required=True,
    )

    assert assessment.confidence == ConfidenceLevel.HIGH

    assert assessment.human_approval_required is True