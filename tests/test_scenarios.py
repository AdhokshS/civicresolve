from decimal import Decimal

from civicresolve.data.scenarios import build_integration_exception_case
from civicresolve.models.case import (
    ApplicationStatus,
    CaseSeverity,
    CaseStatus,
    DocumentStatus,
    EventType,
    PaymentStatus,
    WorkflowPaymentState,
    WorkflowStage,
)


def test_integration_exception_case_has_expected_identity():
    case = build_integration_exception_case()

    assert case.case_id == "CASE-1047"
    assert case.application.application_id == "LIC-2026-1047"

    assert (
        case.application.applicant.business_name
        == "Harbor Street Coffee LLC"
    )

    assert case.synthetic is True


def test_integration_exception_case_has_successful_payment():
    case = build_integration_exception_case()

    assert case.payment is not None

    assert case.payment.transaction_id == "PAY-88219"
    assert case.payment.status == PaymentStatus.SUCCESS
    assert case.payment.amount == Decimal("250.00")


def test_integration_exception_case_workflow_is_stuck():
    case = build_integration_exception_case()

    assert (
        case.application.status
        == ApplicationStatus.AWAITING_PAYMENT
    )

    assert case.workflow.current_stage == WorkflowStage.PAYMENT

    assert (
        case.workflow.payment_state
        == WorkflowPaymentState.AWAITING_PAYMENT
    )


def test_integration_exception_case_documents_are_valid():
    case = build_integration_exception_case()

    assert len(case.documents) == 2

    assert all(
        document.status == DocumentStatus.VALID
        for document in case.documents
    )


def test_integration_exception_case_contains_failed_sync_history():
    case = build_integration_exception_case()

    event_types = {
        event.event_type
        for event in case.events
    }

    assert EventType.PAYMENT_SUCCEEDED in event_types
    assert EventType.WORKFLOW_UPDATE_ATTEMPTED in event_types
    assert EventType.RETRY_SCHEDULED in event_types
    assert EventType.RETRY_EXHAUSTED in event_types

    failed_events = [
        event
        for event in case.events
        if event.success is False
    ]

    assert len(failed_events) == 2


def test_integration_exception_case_is_open_high_severity():
    case = build_integration_exception_case()

    assert case.status == CaseStatus.OPEN
    assert case.severity == CaseSeverity.HIGH