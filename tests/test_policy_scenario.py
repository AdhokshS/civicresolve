from civicresolve.data.scenarios import (
    build_policy_exception_case,
)
from civicresolve.models.case import (
    DocumentStatus,
    PaymentStatus,
    WorkflowPaymentState,
    WorkflowStage,
)
from civicresolve.models.evidence import (
    EvidenceType,
    SourceSystem,
)
from civicresolve.rules.payment import (
    detect_payment_workflow_state_mismatch,
)
from civicresolve.services.evidence_service import (
    build_evidence_bundle,
)


def test_policy_case_payment_is_successful_and_synchronized():
    case = build_policy_exception_case()

    assert case.payment is not None
    assert case.payment.status == PaymentStatus.SUCCESS

    assert (
        case.workflow.payment_state
        == WorkflowPaymentState.CONFIRMED
    )

    assert case.workflow.current_stage == WorkflowStage.REVIEW


def test_policy_case_contains_expired_required_insurance():
    case = build_policy_exception_case()

    insurance = next(
        document
        for document in case.documents
        if document.document_type == "Proof of Insurance"
    )

    assert insurance.required is True
    assert insurance.status == DocumentStatus.EXPIRED


def test_policy_case_contains_explicit_insurance_policy():
    case = build_policy_exception_case()

    assert len(case.policy_requirements) == 1

    policy = case.policy_requirements[0]

    assert policy.policy_id == "POL-LIC-INS-001"
    assert policy.required_document_type == "Proof of Insurance"
    assert policy.requires_valid_document is True
    assert policy.blocking is True


def test_policy_requirement_is_reconstructed_as_evidence():
    case = build_policy_exception_case()

    bundle = build_evidence_bundle(case)

    evidence = bundle.get("EVD-POL-LIC-INS-001")

    assert evidence is not None

    assert evidence.source_system == SourceSystem.POLICY

    assert (
        evidence.evidence_type
        == EvidenceType.POLICY_RULE
    )

    assert (
        evidence.fields["required_document_type"]
        == "Proof of Insurance"
    )

    assert (
        evidence.fields["requires_valid_document"]
        is True
    )


def test_expired_insurance_is_reconstructed_as_evidence():
    case = build_policy_exception_case()

    bundle = build_evidence_bundle(case)

    evidence = bundle.get("EVD-DOC-4451")

    assert evidence is not None

    assert evidence.fields["document_status"] == "EXPIRED"


def test_payment_mismatch_rule_does_not_trigger_for_policy_case():
    case = build_policy_exception_case()

    bundle = build_evidence_bundle(case)

    finding = detect_payment_workflow_state_mismatch(
        case,
        bundle,
    )

    assert finding.triggered is False