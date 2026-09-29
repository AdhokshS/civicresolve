import pytest

from civicresolve.db.audit_repository import (
    AuditRepository,
)
from civicresolve.models.action import (
    ActionExecutionStatus,
    ControlledOperationType,
)
from civicresolve.models.audit import (
    AuditEventType,
    HumanReviewDecision,
)
from civicresolve.services.action_service import (
    ActionNotAuthorizedError,
    build_authorized_action_plan,
    ensure_action_preview_audit_event,
    simulate_controlled_action,
)
from civicresolve.services.audit_service import (
    ensure_ai_assessment_audit_event,
    record_human_review_decision,
)
from civicresolve.ui.console import (
    build_case_workspaces,
)


def _build_workspace():
    return build_case_workspaces()[
        "CASE-1047"
    ]


def _build_repository(
    tmp_path,
):
    return AuditRepository(
        tmp_path
        / "action-test.duckdb"
    )


def _persist_ai_assessment(
    repository,
    workspace,
):
    event = ensure_ai_assessment_audit_event(
        repository,
        case_id=workspace.case.case_id,
        application_id=(
            workspace.case.application.application_id
        ),
        assessment_run=workspace.assessment_run,
    )

    assert event is not None

    return event


def _authorize(
    repository,
    workspace,
):
    _persist_ai_assessment(
        repository,
        workspace,
    )

    return record_human_review_decision(
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
            "Authorize preparation of the bounded "
            "operational next step."
        ),
    )


def test_action_plan_requires_human_authorization(
    tmp_path,
):
    repository = _build_repository(
        tmp_path
    )

    workspace = _build_workspace()

    _persist_ai_assessment(
        repository,
        workspace,
    )

    assessment = (
        workspace.validated_assessment
    )

    assert assessment is not None

    with pytest.raises(
        ActionNotAuthorizedError
    ):
        build_authorized_action_plan(
            repository,
            case=workspace.case,
            assessment=assessment,
        )


def test_non_authorizing_review_blocks_action_plan(
    tmp_path,
):
    repository = _build_repository(
        tmp_path
    )

    workspace = _build_workspace()

    _persist_ai_assessment(
        repository,
        workspace,
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
            "More evidence is required."
        ),
    )

    assessment = (
        workspace.validated_assessment
    )

    assert assessment is not None

    with pytest.raises(
        ActionNotAuthorizedError
    ):
        build_authorized_action_plan(
            repository,
            case=workspace.case,
            assessment=assessment,
        )


def test_authorized_hero_case_builds_bounded_plan(
    tmp_path,
):
    repository = _build_repository(
        tmp_path
    )

    workspace = _build_workspace()

    _authorize(
        repository,
        workspace,
    )

    assessment = (
        workspace.validated_assessment
    )

    assert assessment is not None

    plan = build_authorized_action_plan(
        repository,
        case=workspace.case,
        assessment=assessment,
    )

    assert (
        plan.operation
        == ControlledOperationType
        .CREATE_INTEGRATION_INVESTIGATION_TASK
    )

    assert (
        plan.current_state[
            "payment_status"
        ]
        == "SUCCESS"
    )

    assert (
        plan.current_state[
            "workflow_payment_state"
        ]
        == "AWAITING_PAYMENT"
    )

    assert (
        plan.human_authorization_required
        is True
    )

    assert any(
        "Do not approve"
        in effect
        for effect in plan.prohibited_effects
    )


def test_action_preview_is_persisted_once(
    tmp_path,
):
    repository = _build_repository(
        tmp_path
    )

    workspace = _build_workspace()

    _authorize(
        repository,
        workspace,
    )

    assessment = (
        workspace.validated_assessment
    )

    assert assessment is not None

    plan = build_authorized_action_plan(
        repository,
        case=workspace.case,
        assessment=assessment,
    )

    first = ensure_action_preview_audit_event(
        repository,
        plan,
    )

    second = ensure_action_preview_audit_event(
        repository,
        plan,
    )

    assert (
        first.event_id
        == second.event_id
    )

    events = repository.list_case_events(
        workspace.case.case_id
    )

    preview_events = [
        event
        for event in events
        if (
            event.event_type
            == AuditEventType.ACTION_PREVIEWED
        )
    ]

    assert len(preview_events) == 1

    assert (
        repository.verify_case_chain(
            workspace.case.case_id
        )
        is True
    )


def test_simulated_execution_changes_no_external_system(
    tmp_path,
):
    repository = _build_repository(
        tmp_path
    )

    workspace = _build_workspace()

    _authorize(
        repository,
        workspace,
    )

    assessment = (
        workspace.validated_assessment
    )

    assert assessment is not None

    plan = build_authorized_action_plan(
        repository,
        case=workspace.case,
        assessment=assessment,
    )

    result = simulate_controlled_action(
        repository,
        plan,
    )

    assert (
        result.status
        == ActionExecutionStatus.SIMULATED_SUCCESS
    )

    assert (
        result.external_system_changed
        is False
    )

    assert (
        result.government_decision_changed
        is False
    )

    assert (
        repository.verify_case_chain(
            workspace.case.case_id
        )
        is True
    )


def test_simulated_execution_is_idempotent(
    tmp_path,
):
    repository = _build_repository(
        tmp_path
    )

    workspace = _build_workspace()

    _authorize(
        repository,
        workspace,
    )

    assessment = (
        workspace.validated_assessment
    )

    assert assessment is not None

    plan = build_authorized_action_plan(
        repository,
        case=workspace.case,
        assessment=assessment,
    )

    first = simulate_controlled_action(
        repository,
        plan,
    )

    second = simulate_controlled_action(
        repository,
        plan,
    )

    assert (
        first.execution_id
        == second.execution_id
    )

    events = repository.list_case_events(
        workspace.case.case_id
    )

    execution_events = [
        event
        for event in events
        if (
            event.event_type
            == AuditEventType.ACTION_EXECUTED
        )
    ]

    assert len(execution_events) == 1

    assert (
        repository.verify_case_chain(
            workspace.case.case_id
        )
        is True
    )
