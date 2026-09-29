from civicresolve.data.scenarios import (
    build_ownership_exception_case,
)
from civicresolve.models.case import (
    DocumentStatus,
    PaymentStatus,
    WorkflowPaymentState,
    WorkflowStage,
)
from civicresolve.rules.payment import (
    detect_payment_workflow_state_mismatch,
)
from civicresolve.rules.policy import (
    detect_required_document_policy_blocker,
)
from civicresolve.services.evidence_service import (
    build_evidence_bundle,
)


def test_ownership_case_is_at_approval_stage_without_owner():
    case = build_ownership_exception_case()

    assert case.workflow.current_stage == WorkflowStage.APPROVAL
    assert case.workflow.expected_next_stage == WorkflowStage.COMPLETE

    assert case.workflow.assigned_team is None
    assert case.workflow.assigned_role is None


def test_ownership_case_payment_is_successful_and_synchronized():
    case = build_ownership_exception_case()

    assert case.payment is not None
    assert case.payment.status == PaymentStatus.SUCCESS

    assert (
        case.workflow.payment_state
        == WorkflowPaymentState.CONFIRMED
    )


def test_ownership_case_documents_are_valid():
    case = build_ownership_exception_case()

    assert len(case.documents) == 2

    assert all(
        document.status == DocumentStatus.VALID
        for document in case.documents
    )


def test_payment_rule_does_not_trigger_for_ownership_case():
    case = build_ownership_exception_case()

    bundle = build_evidence_bundle(case)

    finding = detect_payment_workflow_state_mismatch(
        case,
        bundle,
    )

    assert finding.triggered is False


def test_policy_rule_does_not_trigger_for_ownership_case():
    case = build_ownership_exception_case()

    bundle = build_evidence_bundle(case)

    finding = detect_required_document_policy_blocker(
        case,
        bundle,
    )

    assert finding.triggered is False