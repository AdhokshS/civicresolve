from datetime import date, datetime, timezone
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


def build_data_linkage_exception_case() -> BusinessLicenseCase:
    """
    Data-linkage demo case.

    A successful payment record is associated with the case, but the
    payment carries a different application reference and remains
    unmatched for reconciliation.
    """

    submitted_at = datetime(
        2026,
        9,
        26,
        13,
        10,
        0,
        tzinfo=timezone.utc,
    )

    payment_succeeded_at = datetime(
        2026,
        9,
        26,
        13,
        12,
        41,
        tzinfo=timezone.utc,
    )

    exception_opened_at = datetime(
        2026,
        9,
        26,
        13,
        15,
        0,
        tzinfo=timezone.utc,
    )

    applicant = Applicant(
        applicant_id="BUS-1004",
        business_name="Summit Printworks LLC",
    )

    application = LicenseApplication(
        application_id="LIC-2026-1074",
        license_type="Business License Renewal",
        applicant=applicant,
        submitted_at=submitted_at,
        status=ApplicationStatus.AWAITING_PAYMENT,
        required_document_types=[
            "Proof of Insurance",
            "Business Registration",
        ],
    )

    payment = Payment(
        transaction_id="PAY-88410",
        application_id="LIC-2026-0998",
        amount=Decimal("250.00"),
        currency="USD",
        status=PaymentStatus.SUCCESS,
        reconciliation_state=PaymentReconciliationState.UNMATCHED,
        processor_response_code="APPROVED",
        processed_at=payment_succeeded_at,
    )

    insurance_document = Document(
        document_id="DOC-4511",
        application_id="LIC-2026-1074",
        document_type="Proof of Insurance",
        status=DocumentStatus.VALID,
        required=True,
        issued_on=date(2026, 3, 1),
        expires_on=date(2027, 3, 1),
    )

    registration_document = Document(
        document_id="DOC-4512",
        application_id="LIC-2026-1074",
        document_type="Business Registration",
        status=DocumentStatus.VALID,
        required=True,
        issued_on=date(2025, 7, 14),
        expires_on=None,
    )

    workflow = WorkflowState(
        workflow_id="WF-1074",
        application_id="LIC-2026-1074",
        current_stage=WorkflowStage.PAYMENT,
        expected_next_stage=WorkflowStage.REVIEW,
        payment_state=WorkflowPaymentState.AWAITING_PAYMENT,
        assigned_team="Revenue Operations",
        assigned_role="Payment Reconciliation Specialist",
        updated_at=exception_opened_at,
    )

    events = [
        WorkflowEvent(
            event_id="EVT-91600",
            application_id="LIC-2026-1074",
            source_system="forms",
            event_type=EventType.FORM_SUBMITTED,
            occurred_at=submitted_at,
            success=True,
            message="Business-license renewal submitted successfully.",
        ),
        WorkflowEvent(
            event_id="EVT-91601",
            application_id="LIC-2026-1074",
            source_system="payments",
            event_type=EventType.PAYMENT_SUCCEEDED,
            occurred_at=payment_succeeded_at,
            success=True,
            message=(
                "Payment processor confirmed successful payment, "
                "but the supplied application reference does not "
                "match the case application."
            ),
            details={
                "transaction_id": "PAY-88410",
                "amount": "250.00",
                "currency": "USD",
                "payment_application_reference": "LIC-2026-0998",
                "case_application_reference": "LIC-2026-1074",
                "reconciliation_state": "UNMATCHED",
            },
        ),
    ]

    return BusinessLicenseCase(
        case_id="CASE-1074",
        application=application,
        payment=payment,
        documents=[
            insurance_document,
            registration_document,
        ],
        policy_requirements=[],
        workflow=workflow,
        events=events,
        severity=CaseSeverity.HIGH,
        status=CaseStatus.OPEN,
        exception_opened_at=exception_opened_at,
        synthetic=True,
    )