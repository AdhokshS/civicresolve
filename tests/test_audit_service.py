from datetime import UTC, datetime

from civicresolve.db.audit_repository import (
    AuditRepository,
)
from civicresolve.models.audit import (
    AuditEventType,
    HumanReviewDecision,
)
from civicresolve.services.audit_service import (
    ensure_ai_assessment_audit_event,
    get_latest_human_review_event,
    record_human_review_decision,
)
from civicresolve.ui.console import (
    build_case_workspaces,
)


def _build_workspace():
    return build_case_workspaces()[
        "CASE-1047"
    ]


def test_ai_assessment_is_persisted_once(
    tmp_path,
):
    repository = AuditRepository(
        tmp_path
        / "audit-service.duckdb"
    )

    workspace = _build_workspace()

    first = ensure_ai_assessment_audit_event(
        repository,
        case_id=workspace.case.case_id,
        application_id=(
            workspace.case.application.application_id
        ),
        assessment_run=workspace.assessment_run,
    )

    second = ensure_ai_assessment_audit_event(
        repository,
        case_id=workspace.case.case_id,
        application_id=(
            workspace.case.application.application_id
        ),
        assessment_run=workspace.assessment_run,
    )

    assert first is not None
    assert second is not None

    assert (
        first.event_id
        == second.event_id
    )

    events = repository.list_case_events(
        workspace.case.case_id
    )

    assert len(events) == 1

    assert (
        events[0].event_type
        == AuditEventType.AI_ASSESSMENT_VALIDATED
    )


def test_ai_audit_event_contains_decision_provenance(
    tmp_path,
):
    repository = AuditRepository(
        tmp_path
        / "audit-service.duckdb"
    )

    workspace = _build_workspace()

    event = ensure_ai_assessment_audit_event(
        repository,
        case_id=workspace.case.case_id,
        application_id=(
            workspace.case.application.application_id
        ),
        assessment_run=workspace.assessment_run,
    )

    assert event is not None

    assert (
        event.payload["likely_category"]
        == "SYSTEM_INTEGRATION"
    )

    assert (
        event.payload["confidence"]
        == "HIGH"
    )

    assert (
        event.payload["recommended_action"]
        == "INVESTIGATE_INTEGRATION_SYNC"
    )

    assert (
        "EVD-PAY-88219"
        in event.payload[
            "supporting_evidence_ids"
        ]
    )

    assert (
        event.payload[
            "human_approval_required"
        ]
        is True
    )


def test_human_review_appends_to_ai_audit_chain(
    tmp_path,
):
    repository = AuditRepository(
        tmp_path
        / "audit-service.duckdb"
    )

    workspace = _build_workspace()

    ai_event = ensure_ai_assessment_audit_event(
        repository,
        case_id=workspace.case.case_id,
        application_id=(
            workspace.case.application.application_id
        ),
        assessment_run=workspace.assessment_run,
    )

    assert ai_event is not None

    review_event = record_human_review_decision(
        repository,
        case_id=workspace.case.case_id,
        application_id=(
            workspace.case.application.application_id
        ),
        decision=(
            HumanReviewDecision
            .AUTHORIZE_NEXT_STEP_PREPARATION
        ),
        rationale=(
            "Evidence supports preparing the bounded "
            "next operational step."
        ),
        reviewer_id="demo-reviewer",
        recorded_at=datetime(
            2026,
            9,
            29,
            3,
            30,
            tzinfo=UTC,
        ),
    )

    assert (
        review_event.previous_event_hash
        == ai_event.event_hash
    )

    assert (
        review_event.payload[
            "external_action_executed"
        ]
        is False
    )

    assert (
        repository.verify_case_chain(
            workspace.case.case_id
        )
        is True
    )


def test_latest_human_review_survives_repository_reopen(
    tmp_path,
):
    db_path = (
        tmp_path
        / "audit-service.duckdb"
    )

    repository = AuditRepository(
        db_path
    )

    workspace = _build_workspace()

    ensure_ai_assessment_audit_event(
        repository,
        case_id=workspace.case.case_id,
        application_id=(
            workspace.case.application.application_id
        ),
        assessment_run=workspace.assessment_run,
    )

    record_human_review_decision(
        repository,
        case_id=workspace.case.case_id,
        application_id=(
            workspace.case.application.application_id
        ),
        decision=(
            HumanReviewDecision
            .REQUEST_ADDITIONAL_EVIDENCE
        ),
        rationale=(
            "Confirm the downstream workflow response."
        ),
        reviewer_id="demo-reviewer",
        recorded_at=datetime(
            2026,
            9,
            29,
            3,
            31,
            tzinfo=UTC,
        ),
    )

    reopened = AuditRepository(
        db_path
    )

    latest = get_latest_human_review_event(
        reopened,
        workspace.case.case_id,
    )

    assert latest is not None

    assert (
        latest.payload["decision"]
        == "REQUEST_ADDITIONAL_EVIDENCE"
    )

    assert (
        latest.payload[
            "external_action_executed"
        ]
        is False
    )

    assert (
        reopened.verify_case_chain(
            workspace.case.case_id
        )
        is True
    )