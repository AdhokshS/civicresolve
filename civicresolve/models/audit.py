from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field

from civicresolve.models.case import StrictModel


class AuditEventType(str, Enum):
    AI_ASSESSMENT_VALIDATED = "AI_ASSESSMENT_VALIDATED"
    HUMAN_REVIEW_RECORDED = "HUMAN_REVIEW_RECORDED"
    ACTION_PREVIEWED = "ACTION_PREVIEWED"
    ACTION_EXECUTED = "ACTION_EXECUTED"
    ACTION_REJECTED = "ACTION_REJECTED"


class AuditActorType(str, Enum):
    SYSTEM = "SYSTEM"
    AI = "AI"
    HUMAN = "HUMAN"


class HumanReviewDecision(str, Enum):
    AUTHORIZE_NEXT_STEP_PREPARATION = (
        "AUTHORIZE_NEXT_STEP_PREPARATION"
    )

    REQUEST_ADDITIONAL_EVIDENCE = (
        "REQUEST_ADDITIONAL_EVIDENCE"
    )

    REJECT_RECOMMENDATION = (
        "REJECT_RECOMMENDATION"
    )


class HumanReviewRecord(StrictModel):
    case_id: str
    application_id: str

    decision: HumanReviewDecision

    reviewer_id: str = "demo-reviewer"

    rationale: str = ""

    recorded_at: datetime

    external_action_executed: bool = False


class AuditEvent(StrictModel):
    """
    One append-only CivicResolve provenance event.

    chain_position represents append order within one case and is
    independent of the event's business timestamp.

    Events are hash-linked so CivicResolve can detect modification
    of previously persisted audit content.
    """

    schema_version: str = "1.0"

    event_id: str

    case_id: str
    application_id: str

    chain_position: int = Field(
        ge=1
    )

    event_type: AuditEventType

    actor_type: AuditActorType
    actor_id: str | None = None

    occurred_at: datetime

    payload: dict[str, Any] = Field(
        default_factory=dict
    )

    previous_event_hash: str | None = None

    event_hash: str