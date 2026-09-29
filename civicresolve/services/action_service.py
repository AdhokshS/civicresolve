from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from civicresolve.db.audit_repository import AuditRepository
from civicresolve.models.action import (
    ActionExecutionResult,
    ActionExecutionStatus,
    ActionPlan,
    ControlledOperationType,
)
from civicresolve.models.assessment import (
    RecommendedActionType,
    ValidatedAssessment,
)
from civicresolve.models.audit import (
    AuditActorType,
    AuditEvent,
    AuditEventType,
    HumanReviewDecision,
)
from civicresolve.models.case import (
    BusinessLicenseCase,
)
from civicresolve.services.audit_service import (
    get_latest_human_review_event,
)


class ActionNotAuthorizedError(RuntimeError):
    """
    Raised when CivicResolve is asked to prepare an action without
    a persisted human authorization.
    """


ACTION_TEMPLATES = {
    RecommendedActionType.INVESTIGATE_INTEGRATION_SYNC: {
        "operation": (
            ControlledOperationType
            .CREATE_INTEGRATION_INVESTIGATION_TASK
        ),
        "target_system": (
            "Technical Operations work queue"
        ),
        "summary": (
            "Create an integration-investigation work item containing "
            "the validated exception, supporting evidence references, "
            "and failed synchronization events."
        ),
    },
    RecommendedActionType.PREPARE_PAYMENT_STATE_RECONCILIATION: {
        "operation": (
            ControlledOperationType
            .CREATE_PAYMENT_RECONCILIATION_TASK
        ),
        "target_system": (
            "Payment Reconciliation work queue"
        ),
        "summary": (
            "Create a payment-state reconciliation work item for "
            "human review using the confirmed payment and workflow "
            "evidence."
        ),
    },
    RecommendedActionType.REQUEST_UPDATED_DOCUMENT: {
        "operation": (
            ControlledOperationType
            .CREATE_DOCUMENT_REQUEST_TASK
        ),
        "target_system": (
            "Applicant Services work queue"
        ),
        "summary": (
            "Prepare an applicant-services work item requesting the "
            "required updated document. Demo mode does not send an "
            "external communication."
        ),
    },
    RecommendedActionType.ROUTE_FOR_OWNER_ASSIGNMENT: {
        "operation": (
            ControlledOperationType
            .CREATE_OWNER_ASSIGNMENT_TASK
        ),
        "target_system": (
            "Licensing Supervisor work queue"
        ),
        "summary": (
            "Create a supervisor work item to assign an accountable "
            "operational owner for the next workflow stage."
        ),
    },
    RecommendedActionType.RECONCILE_PAYMENT_REFERENCE: {
        "operation": (
            ControlledOperationType
            .CREATE_PAYMENT_REFERENCE_RECONCILIATION_TASK
        ),
        "target_system": (
            "Payment Reconciliation work queue"
        ),
        "summary": (
            "Create a reconciliation work item for the mismatched "
            "payment and application references. No payment linkage "
            "is changed automatically."
        ),
    },
    RecommendedActionType.ESCALATE_FOR_HUMAN_INVESTIGATION: {
        "operation": (
            ControlledOperationType
            .CREATE_HUMAN_INVESTIGATION_TASK
        ),
        "target_system": (
            "Human Review work queue"
        ),
        "summary": (
            "Create a human-investigation work item containing the "
            "validated evidence and unresolved uncertainty."
        ),
    },
    RecommendedActionType.NO_ACTION: {
        "operation": (
            ControlledOperationType.NO_OPERATION
        ),
        "target_system": (
            "CivicResolve audit ledger"
        ),
        "summary": (
            "Record that no bounded operational action is proposed."
        ),
    },
}


PROHIBITED_EFFECTS = [
    "Do not approve, deny, issue, suspend, or revoke a license.",
    "Do not bypass or waive a policy requirement.",
    "Do not directly mutate the licensing workflow state.",
    "Do not refund, cancel, or reassign a payment.",
    "Do not modify an external system in demo mode.",
]


def _require_authorized_review(
    repository: AuditRepository,
    case_id: str,
) -> AuditEvent:
    review_event = get_latest_human_review_event(
        repository,
        case_id,
    )

    if review_event is None:
        raise ActionNotAuthorizedError(
            "No persisted human review exists for this case."
        )

    decision = review_event.payload.get(
        "decision"
    )

    if (
        decision
        != HumanReviewDecision
        .AUTHORIZE_NEXT_STEP_PREPARATION
        .value
    ):
        raise ActionNotAuthorizedError(
            "The latest human review did not authorize "
            "next-step preparation."
        )

    return review_event


def _build_idempotency_key(
    *,
    case_id: str,
    application_id: str,
    recommendation: RecommendedActionType,
    authorization_event_id: str,
) -> str:
    material = (
        f"{case_id}|"
        f"{application_id}|"
        f"{recommendation.value}|"
        f"{authorization_event_id}"
    )

    return hashlib.sha256(
        material.encode("utf-8")
    ).hexdigest()


def build_authorized_action_plan(
    repository: AuditRepository,
    *,
    case: BusinessLicenseCase,
    assessment: ValidatedAssessment,
) -> ActionPlan:
    """
    Build a deterministic action plan only after a persisted human
    authorization exists.

    Building the plan does not execute anything.
    """

    authorization = _require_authorized_review(
        repository,
        case.case_id,
    )

    template = ACTION_TEMPLATES[
        assessment.recommended_action
    ]

    idempotency_key = _build_idempotency_key(
        case_id=case.case_id,
        application_id=(
            case.application.application_id
        ),
        recommendation=(
            assessment.recommended_action
        ),
        authorization_event_id=(
            authorization.event_id
        ),
    )

    plan_id = (
        "PLAN-"
        f"{idempotency_key[:12].upper()}"
    )

    payment_reference_matches = (
        case.payment.application_id
        == case.application.application_id
    )

    current_state = {
        "application_status": (
            case.application.status.value
        ),
        "workflow_stage": (
            case.workflow.current_stage.value
        ),
        "workflow_payment_state": (
            case.workflow.payment_state.value
        ),
        "payment_status": (
            case.payment.status.value
        ),
        "payment_reference": (
            case.payment.application_id
        ),
        "payment_reference_matches_application": (
            "YES"
            if payment_reference_matches
            else "NO"
        ),
    }

    proposed_effects = [
        str(
            template["summary"]
        ),
        (
            "Route the prepared work item to "
            f"{assessment.recommended_owner_role.value}."
        ),
        (
            "Attach the validated supporting evidence references "
            "to the prepared work item."
        ),
    ]

    return ActionPlan(
        plan_id=plan_id,
        idempotency_key=idempotency_key,
        case_id=case.case_id,
        application_id=(
            case.application.application_id
        ),
        authorization_event_id=(
            authorization.event_id
        ),
        source_recommendation=(
            assessment.recommended_action
        ),
        operation=template["operation"],
        target_owner_role=(
            assessment.recommended_owner_role
        ),
        target_system=str(
            template["target_system"]
        ),
        summary=str(
            template["summary"]
        ),
        current_state=current_state,
        proposed_effects=proposed_effects,
        prohibited_effects=(
            PROHIBITED_EFFECTS.copy()
        ),
        human_authorization_required=True,
        synthetic=True,
    )


def ensure_action_preview_audit_event(
    repository: AuditRepository,
    plan: ActionPlan,
) -> AuditEvent:
    """
    Persist one ACTION_PREVIEWED event for an idempotency key.

    Re-rendering Streamlit does not create duplicate preview events.
    """

    events = repository.list_case_events(
        plan.case_id
    )

    for event in events:
        if (
            event.event_type
            == AuditEventType.ACTION_PREVIEWED
            and event.payload.get(
                "idempotency_key"
            )
            == plan.idempotency_key
        ):
            return event

    payload = {
        "plan_id": plan.plan_id,
        "idempotency_key": (
            plan.idempotency_key
        ),
        "authorization_event_id": (
            plan.authorization_event_id
        ),
        "source_recommendation": (
            plan.source_recommendation.value
        ),
        "operation": (
            plan.operation.value
        ),
        "target_owner_role": (
            plan.target_owner_role.value
        ),
        "target_system": (
            plan.target_system
        ),
        "summary": (
            plan.summary
        ),
        "current_state": (
            plan.current_state
        ),
        "proposed_effects": (
            plan.proposed_effects
        ),
        "prohibited_effects": (
            plan.prohibited_effects
        ),
        "human_authorization_required": (
            plan.human_authorization_required
        ),
        "synthetic": (
            plan.synthetic
        ),
    }

    return repository.append_event(
        case_id=plan.case_id,
        application_id=(
            plan.application_id
        ),
        event_type=(
            AuditEventType.ACTION_PREVIEWED
        ),
        actor_type=(
            AuditActorType.SYSTEM
        ),
        actor_id=(
            "civicresolve-action-planner"
        ),
        payload=payload,
    )


def _execution_from_event(
    event: AuditEvent,
) -> ActionExecutionResult:
    return ActionExecutionResult(
        execution_id=event.payload[
            "execution_id"
        ],
        plan_id=event.payload[
            "plan_id"
        ],
        idempotency_key=event.payload[
            "idempotency_key"
        ],
        case_id=event.case_id,
        application_id=(
            event.application_id
        ),
        operation=event.payload[
            "operation"
        ],
        status=event.payload[
            "status"
        ],
        executed_at=event.occurred_at,
        external_system_changed=(
            event.payload[
                "external_system_changed"
            ]
        ),
        government_decision_changed=(
            event.payload[
                "government_decision_changed"
            ]
        ),
        message=event.payload[
            "message"
        ],
    )


def simulate_controlled_action(
    repository: AuditRepository,
    plan: ActionPlan,
) -> ActionExecutionResult:
    """
    Simulate the bounded action.

    The demo executor does not call or modify an external system.

    Execution is idempotent: repeating the same authorized plan
    returns the previously persisted execution result.
    """

    _require_authorized_review(
        repository,
        plan.case_id,
    )

    ensure_action_preview_audit_event(
        repository,
        plan,
    )

    events = repository.list_case_events(
        plan.case_id
    )

    for event in events:
        if (
            event.event_type
            == AuditEventType.ACTION_EXECUTED
            and event.payload.get(
                "idempotency_key"
            )
            == plan.idempotency_key
        ):
            return _execution_from_event(
                event
            )

    execution_id = (
        "EXEC-"
        f"{plan.idempotency_key[12:24].upper()}"
    )

    timestamp = datetime.now(
        UTC
    )

    message = (
        "Controlled action simulated successfully. "
        "The bounded work item was prepared locally; "
        "no external system or government decision was changed."
    )

    result = ActionExecutionResult(
        execution_id=execution_id,
        plan_id=plan.plan_id,
        idempotency_key=(
            plan.idempotency_key
        ),
        case_id=plan.case_id,
        application_id=(
            plan.application_id
        ),
        operation=plan.operation,
        status=(
            ActionExecutionStatus
            .SIMULATED_SUCCESS
        ),
        executed_at=timestamp,
        external_system_changed=False,
        government_decision_changed=False,
        message=message,
    )

    repository.append_event(
        case_id=plan.case_id,
        application_id=(
            plan.application_id
        ),
        event_type=(
            AuditEventType.ACTION_EXECUTED
        ),
        actor_type=(
            AuditActorType.SYSTEM
        ),
        actor_id=(
            "civicresolve-demo-executor"
        ),
        occurred_at=timestamp,
        payload={
            "execution_id": (
                result.execution_id
            ),
            "plan_id": (
                result.plan_id
            ),
            "idempotency_key": (
                result.idempotency_key
            ),
            "operation": (
                result.operation.value
            ),
            "status": (
                result.status.value
            ),
            "external_system_changed": False,
            "government_decision_changed": False,
            "message": (
                result.message
            ),
        },
    )

    return result