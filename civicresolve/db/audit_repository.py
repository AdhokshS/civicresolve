from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import duckdb

from civicresolve.models.audit import (
    AuditActorType,
    AuditEvent,
    AuditEventType,
    HumanReviewRecord,
)

DEFAULT_AUDIT_DB_PATH = Path(
    "data/civicresolve.duckdb"
)


def _normalize_timestamp(
    timestamp: datetime,
) -> datetime:
    """
    Normalize audit timestamps to timezone-aware UTC.

    occurred_at describes when the underlying event occurred.
    It does not determine append order in the audit chain.
    """

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(
            tzinfo=UTC
        )

    return timestamp.astimezone(
        UTC
    )


def _canonical_timestamp(
    timestamp: datetime,
) -> str:
    normalized = _normalize_timestamp(
        timestamp
    )

    return (
        normalized.isoformat(
            timespec="microseconds"
        )
        .replace(
            "+00:00",
            "Z",
        )
    )


def _canonical_payload(
    payload: dict[str, Any],
) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def _calculate_event_hash(
    *,
    event_id: str,
    case_id: str,
    application_id: str,
    chain_position: int,
    event_type: str,
    actor_type: str,
    actor_id: str | None,
    occurred_at: datetime,
    payload_json: str,
    previous_event_hash: str | None,
) -> str:
    """
    Calculate a digest from a stable canonical event representation.

    chain_position is included in the digest so reordering events
    is detectable.
    """

    material = "|".join(
        [
            event_id,
            case_id,
            application_id,
            str(chain_position),
            event_type,
            actor_type,
            actor_id or "",
            _canonical_timestamp(
                occurred_at
            ),
            payload_json,
            previous_event_hash or "",
        ]
    )

    return hashlib.sha256(
        material.encode("utf-8")
    ).hexdigest()


class AuditRepository:
    """
    DuckDB-backed append-only audit repository.

    Events are hash-linked using append order rather than occurred_at
    time. This allows late-arriving or backdated business events to be
    recorded without corrupting chain verification.

    The hash chain is tamper-evident. It does not make the underlying
    database physically immutable.
    """

    def __init__(
        self,
        db_path: str | Path = DEFAULT_AUDIT_DB_PATH,
    ) -> None:
        self.db_path = Path(
            db_path
        )

        self.db_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._ensure_schema()

    def _connect(
        self,
    ) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(
            str(self.db_path)
        )

    def _ensure_schema(
        self,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id VARCHAR PRIMARY KEY,
                    schema_version VARCHAR NOT NULL,
                    case_id VARCHAR NOT NULL,
                    application_id VARCHAR NOT NULL,
                    chain_position BIGINT,
                    event_type VARCHAR NOT NULL,
                    actor_type VARCHAR NOT NULL,
                    actor_id VARCHAR,
                    occurred_at TIMESTAMPTZ NOT NULL,
                    payload_json VARCHAR NOT NULL,
                    previous_event_hash VARCHAR,
                    event_hash VARCHAR NOT NULL
                )
                """
            )

            columns = {
                row[1]
                for row in connection.execute(
                    """
                    PRAGMA table_info('audit_events')
                    """
                ).fetchall()
            }

            if "chain_position" not in columns:
                connection.execute(
                    """
                    ALTER TABLE audit_events
                    ADD COLUMN chain_position BIGINT
                    """
                )

                connection.execute(
                    """
                    UPDATE audit_events
                    SET chain_position = ranked.chain_position
                    FROM (
                        SELECT
                            event_id,
                            ROW_NUMBER() OVER (
                                PARTITION BY case_id
                                ORDER BY occurred_at, event_id
                            ) AS chain_position
                        FROM audit_events
                    ) AS ranked
                    WHERE
                        audit_events.event_id = ranked.event_id
                        AND audit_events.chain_position IS NULL
                    """
                )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    audit_events_case_index
                ON audit_events(
                    case_id,
                    chain_position
                )
                """
            )

    def _next_chain_position(
        self,
        case_id: str,
    ) -> int:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    COALESCE(
                        MAX(chain_position),
                        0
                    ) + 1
                FROM audit_events
                WHERE case_id = ?
                """,
                [case_id],
            ).fetchone()

        if row is None:
            return 1

        return int(
            row[0]
        )

    def _latest_event_hash(
        self,
        case_id: str,
    ) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT event_hash
                FROM audit_events
                WHERE case_id = ?
                ORDER BY chain_position DESC
                LIMIT 1
                """,
                [case_id],
            ).fetchone()

        if row is None:
            return None

        return str(
            row[0]
        )

    def append_event(
        self,
        *,
        case_id: str,
        application_id: str,
        event_type: AuditEventType,
        actor_type: AuditActorType,
        payload: dict[str, Any],
        actor_id: str | None = None,
        occurred_at: datetime | None = None,
    ) -> AuditEvent:
        timestamp = (
            occurred_at
            if occurred_at is not None
            else datetime.now(UTC)
        )

        timestamp = _normalize_timestamp(
            timestamp
        )

        event_id = str(
            uuid4()
        )

        chain_position = (
            self._next_chain_position(
                case_id
            )
        )

        previous_hash = (
            self._latest_event_hash(
                case_id
            )
        )

        payload_json = _canonical_payload(
            payload
        )

        event_hash = _calculate_event_hash(
            event_id=event_id,
            case_id=case_id,
            application_id=application_id,
            chain_position=chain_position,
            event_type=event_type.value,
            actor_type=actor_type.value,
            actor_id=actor_id,
            occurred_at=timestamp,
            payload_json=payload_json,
            previous_event_hash=previous_hash,
        )

        event = AuditEvent(
            event_id=event_id,
            case_id=case_id,
            application_id=application_id,
            chain_position=chain_position,
            event_type=event_type,
            actor_type=actor_type,
            actor_id=actor_id,
            occurred_at=timestamp,
            payload=json.loads(
                payload_json
            ),
            previous_event_hash=previous_hash,
            event_hash=event_hash,
        )

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO audit_events (
                    event_id,
                    schema_version,
                    case_id,
                    application_id,
                    chain_position,
                    event_type,
                    actor_type,
                    actor_id,
                    occurred_at,
                    payload_json,
                    previous_event_hash,
                    event_hash
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                [
                    event.event_id,
                    event.schema_version,
                    event.case_id,
                    event.application_id,
                    event.chain_position,
                    event.event_type.value,
                    event.actor_type.value,
                    event.actor_id,
                    event.occurred_at,
                    payload_json,
                    event.previous_event_hash,
                    event.event_hash,
                ],
            )

        return event

    def record_human_review(
        self,
        record: HumanReviewRecord,
    ) -> AuditEvent:
        payload = {
            "decision": (
                record.decision.value
            ),
            "rationale": (
                record.rationale
            ),
            "external_action_executed": (
                record.external_action_executed
            ),
        }

        return self.append_event(
            case_id=record.case_id,
            application_id=record.application_id,
            event_type=(
                AuditEventType.HUMAN_REVIEW_RECORDED
            ),
            actor_type=(
                AuditActorType.HUMAN
            ),
            actor_id=record.reviewer_id,
            occurred_at=record.recorded_at,
            payload=payload,
        )

    def list_case_events(
        self,
        case_id: str,
    ) -> list[AuditEvent]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    event_id,
                    schema_version,
                    case_id,
                    application_id,
                    chain_position,
                    event_type,
                    actor_type,
                    actor_id,
                    occurred_at,
                    payload_json,
                    previous_event_hash,
                    event_hash
                FROM audit_events
                WHERE case_id = ?
                ORDER BY chain_position ASC
                """,
                [case_id],
            ).fetchall()

        events: list[AuditEvent] = []

        for row in rows:
            occurred_at = _normalize_timestamp(
                row[8]
            )

            events.append(
                AuditEvent(
                    event_id=row[0],
                    schema_version=row[1],
                    case_id=row[2],
                    application_id=row[3],
                    chain_position=int(
                        row[4]
                    ),
                    event_type=row[5],
                    actor_type=row[6],
                    actor_id=row[7],
                    occurred_at=occurred_at,
                    payload=json.loads(
                        row[9]
                    ),
                    previous_event_hash=row[10],
                    event_hash=row[11],
                )
            )

        return events

    def verify_case_chain(
        self,
        case_id: str,
    ) -> bool:
        events = self.list_case_events(
            case_id
        )

        expected_previous_hash: str | None = None
        expected_position = 1

        for event in events:
            if (
                event.chain_position
                != expected_position
            ):
                return False

            if (
                event.previous_event_hash
                != expected_previous_hash
            ):
                return False

            payload_json = _canonical_payload(
                event.payload
            )

            expected_hash = _calculate_event_hash(
                event_id=event.event_id,
                case_id=event.case_id,
                application_id=event.application_id,
                chain_position=event.chain_position,
                event_type=event.event_type.value,
                actor_type=event.actor_type.value,
                actor_id=event.actor_id,
                occurred_at=event.occurred_at,
                payload_json=payload_json,
                previous_event_hash=(
                    event.previous_event_hash
                ),
            )

            if (
                expected_hash
                != event.event_hash
            ):
                return False

            expected_previous_hash = (
                event.event_hash
            )

            expected_position += 1

        return True