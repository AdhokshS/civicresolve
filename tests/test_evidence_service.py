from civicresolve.data.scenarios import (
    build_integration_exception_case,
)
from civicresolve.models.evidence import (
    EvidenceType,
    SourceSystem,
)
from civicresolve.services.evidence_service import (
    build_evidence_bundle,
)


def test_evidence_bundle_contains_expected_number_of_items():
    case = build_integration_exception_case()

    bundle = build_evidence_bundle(case)

    assert len(bundle.items) == 10


def test_evidence_bundle_contains_unique_ids():
    case = build_integration_exception_case()

    bundle = build_evidence_bundle(case)

    evidence_ids = [
        item.evidence_id
        for item in bundle.items
    ]

    assert len(evidence_ids) == len(set(evidence_ids))


def test_payment_evidence_preserves_successful_payment():
    case = build_integration_exception_case()

    bundle = build_evidence_bundle(case)

    evidence = bundle.get("EVD-PAY-88219")

    assert evidence is not None

    assert (
        evidence.source_system
        == SourceSystem.PAYMENTS
    )

    assert (
        evidence.evidence_type
        == EvidenceType.PAYMENT_RECORD
    )

    assert evidence.fields["payment_status"] == "SUCCESS"

    assert evidence.fields["amount"] == "250.00"

    assert (
        evidence.fields["payment_application_id"]
        == "LIC-2026-1047"
    )


def test_workflow_evidence_preserves_awaiting_payment_state():
    case = build_integration_exception_case()

    bundle = build_evidence_bundle(case)

    evidence = bundle.get("EVD-WF-1047")

    assert evidence is not None

    assert evidence.fields["current_stage"] == "PAYMENT"

    assert (
        evidence.fields["payment_state"]
        == "AWAITING_PAYMENT"
    )

    assert (
        evidence.fields["expected_next_stage"]
        == "REVIEW"
    )


def test_failed_integration_event_is_preserved_as_evidence():
    case = build_integration_exception_case()

    bundle = build_evidence_bundle(case)

    evidence = bundle.get("EVD-EVT-91372")

    assert evidence is not None

    assert (
        evidence.fields["event_type"]
        == "WORKFLOW_UPDATE_ATTEMPTED"
    )

    assert evidence.fields["success"] is False

    assert (
        evidence.fields["details"]["http_status"]
        == 503
    )


def test_retry_exhausted_event_is_preserved_as_evidence():
    case = build_integration_exception_case()

    bundle = build_evidence_bundle(case)

    evidence = bundle.get("EVD-EVT-91374")

    assert evidence is not None

    assert (
        evidence.fields["event_type"]
        == "RETRY_EXHAUSTED"
    )

    assert evidence.fields["success"] is False


def test_documents_remain_valid_in_evidence():
    case = build_integration_exception_case()

    bundle = build_evidence_bundle(case)

    insurance = bundle.get("EVD-DOC-4401")
    registration = bundle.get("EVD-DOC-4402")

    assert insurance is not None
    assert registration is not None

    assert (
        insurance.fields["document_status"]
        == "VALID"
    )

    assert (
        registration.fields["document_status"]
        == "VALID"
    )


def test_evidence_snapshot_uses_stable_capture_time():
    case = build_integration_exception_case()

    bundle = build_evidence_bundle(case)

    capture_times = {
        item.captured_at
        for item in bundle.items
    }

    assert len(capture_times) == 1

    assert (
        next(iter(capture_times))
        == case.exception_opened_at
    )