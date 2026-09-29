from civicresolve.data.data_linkage_scenario import (
    build_data_linkage_exception_case,
)
from civicresolve.models.case import (
    DocumentStatus,
    PaymentReconciliationState,
    PaymentStatus,
    WorkflowPaymentState,
)


def test_data_linkage_case_contains_successful_payment():
    case = build_data_linkage_exception_case()

    assert case.payment is not None
    assert case.payment.status == PaymentStatus.SUCCESS


def test_data_linkage_case_contains_mismatched_application_reference():
    case = build_data_linkage_exception_case()

    assert case.payment is not None

    assert (
        case.payment.application_id
        != case.application.application_id
    )

    assert case.payment.application_id == "LIC-2026-0998"

    assert (
        case.application.application_id
        == "LIC-2026-1074"
    )


def test_data_linkage_case_payment_is_unmatched():
    case = build_data_linkage_exception_case()

    assert case.payment is not None

    assert (
        case.payment.reconciliation_state
        == PaymentReconciliationState.UNMATCHED
    )


def test_data_linkage_case_workflow_still_waits_for_payment():
    case = build_data_linkage_exception_case()

    assert (
        case.workflow.payment_state
        == WorkflowPaymentState.AWAITING_PAYMENT
    )


def test_data_linkage_case_documents_are_valid():
    case = build_data_linkage_exception_case()

    assert len(case.documents) == 2

    assert all(
        document.status == DocumentStatus.VALID
        for document in case.documents
    )