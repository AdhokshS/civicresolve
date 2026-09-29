from civicresolve.data.scenarios import (
    build_integration_exception_case,
)
from civicresolve.models.assessment import (
    AssessmentCategory,
    ConfidenceLevel,
    ModelAssessmentDraft,
    RecommendedActionType,
    RecommendedOwnerRole,
)
from civicresolve.rules.engine import run_rule_engine
from civicresolve.services.assessment_validation_service import (
    validate_model_assessment,
)
from civicresolve.services.context_service import (
    build_investigation_context,
)
from civicresolve.services.evidence_service import (
    build_evidence_bundle,
)
from civicresolve.services.reasoning_service import (
    build_reasoning_packet,
)


def _build_packet():
    case = build_integration_exception_case()

    evidence = build_evidence_bundle(case)

    rules = run_rule_engine(
        case,
        evidence,
    )

    context = build_investigation_context(
        case,
        evidence,
        rules,
    )

    return build_reasoning_packet(context)


def _build_valid_draft():
    return ModelAssessmentDraft(
        likely_category=(
            AssessmentCategory.SYSTEM_INTEGRATION
        ),
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
            "Review the failed synchronization event and determine "
            "whether reconciliation preparation is appropriate "
            "for human review."
        ),
        recommended_owner_role=(
            RecommendedOwnerRole.TECHNICAL_OPERATIONS
        ),
        safety_constraints=[
            (
                "Human authorization is required before any "
                "workflow state change."
            )
        ],
    )


def test_valid_grounded_assessment_passes():
    result = validate_model_assessment(
        _build_packet(),
        _build_valid_draft(),
    )

    assert result.is_valid is True
    assert result.assessment is not None

    assert (
        result.assessment.confidence
        == ConfidenceLevel.HIGH
    )


def test_missing_supporting_evidence_fails_closed():
    draft = _build_valid_draft().model_copy(
        update={
            "supporting_evidence_ids": [],
        }
    )

    result = validate_model_assessment(
        _build_packet(),
        draft,
    )

    assert result.is_valid is False
    assert result.assessment is None

    assert any(
        issue.code
        == "MISSING_SUPPORTING_EVIDENCE"
        for issue in result.issues
    )


def test_unknown_evidence_reference_fails_closed():
    draft = _build_valid_draft().model_copy(
        update={
            "supporting_evidence_ids": [
                "EVD-PAY-88219",
                "EVD-WF-1047",
                "EVD-NOT-REAL",
            ]
        }
    )

    result = validate_model_assessment(
        _build_packet(),
        draft,
    )

    assert result.is_valid is False

    assert any(
        issue.code
        == "UNKNOWN_EVIDENCE_REFERENCE"
        for issue in result.issues
    )


def test_category_conflict_fails_closed():
    draft = _build_valid_draft().model_copy(
        update={
            "likely_category": AssessmentCategory.POLICY,
            "recommended_action": (
                RecommendedActionType.REQUEST_UPDATED_DOCUMENT
            ),
            "recommended_owner_role": (
                RecommendedOwnerRole.APPLICANT_SERVICES
            ),
        }
    )

    result = validate_model_assessment(
        _build_packet(),
        draft,
    )

    assert result.is_valid is False

    assert any(
        issue.code == "CATEGORY_CONFLICT"
        for issue in result.issues
    )


def test_incompatible_action_fails_closed():
    draft = _build_valid_draft().model_copy(
        update={
            "recommended_action": (
                RecommendedActionType.REQUEST_UPDATED_DOCUMENT
            ),
            "recommended_owner_role": (
                RecommendedOwnerRole.APPLICANT_SERVICES
            ),
        }
    )

    result = validate_model_assessment(
        _build_packet(),
        draft,
    )

    assert result.is_valid is False

    assert any(
        issue.code == "INCOMPATIBLE_ACTION"
        for issue in result.issues
    )


def test_incompatible_owner_fails_closed():
    draft = _build_valid_draft().model_copy(
        update={
            "recommended_owner_role": (
                RecommendedOwnerRole.APPLICANT_SERVICES
            ),
        }
    )

    result = validate_model_assessment(
        _build_packet(),
        draft,
    )

    assert result.is_valid is False

    assert any(
        issue.code == "INCOMPATIBLE_OWNER"
        for issue in result.issues
    )


def test_prohibited_directive_language_fails_closed():
    draft = _build_valid_draft().model_copy(
        update={
            "recommended_action_rationale": (
                "Review the logs and then manually update the "
                "workflow state."
            ),
        }
    )

    result = validate_model_assessment(
        _build_packet(),
        draft,
    )

    assert result.is_valid is False

    assert any(
        issue.code
        == "PROHIBITED_ACTION_LANGUAGE"
        for issue in result.issues
    )


def test_conflicting_evidence_reduces_confidence():
    draft = _build_valid_draft().model_copy(
        update={
            "conflicting_evidence_ids": [
                "EVD-EVT-91373",
            ],
        }
    )

    result = validate_model_assessment(
        _build_packet(),
        draft,
    )

    assert result.is_valid is True
    assert result.assessment is not None

    assert (
        result.assessment.confidence
        == ConfidenceLevel.LOW
    )