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
    PolicyRequirement,
    PolicyRequirementType,
    WorkflowEvent,
    WorkflowPaymentState,
    WorkflowStage,
    WorkflowState,
)


def build_integration_exception_case() -> BusinessLicenseCase:
    """
    Hero demo case.

    Payment succeeds in the payment system, but the licensing workflow
    remains stuck in AWAITING_PAYMENT after a simulated integration failure.
    """

    submitted_at = datetime(
        2026,
        9,
        24,
        10,
        12,
        5,
        tzinfo=timezone.utc,
    )

    payment_succeeded_at = datetime(
        2026,
        9,
        24,
        10,
        14,
        32,
        tzinfo=timezone.utc,
    )

    workflow_update_attempted_at = datetime(
        2026,
        9,
        24,
        10,
        14,
        34,
        tzinfo=timezone.utc,
    )

    retry_scheduled_at = datetime(
        2026,
        9,
        24,
        10,
        14,
        35,
        tzinfo=timezone.utc,
    )

    retry_exhausted_at = datetime(
        2026,
        9,
        24,
        10,
        19,
        35,
        tzinfo=timezone.utc,
    )

    applicant = Applicant(
        applicant_id="BUS-1001",
        business_name="Harbor Street Coffee LLC",
    )

    application = LicenseApplication(
        application_id="LIC-2026-1047",
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
        transaction_id="PAY-88219",
        application_id="LIC-2026-1047",
        amount=Decimal("250.00"),
        currency="USD",
        status=PaymentStatus.SUCCESS,
        reconciliation_state=PaymentReconciliationState.MATCHED,
        processor_response_code="APPROVED",
        processed_at=payment_succeeded_at,
    )

    insurance_document = Document(
        document_id="DOC-4401",
        application_id="LIC-2026-1047",
        document_type="Proof of Insurance",
        status=DocumentStatus.VALID,
        required=True,
        issued_on=date(2026, 1, 15),
        expires_on=date(2027, 1, 15),
    )

    registration_document = Document(
        document_id="DOC-4402",
        application_id="LIC-2026-1047",
        document_type="Business Registration",
        status=DocumentStatus.VALID,
        required=True,
        issued_on=date(2024, 6, 1),
        expires_on=None,
    )

    workflow = WorkflowState(
        workflow_id="WF-1047",
        application_id="LIC-2026-1047",
        current_stage=WorkflowStage.PAYMENT,
        expected_next_stage=WorkflowStage.REVIEW,
        payment_state=WorkflowPaymentState.AWAITING_PAYMENT,
        assigned_team="Licensing Operations",
        assigned_role="Licensing Specialist",
        updated_at=retry_exhausted_at,
    )

    events = [
        WorkflowEvent(
            event_id="EVT-91370",
            application_id="LIC-2026-1047",
            source_system="forms",
            event_type=EventType.FORM_SUBMITTED,
            occurred_at=submitted_at,
            success=True,
            message="Business-license renewal submitted successfully.",
        ),
        WorkflowEvent(
            event_id="EVT-91371",
            application_id="LIC-2026-1047",
            source_system="payments",
            event_type=EventType.PAYMENT_SUCCEEDED,
            occurred_at=payment_succeeded_at,
            success=True,
            message="Payment processor confirmed successful payment.",
            details={
                "transaction_id": "PAY-88219",
                "amount": "250.00",
                "currency": "USD",
                "processor_response_code": "APPROVED",
            },
        ),
        WorkflowEvent(
            event_id="EVT-91372",
            application_id="LIC-2026-1047",
            source_system="workflow_integration",
            event_type=EventType.WORKFLOW_UPDATE_ATTEMPTED,
            occurred_at=workflow_update_attempted_at,
            success=False,
            message=(
                "Attempt to synchronize confirmed payment "
                "with licensing workflow failed."
            ),
            details={
                "target_state": "PAYMENT_CONFIRMED",
                "http_status": 503,
            },
        ),
        WorkflowEvent(
            event_id="EVT-91373",
            application_id="LIC-2026-1047",
            source_system="workflow_integration",
            event_type=EventType.RETRY_SCHEDULED,
            occurred_at=retry_scheduled_at,
            success=True,
            message="Retry scheduled after workflow synchronization failure.",
            details={
                "retry_number": 1,
                "retry_delay_seconds": 300,
            },
        ),
        WorkflowEvent(
            event_id="EVT-91374",
            application_id="LIC-2026-1047",
            source_system="workflow_integration",
            event_type=EventType.RETRY_EXHAUSTED,
            occurred_at=retry_exhausted_at,
            success=False,
            message=(
                "Workflow synchronization retry exhausted. "
                "Manual investigation required."
            ),
            details={
                "retry_number": 1,
                "final_http_status": 503,
            },
        ),
    ]

    return BusinessLicenseCase(
        case_id="CASE-1047",
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
        exception_opened_at=retry_exhausted_at,
        synthetic=True,
    )


def build_policy_exception_case() -> BusinessLicenseCase:
    """
    Policy-blocker demo case.

    Payment has succeeded and the payment workflow is synchronized,
    but the application cannot safely progress because a required
    insurance document is expired.
    """

    submitted_at = datetime(
        2026,
        9,
        25,
        14,
        30,
        0,
        tzinfo=timezone.utc,
    )

    payment_succeeded_at = datetime(
        2026,
        9,
        25,
        14,
        32,
        18,
        tzinfo=timezone.utc,
    )

    review_started_at = datetime(
        2026,
        9,
        25,
        14,
        34,
        10,
        tzinfo=timezone.utc,
    )

    document_checked_at = datetime(
        2026,
        9,
        25,
        14,
        35,
        2,
        tzinfo=timezone.utc,
    )

    applicant = Applicant(
        applicant_id="BUS-1002",
        business_name="Cedar & Pine Catering LLC",
    )

    application = LicenseApplication(
        application_id="LIC-2026-1052",
        license_type="Business License Renewal",
        applicant=applicant,
        submitted_at=submitted_at,
        status=ApplicationStatus.UNDER_REVIEW,
        required_document_types=[
            "Proof of Insurance",
            "Business Registration",
        ],
    )

    payment = Payment(
        transaction_id="PAY-88304",
        application_id="LIC-2026-1052",
        amount=Decimal("250.00"),
        currency="USD",
        status=PaymentStatus.SUCCESS,
        reconciliation_state=PaymentReconciliationState.RECONCILED,
        processor_response_code="APPROVED",
        processed_at=payment_succeeded_at,
    )

    expired_insurance = Document(
        document_id="DOC-4451",
        application_id="LIC-2026-1052",
        document_type="Proof of Insurance",
        status=DocumentStatus.EXPIRED,
        required=True,
        issued_on=date(2025, 9, 1),
        expires_on=date(2026, 8, 31),
    )

    registration_document = Document(
        document_id="DOC-4452",
        application_id="LIC-2026-1052",
        document_type="Business Registration",
        status=DocumentStatus.VALID,
        required=True,
        issued_on=date(2025, 5, 10),
        expires_on=None,
    )

    insurance_policy = PolicyRequirement(
        policy_id="POL-LIC-INS-001",
        name="Active proof of insurance required",
        description=(
            "A valid proof-of-insurance document must be on file "
            "before a business-license renewal can advance "
            "to approval."
        ),
        requirement_type=PolicyRequirementType.REQUIRED_DOCUMENT,
        required_document_type="Proof of Insurance",
        requires_valid_document=True,
        blocking=True,
        effective_from=date(2026, 1, 1),
        effective_to=None,
    )

    workflow = WorkflowState(
        workflow_id="WF-1052",
        application_id="LIC-2026-1052",
        current_stage=WorkflowStage.REVIEW,
        expected_next_stage=WorkflowStage.APPROVAL,
        payment_state=WorkflowPaymentState.CONFIRMED,
        assigned_team="Licensing Operations",
        assigned_role="Licensing Specialist",
        updated_at=document_checked_at,
    )

    events = [
        WorkflowEvent(
            event_id="EVT-91420",
            application_id="LIC-2026-1052",
            source_system="forms",
            event_type=EventType.FORM_SUBMITTED,
            occurred_at=submitted_at,
            success=True,
            message="Business-license renewal submitted successfully.",
        ),
        WorkflowEvent(
            event_id="EVT-91421",
            application_id="LIC-2026-1052",
            source_system="payments",
            event_type=EventType.PAYMENT_SUCCEEDED,
            occurred_at=payment_succeeded_at,
            success=True,
            message="Payment processor confirmed successful payment.",
            details={
                "transaction_id": "PAY-88304",
                "amount": "250.00",
                "currency": "USD",
            },
        ),
        WorkflowEvent(
            event_id="EVT-91422",
            application_id="LIC-2026-1052",
            source_system="workflow",
            event_type=EventType.WORKFLOW_ADVANCED,
            occurred_at=review_started_at,
            success=True,
            message=(
                "Payment confirmed and application advanced "
                "to licensing review."
            ),
            details={
                "from_stage": "PAYMENT",
                "to_stage": "REVIEW",
            },
        ),
        WorkflowEvent(
            event_id="EVT-91423",
            application_id="LIC-2026-1052",
            source_system="documents",
            event_type=EventType.DOCUMENT_VALIDATED,
            occurred_at=document_checked_at,
            success=False,
            message=(
                "Proof of Insurance failed document validation "
                "because the document is expired."
            ),
            details={
                "document_id": "DOC-4451",
                "document_status": "EXPIRED",
            },
        ),
    ]

    return BusinessLicenseCase(
        case_id="CASE-1052",
        application=application,
        payment=payment,
        documents=[
            expired_insurance,
            registration_document,
        ],
        policy_requirements=[
            insurance_policy,
        ],
        workflow=workflow,
        events=events,
        severity=CaseSeverity.HIGH,
        status=CaseStatus.OPEN,
        exception_opened_at=document_checked_at,
        synthetic=True,
    )


def build_ownership_exception_case() -> BusinessLicenseCase:
    """
    Ownership/process demo case.

    Payment and documents are valid and review has completed, but the
    application has reached the approval stage without a responsible
    team or role assigned to continue the workflow.
    """

    submitted_at = datetime(
        2026,
        9,
        20,
        9,
        0,
        0,
        tzinfo=timezone.utc,
    )

    payment_succeeded_at = datetime(
        2026,
        9,
        20,
        9,
        2,
        14,
        tzinfo=timezone.utc,
    )

    review_started_at = datetime(
        2026,
        9,
        20,
        9,
        5,
        0,
        tzinfo=timezone.utc,
    )

    approval_stage_entered_at = datetime(
        2026,
        9,
        20,
        11,
        15,
        0,
        tzinfo=timezone.utc,
    )

    assignment_cleared_at = datetime(
        2026,
        9,
        20,
        11,
        16,
        0,
        tzinfo=timezone.utc,
    )

    exception_opened_at = datetime(
        2026,
        9,
        25,
        11,
        16,
        0,
        tzinfo=timezone.utc,
    )

    applicant = Applicant(
        applicant_id="BUS-1003",
        business_name="Lakeview Bicycle Repair LLC",
    )

    application = LicenseApplication(
        application_id="LIC-2026-1061",
        license_type="Business License Renewal",
        applicant=applicant,
        submitted_at=submitted_at,
        status=ApplicationStatus.APPROVAL_PENDING,
        required_document_types=[
            "Proof of Insurance",
            "Business Registration",
        ],
    )

    payment = Payment(
        transaction_id="PAY-88361",
        application_id="LIC-2026-1061",
        amount=Decimal("250.00"),
        currency="USD",
        status=PaymentStatus.SUCCESS,
        reconciliation_state=PaymentReconciliationState.RECONCILED,
        processor_response_code="APPROVED",
        processed_at=payment_succeeded_at,
    )

    insurance_document = Document(
        document_id="DOC-4481",
        application_id="LIC-2026-1061",
        document_type="Proof of Insurance",
        status=DocumentStatus.VALID,
        required=True,
        issued_on=date(2026, 2, 1),
        expires_on=date(2027, 2, 1),
    )

    registration_document = Document(
        document_id="DOC-4482",
        application_id="LIC-2026-1061",
        document_type="Business Registration",
        status=DocumentStatus.VALID,
        required=True,
        issued_on=date(2025, 4, 10),
        expires_on=None,
    )

    workflow = WorkflowState(
        workflow_id="WF-1061",
        application_id="LIC-2026-1061",
        current_stage=WorkflowStage.APPROVAL,
        expected_next_stage=WorkflowStage.COMPLETE,
        payment_state=WorkflowPaymentState.CONFIRMED,
        assigned_team=None,
        assigned_role=None,
        updated_at=assignment_cleared_at,
    )

    events = [
        WorkflowEvent(
            event_id="EVT-91500",
            application_id="LIC-2026-1061",
            source_system="forms",
            event_type=EventType.FORM_SUBMITTED,
            occurred_at=submitted_at,
            success=True,
            message="Business-license renewal submitted successfully.",
        ),
        WorkflowEvent(
            event_id="EVT-91501",
            application_id="LIC-2026-1061",
            source_system="payments",
            event_type=EventType.PAYMENT_SUCCEEDED,
            occurred_at=payment_succeeded_at,
            success=True,
            message="Payment processor confirmed successful payment.",
            details={
                "transaction_id": "PAY-88361",
                "amount": "250.00",
                "currency": "USD",
            },
        ),
        WorkflowEvent(
            event_id="EVT-91502",
            application_id="LIC-2026-1061",
            source_system="workflow",
            event_type=EventType.WORKFLOW_ADVANCED,
            occurred_at=review_started_at,
            success=True,
            message=(
                "Payment confirmed and application advanced "
                "to licensing review."
            ),
            details={
                "from_stage": "PAYMENT",
                "to_stage": "REVIEW",
            },
        ),
        WorkflowEvent(
            event_id="EVT-91503",
            application_id="LIC-2026-1061",
            source_system="workflow",
            event_type=EventType.WORKFLOW_ADVANCED,
            occurred_at=approval_stage_entered_at,
            success=True,
            message=(
                "Application review completed and workflow "
                "advanced to approval."
            ),
            details={
                "from_stage": "REVIEW",
                "to_stage": "APPROVAL",
            },
        ),
        WorkflowEvent(
            event_id="EVT-91504",
            application_id="LIC-2026-1061",
            source_system="workflow",
            event_type=EventType.OWNER_REMOVED,
            occurred_at=assignment_cleared_at,
            success=True,
            message=(
                "Previous review assignment cleared after review completion. "
                "No downstream approval owner is currently assigned."
            ),
            details={
                "current_stage": "APPROVAL",
                "assigned_team": None,
                "assigned_role": None,
            },
        ),
    ]

    return BusinessLicenseCase(
        case_id="CASE-1061",
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