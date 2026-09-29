from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    """
    Base model for CivicResolve domain objects.

    extra="forbid" prevents unexpected fields from being silently accepted.
    This helps keep our synthetic records predictable and auditable.
    """

    model_config = ConfigDict(extra="forbid")


class CaseSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class CaseStatus(str, Enum):
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class ApplicationStatus(str, Enum):
    SUBMITTED = "SUBMITTED"
    AWAITING_PAYMENT = "AWAITING_PAYMENT"
    PAYMENT_CONFIRMED = "PAYMENT_CONFIRMED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVAL_PENDING = "APPROVAL_PENDING"
    COMPLETE = "COMPLETE"
    BLOCKED = "BLOCKED"


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class PaymentReconciliationState(str, Enum):
    UNMATCHED = "UNMATCHED"
    MATCHED = "MATCHED"
    RECONCILED = "RECONCILED"


class WorkflowPaymentState(str, Enum):
    NOT_REQUIRED = "NOT_REQUIRED"
    AWAITING_PAYMENT = "AWAITING_PAYMENT"
    CONFIRMED = "CONFIRMED"


class DocumentStatus(str, Enum):
    VALID = "VALID"
    EXPIRED = "EXPIRED"
    MISSING = "MISSING"
    REJECTED = "REJECTED"

class PolicyRequirementType(str, Enum):
    REQUIRED_DOCUMENT = "REQUIRED_DOCUMENT"
    PAYMENT_REQUIRED = "PAYMENT_REQUIRED"
    APPROVAL_SEQUENCE = "APPROVAL_SEQUENCE"

class WorkflowStage(str, Enum):
    SUBMITTED = "SUBMITTED"
    PAYMENT = "PAYMENT"
    REVIEW = "REVIEW"
    APPROVAL = "APPROVAL"
    COMPLETE = "COMPLETE"


class EventType(str, Enum):
    FORM_SUBMITTED = "FORM_SUBMITTED"
    DOCUMENT_VALIDATED = "DOCUMENT_VALIDATED"

    PAYMENT_INITIATED = "PAYMENT_INITIATED"
    PAYMENT_SUCCEEDED = "PAYMENT_SUCCEEDED"
    PAYMENT_FAILED = "PAYMENT_FAILED"

    WORKFLOW_UPDATE_ATTEMPTED = "WORKFLOW_UPDATE_ATTEMPTED"
    WORKFLOW_ADVANCED = "WORKFLOW_ADVANCED"

    WEBHOOK_RECEIVED = "WEBHOOK_RECEIVED"
    WEBHOOK_FAILED = "WEBHOOK_FAILED"
    RETRY_SCHEDULED = "RETRY_SCHEDULED"
    RETRY_EXHAUSTED = "RETRY_EXHAUSTED"

    OWNER_ASSIGNED = "OWNER_ASSIGNED"
    OWNER_REMOVED = "OWNER_REMOVED"

    CASE_CREATED = "CASE_CREATED"


class Applicant(StrictModel):
    """
    Synthetic business/applicant identity.

    We intentionally keep this minimal because the prototype does not need
    sensitive constituent information.
    """

    applicant_id: str
    business_name: str


class LicenseApplication(StrictModel):
    application_id: str
    license_type: str

    applicant: Applicant

    submitted_at: AwareDatetime
    status: ApplicationStatus

    required_document_types: list[str] = Field(default_factory=list)


class Payment(StrictModel):
    transaction_id: str

    # The application reference contained in the payment system.
    # This can intentionally be incorrect in our data-linkage exception case.
    application_id: str

    amount: Decimal = Field(gt=0)
    currency: str = "USD"

    status: PaymentStatus
    reconciliation_state: PaymentReconciliationState

    processor_response_code: str | None = None
    processed_at: AwareDatetime | None = None


class Document(StrictModel):
    document_id: str
    application_id: str

    document_type: str
    status: DocumentStatus

    required: bool = True

    issued_on: date | None = None
    expires_on: date | None = None

class PolicyRequirement(StrictModel):
    """
    Synthetic policy or business-rule record used by CivicResolve.

    The policy describes a requirement. It does not itself determine
    whether a specific case is compliant.
    """

    policy_id: str
    name: str
    description: str

    requirement_type: PolicyRequirementType

    required_document_type: str | None = None
    requires_valid_document: bool = False

    blocking: bool = True

    effective_from: date
    effective_to: date | None = None

class WorkflowState(StrictModel):
    workflow_id: str
    application_id: str

    current_stage: WorkflowStage
    expected_next_stage: WorkflowStage | None = None

    payment_state: WorkflowPaymentState

    assigned_team: str | None = None
    assigned_role: str | None = None

    updated_at: AwareDatetime


class WorkflowEvent(StrictModel):
    event_id: str
    application_id: str

    source_system: str
    event_type: EventType

    occurred_at: AwareDatetime

    success: bool
    message: str

    details: dict[str, Any] = Field(default_factory=dict)


class BusinessLicenseCase(StrictModel):
    """
    Complete case snapshot used by CivicResolve.

    This brings together records from multiple simulated source systems
    without pretending that they originate from one database.
    """

    case_id: str

    application: LicenseApplication
    payment: Payment | None = None
    documents: list[Document] = Field(default_factory=list)

    policy_requirements: list[PolicyRequirement] = Field(
        default_factory=list
    )

    workflow: WorkflowState
    events: list[WorkflowEvent] = Field(default_factory=list)

    severity: CaseSeverity
    status: CaseStatus

    exception_opened_at: AwareDatetime | None = None

    # All prototype data must remain explicitly marked as synthetic.
    synthetic: bool = True