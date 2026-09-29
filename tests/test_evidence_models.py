from datetime import datetime, timezone

from civicresolve.models.evidence import (
    EvidenceBundle,
    EvidenceItem,
    EvidenceReference,
    EvidenceType,
    SourceSystem,
)


def test_evidence_item_can_be_created():
    timestamp = datetime.now(timezone.utc)

    evidence = EvidenceItem(
        evidence_id="EVD-PAY-88219",
        case_id="CASE-1047",
        application_id="LIC-2026-1047",
        source_system=SourceSystem.PAYMENTS,
        evidence_type=EvidenceType.PAYMENT_RECORD,
        source_record_id="PAY-88219",
        observed_at=timestamp,
        captured_at=timestamp,
        summary="Payment processor confirmed successful payment.",
        fields={
            "status": "SUCCESS",
            "amount": "250.00",
            "currency": "USD",
        },
        synthetic=True,
    )

    assert evidence.evidence_id == "EVD-PAY-88219"
    assert evidence.source_system == SourceSystem.PAYMENTS
    assert evidence.fields["status"] == "SUCCESS"
    assert evidence.synthetic is True


def test_evidence_reference_can_point_to_evidence():
    reference = EvidenceReference(
        evidence_id="EVD-PAY-88219",
        reason="Payment is confirmed by the payment processor.",
    )

    assert reference.evidence_id == "EVD-PAY-88219"


def test_evidence_bundle_can_find_evidence_by_id():
    timestamp = datetime.now(timezone.utc)

    payment_evidence = EvidenceItem(
        evidence_id="EVD-PAY-88219",
        case_id="CASE-1047",
        application_id="LIC-2026-1047",
        source_system=SourceSystem.PAYMENTS,
        evidence_type=EvidenceType.PAYMENT_RECORD,
        source_record_id="PAY-88219",
        observed_at=timestamp,
        captured_at=timestamp,
        summary="Payment processor confirmed successful payment.",
        fields={
            "status": "SUCCESS",
            "amount": "250.00",
        },
    )

    workflow_evidence = EvidenceItem(
        evidence_id="EVD-WF-1047",
        case_id="CASE-1047",
        application_id="LIC-2026-1047",
        source_system=SourceSystem.WORKFLOW,
        evidence_type=EvidenceType.WORKFLOW_STATE,
        source_record_id="WF-1047",
        observed_at=timestamp,
        captured_at=timestamp,
        summary="Workflow is still waiting for payment.",
        fields={
            "payment_state": "AWAITING_PAYMENT",
            "current_stage": "PAYMENT",
        },
    )

    bundle = EvidenceBundle(
        case_id="CASE-1047",
        application_id="LIC-2026-1047",
        items=[
            payment_evidence,
            workflow_evidence,
        ],
    )

    assert bundle.contains("EVD-PAY-88219") is True
    assert bundle.contains("EVD-WF-1047") is True

    assert bundle.contains("EVD-NOT-REAL") is False

    found = bundle.get("EVD-WF-1047")

    assert found is not None
    assert found.source_system == SourceSystem.WORKFLOW