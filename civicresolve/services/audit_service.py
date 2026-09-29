from __future__ import annotations

from datetime import UTC, datetime

from civicresolve.db.audit_repository import AuditRepository
from civicresolve.models.assessment_run import (
    AssessmentRunResult,
)
from civicresolve.models.audit import (
    AuditActorType,
    AuditEvent,
    AuditEventType,
    HumanReviewDecision,
    HumanReviewRecord,
)


def ensure_ai_assessment_audit_event(
    repository: AuditRepository,
    *,
    case_id: str,
    application_id: str,
    assessment_run: AssessmentRunResult,
) -> AuditEvent | None:
    """
    Persist one validated-AI-assessment provenance event per case.

    Streamlit reruns frequently, so this function is intentionally
    idempotent for the demo: if a validated AI event already exists
    for the case, the existing event is returned instead of creating
    a duplicate.
    """

    existing_events = repository.list_case_events(
        case_id
    )

    for event in existing_events:
        if (
            event.event_type
            == AuditEventType.AI_ASSESSMENT_VALIDATED
        ):
            return event

    assessment = assessment_run.validated_assessment

    if assessment is None:
        return None

    validated_attempt = next(
        (
            attempt
            for attempt in reversed(
                assessment_run.attempts
            )
            if attempt.validation.is_valid
        ),
        None,
    )

    if validated_attempt is None:
        return None

    inference = validated_attempt.inference

    payload = {
        "assessment_status": assessment_run.status.value,
        "provider": inference.provider,
        "model_name": inference.model_name,
        "prompt_version": inference.prompt_version,
        "packet_version": inference.packet_version,
        "likely_category": (
            assessment.likely_category.value
        ),
        "confidence": assessment.confidence.value,
        "confidence_basis": (
            assessment.confidence_basis
        ),
        "supporting_evidence_ids": (
            assessment.supporting_evidence_ids
        ),
        "recommended_action": (
            assessment.recommended_action.value
        ),
        "recommended_owner_role": (
            assessment.recommended_owner_role.value
        ),
        "human_approval_required": (
            assessment.human_approval_required
        ),
    }

    return repository.append_event(
        case_id=case_id,
        application_id=application_id,
        event_type=(
            AuditEventType.AI_ASSESSMENT_VALIDATED
        ),
        actor_type=AuditActorType.AI,
        actor_id=inference.model_name,
        occurred_at=datetime.now(UTC),
        payload=payload,
    )


def record_human_review_decision(
    repository: AuditRepository,
    *,
    case_id: str,
    application_id: str,
    decision: HumanReviewDecision,
    rationale: str,
    reviewer_id: str = "demo-reviewer",
    recorded_at: datetime | None = None,
) -> AuditEvent:
    """
    Persist a human review decision.

    Recording the review does not execute an external workflow
    action. Execution remains a separate lifecycle step.
    """

    timestamp = (
        recorded_at
        if recorded_at is not None
        else datetime.now(UTC)
    )

    record = HumanReviewRecord(
        case_id=case_id,
        application_id=application_id,
        decision=decision,
        reviewer_id=reviewer_id,
        rationale=rationale,
        recorded_at=timestamp,
        external_action_executed=False,
    )

    return repository.record_human_review(
        record
    )


def get_human_review_events(
    repository: AuditRepository,
    case_id: str,
) -> list[AuditEvent]:
    """
    Return persisted human-review events for one case.
    """

    return [
        event
        for event in repository.list_case_events(
            case_id
        )
        if (
            event.event_type
            == AuditEventType.HUMAN_REVIEW_RECORDED
        )
    ]


def get_latest_human_review_event(
    repository: AuditRepository,
    case_id: str,
) -> AuditEvent | None:
    """
    Return the most recently persisted human-review event.
    """

    events = get_human_review_events(
        repository,
        case_id,
    )

    if not events:
        return None

    return events[-1]