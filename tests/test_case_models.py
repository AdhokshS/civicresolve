from datetime import datetime, timezone
from decimal import Decimal

from civicresolve.models.case import (
    Applicant,
    ApplicationStatus,
    BusinessLicenseCase,
    CaseSeverity,
    CaseStatus,
    Document,
    DocumentStatus,
    EventType,
    LicenseApplication,
    Payment,
    PaymentReconciliationState,
    PaymentStatus,
    WorkflowEvent,
    WorkflowPaymentState,
    WorkflowStage,
    WorkflowState,
)


def test_business_license_case_can_be_created():
    timestamp = datetime.now(timezone.utc)

    applicant = Applicant(
        applicant_id="BUS-1001",
        business_name="Harbor Street Coffee LLC",
    )

    application = LicenseApplication(
        application_id="LIC-2026-1047",
        license_type="Business License Renewal",
        applicant=applicant,
        submitted_at=timestamp,
        status=ApplicationStatus.AWAITING_PAYMENT,
        required_document_types=[
            "Proof of Insurance",
            "Business Registration",
        ],
    )

    payment = Payment(
        transaction_id="PAY-88219",
        application_id="LIC-2026-1047",
        amount=Decimal("250.00"),
        currency="USD",
        status=PaymentStatus.SUCCESS,
        reconciliation_state=PaymentReconciliationState.MATCHED,
        processor_response_code="APPROVED",
        processed_at=timestamp,
    )

    insurance_document = Document(
        document_id="DOC-4401",
        application_id="LIC-2026-1047",
        document_type="Proof of Insurance",
        status=DocumentStatus.VALID,
        required=True,
    )

    workflow = WorkflowState(
        workflow_id="WF-1047",
        application_id="LIC-2026-1047",
        current_stage=WorkflowStage.PAYMENT,
        expected_next_stage=WorkflowStage.REVIEW,
        payment_state=WorkflowPaymentState.AWAITING_PAYMENT,
        assigned_team="Licensing Operations",
        assigned_role="Licensing Specialist",
        updated_at=timestamp,
    )

    payment_event = WorkflowEvent(
        event_id="EVT-91372",
        application_id="LIC-2026-1047",
        source_system="payments",
        event_type=EventType.PAYMENT_SUCCEEDED,
        occurred_at=timestamp,
        success=True,
        message="Payment processor confirmed successful payment.",
        details={
            "transaction_id": "PAY-88219",
            "amount": "250.00",
        },
    )

    case = BusinessLicenseCase(
        case_id="CASE-1047",
        application=application,
        payment=payment,
        documents=[insurance_document],
        workflow=workflow,
        events=[payment_event],
        severity=CaseSeverity.HIGH,
        status=CaseStatus.OPEN,
        exception_opened_at=timestamp,
        synthetic=True,
    )

    assert case.case_id == "CASE-1047"

    assert case.payment is not None
    assert case.payment.status == PaymentStatus.SUCCESS

    assert (
        case.workflow.payment_state
        == WorkflowPaymentState.AWAITING_PAYMENT
    )

    assert case.synthetic is True