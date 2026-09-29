from datetime import UTC, datetime

import duckdb

from civicresolve.db.audit_repository import (
    AuditRepository,
)
from civicresolve.models.audit import (
    AuditActorType,
    AuditEventType,
    HumanReviewDecision,
    HumanReviewRecord,
)


def test_audit_event_persists(
    tmp_path,
):
    db_path = (
        tmp_path
        / "audit-test.duckdb"
    )

    repository = AuditRepository(
        db_path
    )

    repository.append_event(
        case_id="CASE-1047",
        application_id="LIC-2026-1047",
        event_type=(
            AuditEventType.AI_ASSESSMENT_VALIDATED
        ),
        actor_type=AuditActorType.AI,
        actor_id="qwen-demo",
        payload={
            "assessment_status": "VALIDATED",
        },
        occurred_at=datetime(
            2026,
            9,
            24,
            10,
            20,
            tzinfo=UTC,
        ),
    )

    reopened = AuditRepository(
        db_path
    )

    events = reopened.list_case_events(
        "CASE-1047"
    )

    assert len(events) == 1

    assert (
        events[0].event_type
        == AuditEventType.AI_ASSESSMENT_VALIDATED
    )


def test_second_event_links_to_first_hash(
    tmp_path,
):
    repository = AuditRepository(
        tmp_path
        / "audit-test.duckdb"
    )

    first = repository.append_event(
        case_id="CASE-1047",
        application_id="LIC-2026-1047",
        event_type=(
            AuditEventType.AI_ASSESSMENT_VALIDATED
        ),
        actor_type=AuditActorType.AI,
        payload={
            "status": "VALIDATED",
        },
    )

    second = repository.append_event(
        case_id="CASE-1047",
        application_id="LIC-2026-1047",
        event_type=(
            AuditEventType.HUMAN_REVIEW_RECORDED
        ),
        actor_type=AuditActorType.HUMAN,
        actor_id="demo-reviewer",
        payload={
            "decision": (
                "AUTHORIZE_NEXT_STEP_PREPARATION"
            ),
        },
    )

    assert (
        second.previous_event_hash
        == first.event_hash
    )


def test_valid_chain_verifies(
    tmp_path,
):
    repository = AuditRepository(
        tmp_path
        / "audit-test.duckdb"
    )

    repository.append_event(
        case_id="CASE-1047",
        application_id="LIC-2026-1047",
        event_type=(
            AuditEventType.AI_ASSESSMENT_VALIDATED
        ),
        actor_type=AuditActorType.AI,
        payload={
            "status": "VALIDATED",
        },
    )

    repository.append_event(
        case_id="CASE-1047",
        application_id="LIC-2026-1047",
        event_type=(
            AuditEventType.HUMAN_REVIEW_RECORDED
        ),
        actor_type=AuditActorType.HUMAN,
        payload={
            "decision": "REQUEST_ADDITIONAL_EVIDENCE",
        },
    )

    assert (
        repository.verify_case_chain(
            "CASE-1047"
        )
        is True
    )


def test_tampered_event_fails_verification(
    tmp_path,
):
    db_path = (
        tmp_path
        / "audit-test.duckdb"
    )

    repository = AuditRepository(
        db_path
    )

    event = repository.append_event(
        case_id="CASE-1047",
        application_id="LIC-2026-1047",
        event_type=(
            AuditEventType.HUMAN_REVIEW_RECORDED
        ),
        actor_type=AuditActorType.HUMAN,
        payload={
            "decision": "REJECT_RECOMMENDATION",
        },
    )

    with duckdb.connect(
        str(db_path)
    ) as connection:
        connection.execute(
            """
            UPDATE audit_events
            SET payload_json = ?
            WHERE event_id = ?
            """,
            [
                '{"decision":"AUTHORIZE_NEXT_STEP_PREPARATION"}',
                event.event_id,
            ],
        )

    assert (
        repository.verify_case_chain(
            "CASE-1047"
        )
        is False
    )


def test_human_review_is_recorded_without_execution(
    tmp_path,
):
    repository = AuditRepository(
        tmp_path
        / "audit-test.duckdb"
    )

    record = HumanReviewRecord(
        case_id="CASE-1047",
        application_id="LIC-2026-1047",
        decision=(
            HumanReviewDecision
            .AUTHORIZE_NEXT_STEP_PREPARATION
        ),
        reviewer_id="demo-reviewer",
        rationale=(
            "Evidence supports preparing the bounded "
            "next operational step."
        ),
        recorded_at=datetime.now(
            UTC
        ),
        external_action_executed=False,
    )

    event = repository.record_human_review(
        record
    )

    assert (
        event.event_type
        == AuditEventType.HUMAN_REVIEW_RECORDED
    )

    assert (
        event.payload[
            "external_action_executed"
        ]
        is False
    )

    assert (
        repository.verify_case_chain(
            "CASE-1047"
        )
        is True
    )