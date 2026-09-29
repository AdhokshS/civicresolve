from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field

from civicresolve.models.assessment import (
    RecommendedActionType,
    RecommendedOwnerRole,
)
from civicresolve.models.case import StrictModel


class ControlledOperationType(str, Enum):
    CREATE_INTEGRATION_INVESTIGATION_TASK = (
        "CREATE_INTEGRATION_INVESTIGATION_TASK"
    )

    CREATE_PAYMENT_RECONCILIATION_TASK = (
        "CREATE_PAYMENT_RECONCILIATION_TASK"
    )

    CREATE_DOCUMENT_REQUEST_TASK = (
        "CREATE_DOCUMENT_REQUEST_TASK"
    )

    CREATE_OWNER_ASSIGNMENT_TASK = (
        "CREATE_OWNER_ASSIGNMENT_TASK"
    )

    CREATE_PAYMENT_REFERENCE_RECONCILIATION_TASK = (
        "CREATE_PAYMENT_REFERENCE_RECONCILIATION_TASK"
    )

    CREATE_HUMAN_INVESTIGATION_TASK = (
        "CREATE_HUMAN_INVESTIGATION_TASK"
    )

    NO_OPERATION = "NO_OPERATION"


class ActionPlan(StrictModel):
    """
    Human-authorized bounded operational action.

    An ActionPlan describes exactly what CivicResolve is permitted
    to prepare or simulate after a human review decision.

    It is not authorization for a government decision.
    """

    plan_version: str = "1.0"

    plan_id: str
    idempotency_key: str

    case_id: str
    application_id: str

    authorization_event_id: str

    source_recommendation: RecommendedActionType

    operation: ControlledOperationType

    target_owner_role: RecommendedOwnerRole

    target_system: str

    summary: str

    current_state: dict[str, str] = Field(
        default_factory=dict
    )

    proposed_effects: list[str] = Field(
        default_factory=list
    )

    prohibited_effects: list[str] = Field(
        default_factory=list
    )

    human_authorization_required: bool = True

    synthetic: bool = True


class ActionExecutionStatus(str, Enum):
    SIMULATED_SUCCESS = "SIMULATED_SUCCESS"


class ActionExecutionResult(StrictModel):
    """
    Result of the CivicResolve demo executor.

    The demo executor records what a bounded action would do without
    modifying an external government, payment, or licensing system.
    """

    execution_id: str

    plan_id: str
    idempotency_key: str

    case_id: str
    application_id: str

    operation: ControlledOperationType

    status: ActionExecutionStatus

    executed_at: datetime

    external_system_changed: bool = False

    government_decision_changed: bool = False

    message: str