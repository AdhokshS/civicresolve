from __future__ import annotations

from collections.abc import Iterable
from enum import Enum

from civicresolve.models.assessment import (
    AssessmentCategory,
    ConfidenceLevel,
    ModelAssessmentDraft,
    RecommendedActionType,
    RecommendedOwnerRole,
    ValidatedAssessment,
)
from civicresolve.models.reasoning import ReasoningPacket
from civicresolve.models.validation import (
    AssessmentValidationIssue,
    AssessmentValidationResult,
    ValidationSeverity,
)

CATEGORY_ACTIONS = {
    AssessmentCategory.SYSTEM_INTEGRATION: {
        RecommendedActionType.INVESTIGATE_INTEGRATION_SYNC,
        RecommendedActionType.PREPARE_PAYMENT_STATE_RECONCILIATION,
        RecommendedActionType.ESCALATE_FOR_HUMAN_INVESTIGATION,
        RecommendedActionType.NO_ACTION,
    },
    AssessmentCategory.POLICY: {
        RecommendedActionType.REQUEST_UPDATED_DOCUMENT,
        RecommendedActionType.ESCALATE_FOR_HUMAN_INVESTIGATION,
        RecommendedActionType.NO_ACTION,
    },
    AssessmentCategory.OWNERSHIP_PROCESS: {
        RecommendedActionType.ROUTE_FOR_OWNER_ASSIGNMENT,
        RecommendedActionType.ESCALATE_FOR_HUMAN_INVESTIGATION,
        RecommendedActionType.NO_ACTION,
    },
    AssessmentCategory.DATA: {
        RecommendedActionType.RECONCILE_PAYMENT_REFERENCE,
        RecommendedActionType.ESCALATE_FOR_HUMAN_INVESTIGATION,
        RecommendedActionType.NO_ACTION,
    },
    AssessmentCategory.AMBIGUOUS: {
        RecommendedActionType.ESCALATE_FOR_HUMAN_INVESTIGATION,
        RecommendedActionType.NO_ACTION,
    },
}


ACTION_OWNERS = {
    RecommendedActionType.INVESTIGATE_INTEGRATION_SYNC: {
        RecommendedOwnerRole.TECHNICAL_OPERATIONS,
        RecommendedOwnerRole.LICENSING_OPERATIONS,
        RecommendedOwnerRole.HUMAN_REVIEW,
    },
    RecommendedActionType.PREPARE_PAYMENT_STATE_RECONCILIATION: {
        RecommendedOwnerRole.PAYMENT_RECONCILIATION,
        RecommendedOwnerRole.REVENUE_OPERATIONS,
        RecommendedOwnerRole.LICENSING_OPERATIONS,
        RecommendedOwnerRole.HUMAN_REVIEW,
    },
    RecommendedActionType.REQUEST_UPDATED_DOCUMENT: {
        RecommendedOwnerRole.APPLICANT_SERVICES,
        RecommendedOwnerRole.LICENSING_OPERATIONS,
        RecommendedOwnerRole.HUMAN_REVIEW,
    },
    RecommendedActionType.ROUTE_FOR_OWNER_ASSIGNMENT: {
        RecommendedOwnerRole.LICENSING_SUPERVISOR,
        RecommendedOwnerRole.LICENSING_OPERATIONS,
        RecommendedOwnerRole.HUMAN_REVIEW,
    },
    RecommendedActionType.RECONCILE_PAYMENT_REFERENCE: {
        RecommendedOwnerRole.PAYMENT_RECONCILIATION,
        RecommendedOwnerRole.REVENUE_OPERATIONS,
        RecommendedOwnerRole.HUMAN_REVIEW,
    },
    RecommendedActionType.ESCALATE_FOR_HUMAN_INVESTIGATION: {
        RecommendedOwnerRole.LICENSING_OPERATIONS,
        RecommendedOwnerRole.LICENSING_SUPERVISOR,
        RecommendedOwnerRole.APPLICANT_SERVICES,
        RecommendedOwnerRole.REVENUE_OPERATIONS,
        RecommendedOwnerRole.PAYMENT_RECONCILIATION,
        RecommendedOwnerRole.TECHNICAL_OPERATIONS,
        RecommendedOwnerRole.HUMAN_REVIEW,
    },
    RecommendedActionType.NO_ACTION: {
        RecommendedOwnerRole.HUMAN_REVIEW,
        RecommendedOwnerRole.LICENSING_OPERATIONS,
        RecommendedOwnerRole.LICENSING_SUPERVISOR,
    },
}


PROHIBITED_ACTION_PHRASES = (
    "refund the payment",
    "cancel the payment",
    "approve the license",
    "approve this license",
    "deny the license",
    "deny this license",
    "issue the license",
    "revoke the license",
    "bypass policy",
    "bypass the policy",
    "waive the policy",
    "manually update the workflow",
    "automatically update the workflow",
    "automatically change the workflow",
)


def _enum_value(value: object) -> str:
    if isinstance(value, Enum):
        return str(value.value)

    return str(value)


def _add_issue(
    issues: list[AssessmentValidationIssue],
    *,
    code: str,
    severity: ValidationSeverity,
    message: str,
) -> None:
    issues.append(
        AssessmentValidationIssue(
            code=code,
            severity=severity,
            message=message,
        )
    )


def _has_errors(
    issues: Iterable[AssessmentValidationIssue],
) -> bool:
    return any(
        issue.severity == ValidationSeverity.ERROR
        for issue in issues
    )


def _available_evidence_ids(
    packet: ReasoningPacket,
) -> set[str]:
    return {
        evidence.evidence_id
        for evidence in packet.evidence
    }


def _deterministic_categories(
    packet: ReasoningPacket,
) -> set[str]:
    return {
        _enum_value(finding.category)
        for finding in packet.deterministic_findings
    }


def _finding_evidence_ids(
    packet: ReasoningPacket,
    category: AssessmentCategory,
) -> set[str]:
    evidence_ids: set[str] = set()

    for finding in packet.deterministic_findings:
        if _enum_value(finding.category) != category.value:
            continue

        evidence_ids.update(
            finding.evidence_ids
        )

    return evidence_ids


def _validate_evidence(
    packet: ReasoningPacket,
    draft: ModelAssessmentDraft,
    issues: list[AssessmentValidationIssue],
) -> None:
    available = _available_evidence_ids(packet)

    supporting = set(
        draft.supporting_evidence_ids
    )

    conflicting = set(
        draft.conflicting_evidence_ids
    )

    if not supporting:
        _add_issue(
            issues,
            code="MISSING_SUPPORTING_EVIDENCE",
            severity=ValidationSeverity.ERROR,
            message=(
                "The model did not cite any supporting evidence."
            ),
        )

    unknown = (
        supporting | conflicting
    ) - available

    if unknown:
        _add_issue(
            issues,
            code="UNKNOWN_EVIDENCE_REFERENCE",
            severity=ValidationSeverity.ERROR,
            message=(
                "The model referenced evidence IDs that are not "
                f"present in the reasoning packet: "
                f"{sorted(unknown)}"
            ),
        )

    overlap = supporting & conflicting

    if overlap:
        _add_issue(
            issues,
            code="CONFLICTING_EVIDENCE_CLASSIFICATION",
            severity=ValidationSeverity.ERROR,
            message=(
                "The same evidence cannot be classified as both "
                f"supporting and conflicting: {sorted(overlap)}"
            ),
        )

    finding_evidence = _finding_evidence_ids(
        packet,
        draft.likely_category,
    )

    if (
        supporting
        and finding_evidence
        and not supporting.intersection(finding_evidence)
    ):
        _add_issue(
            issues,
            code="FINDING_EVIDENCE_NOT_CITED",
            severity=ValidationSeverity.ERROR,
            message=(
                "The assessment did not cite evidence supporting "
                "the matching deterministic finding."
            ),
        )


def _validate_category(
    packet: ReasoningPacket,
    draft: ModelAssessmentDraft,
    issues: list[AssessmentValidationIssue],
) -> None:
    deterministic_categories = (
        _deterministic_categories(packet)
    )

    if not deterministic_categories:
        return

    if (
        draft.likely_category
        != AssessmentCategory.AMBIGUOUS
        and draft.likely_category.value
        not in deterministic_categories
    ):
        _add_issue(
            issues,
            code="CATEGORY_CONFLICT",
            severity=ValidationSeverity.ERROR,
            message=(
                "The model category does not match any "
                "deterministic finding category."
            ),
        )


def _validate_action(
    draft: ModelAssessmentDraft,
    issues: list[AssessmentValidationIssue],
) -> None:
    allowed_actions = CATEGORY_ACTIONS[
        draft.likely_category
    ]

    if draft.recommended_action not in allowed_actions:
        _add_issue(
            issues,
            code="INCOMPATIBLE_ACTION",
            severity=ValidationSeverity.ERROR,
            message=(
                f"Action {draft.recommended_action.value} is not "
                f"allowed for category "
                f"{draft.likely_category.value}."
            ),
        )

    allowed_owners = ACTION_OWNERS[
        draft.recommended_action
    ]

    if (
        draft.recommended_owner_role
        not in allowed_owners
    ):
        _add_issue(
            issues,
            code="INCOMPATIBLE_OWNER",
            severity=ValidationSeverity.ERROR,
            message=(
                f"Owner {draft.recommended_owner_role.value} is "
                f"not compatible with action "
                f"{draft.recommended_action.value}."
            ),
        )


def _validate_free_text_safety(
    draft: ModelAssessmentDraft,
    issues: list[AssessmentValidationIssue],
) -> None:
    rationale = (
        draft.recommended_action_rationale.lower()
    )

    for phrase in PROHIBITED_ACTION_PHRASES:
        if phrase not in rationale:
            continue

        _add_issue(
            issues,
            code="PROHIBITED_ACTION_LANGUAGE",
            severity=ValidationSeverity.ERROR,
            message=(
                "The recommendation rationale contains "
                f"prohibited directive language: {phrase!r}."
            ),
        )


def _validate_safety_constraints(
    draft: ModelAssessmentDraft,
    issues: list[AssessmentValidationIssue],
) -> None:
    if draft.safety_constraints:
        return

    _add_issue(
        issues,
        code="MISSING_SAFETY_CONSTRAINTS",
        severity=ValidationSeverity.WARNING,
        message=(
            "The model returned no explicit safety constraints."
        ),
    )


def _calculate_confidence(
    packet: ReasoningPacket,
    draft: ModelAssessmentDraft,
) -> tuple[ConfidenceLevel, list[str]]:
    basis: list[str] = []

    if (
        draft.likely_category
        == AssessmentCategory.AMBIGUOUS
    ):
        return (
            ConfidenceLevel.LOW,
            [
                "The model classified the case as ambiguous."
            ],
        )

    deterministic_categories = (
        _deterministic_categories(packet)
    )

    category_matches = (
        draft.likely_category.value
        in deterministic_categories
    )

    if category_matches:
        basis.append(
            "The model category matches a deterministic finding."
        )

    finding_evidence = _finding_evidence_ids(
        packet,
        draft.likely_category,
    )

    supporting = set(
        draft.supporting_evidence_ids
    )

    all_finding_evidence_cited = (
        bool(finding_evidence)
        and finding_evidence.issubset(supporting)
    )

    if all_finding_evidence_cited:
        basis.append(
            "All evidence attached to the matching deterministic "
            "finding was cited."
        )

    if draft.conflicting_evidence_ids:
        basis.append(
            "The model identified conflicting evidence."
        )

        return ConfidenceLevel.LOW, basis

    if draft.missing_information:
        basis.append(
            "The model identified missing information."
        )

        return ConfidenceLevel.MEDIUM, basis

    if (
        category_matches
        and all_finding_evidence_cited
    ):
        basis.append(
            "No conflicting evidence or missing information "
            "was reported."
        )

        return ConfidenceLevel.HIGH, basis

    basis.append(
        "The assessment is grounded but does not cite the full "
        "deterministic finding evidence set."
    )

    return ConfidenceLevel.MEDIUM, basis


def validate_model_assessment(
    packet: ReasoningPacket,
    draft: ModelAssessmentDraft,
) -> AssessmentValidationResult:
    """
    Deterministically validate one schema-valid model draft.

    A model response is accepted only when it:
    - cites real packet evidence,
    - aligns with deterministic findings,
    - recommends an allowed bounded action,
    - routes to a compatible owner,
    - avoids prohibited directive language.

    Confidence is calculated by CivicResolve, not by the model.
    """

    issues: list[AssessmentValidationIssue] = []

    _validate_evidence(
        packet,
        draft,
        issues,
    )

    _validate_category(
        packet,
        draft,
        issues,
    )

    _validate_action(
        draft,
        issues,
    )

    _validate_free_text_safety(
        draft,
        issues,
    )

    _validate_safety_constraints(
        draft,
        issues,
    )

    if _has_errors(issues):
        return AssessmentValidationResult(
            is_valid=False,
            issues=issues,
            assessment=None,
        )

    confidence, confidence_basis = (
        _calculate_confidence(
            packet,
            draft,
        )
    )

    warnings = [
        issue.message
        for issue in issues
        if issue.severity
        == ValidationSeverity.WARNING
    ]

    assessment = ValidatedAssessment(
        **draft.model_dump(),
        confidence=confidence,
        confidence_basis=confidence_basis,
        validation_warnings=warnings,
        human_approval_required=True,
    )

    return AssessmentValidationResult(
        is_valid=True,
        issues=issues,
        assessment=assessment,
    )