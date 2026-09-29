from __future__ import annotations

from datetime import datetime

from civicresolve.models.case import BusinessLicenseCase
from civicresolve.models.evidence import (
    EvidenceBundle,
    EvidenceItem,
    EvidenceType,
    SourceSystem,
)


def _get_capture_time(case: BusinessLicenseCase) -> datetime:
    """
    Return a stable capture time for the reconstructed evidence snapshot.

    For the synthetic demo, we avoid datetime.now() so that the same
    scenario produces the same evidence every time it is generated.
    """

    if case.exception_opened_at is not None:
        return case.exception_opened_at

    return case.workflow.updated_at


def build_evidence_bundle(
    case: BusinessLicenseCase,
) -> EvidenceBundle:
    """
    Reconstruct normalized evidence from the source records attached
    to a business-license case.

    This function does not determine root cause and does not make
    recommendations. It only creates observable, citable evidence.
    """

    captured_at = _get_capture_time(case)

    items: list[EvidenceItem] = []

    # ---------------------------------------------------------
    # FORM / APPLICATION EVIDENCE
    # ---------------------------------------------------------

    items.append(
        EvidenceItem(
            evidence_id=(
                f"EVD-FORM-{case.application.application_id}"
            ),
            case_id=case.case_id,
            application_id=case.application.application_id,
            source_system=SourceSystem.FORMS,
            evidence_type=EvidenceType.FORM_RECORD,
            source_record_id=case.application.application_id,
            observed_at=case.application.submitted_at,
            captured_at=captured_at,
            summary=(
                "Business-license application record and "
                "current application status."
            ),
            fields={
                "license_type": case.application.license_type,
                "business_name": (
                    case.application.applicant.business_name
                ),
                "application_status": (
                    case.application.status.value
                ),
                "required_document_types": (
                    case.application.required_document_types
                ),
            },
            synthetic=True,
        )
    )

    # ---------------------------------------------------------
    # PAYMENT EVIDENCE
    # ---------------------------------------------------------

    if case.payment is not None:
        payment_observed_at = (
            case.payment.processed_at
            if case.payment.processed_at is not None
            else captured_at
        )

        items.append(
            EvidenceItem(
                evidence_id=(
                    f"EVD-{case.payment.transaction_id}"
                ),
                case_id=case.case_id,
                application_id=case.application.application_id,
                source_system=SourceSystem.PAYMENTS,
                evidence_type=EvidenceType.PAYMENT_RECORD,
                source_record_id=case.payment.transaction_id,
                observed_at=payment_observed_at,
                captured_at=captured_at,
                summary=(
                    "Payment transaction associated with "
                    "the license application."
                ),
                fields={
                    "payment_application_id": (
                        case.payment.application_id
                    ),
                    "amount": str(case.payment.amount),
                    "currency": case.payment.currency,
                    "payment_status": case.payment.status.value,
                    "reconciliation_state": (
                        case.payment.reconciliation_state.value
                    ),
                    "processor_response_code": (
                        case.payment.processor_response_code
                    ),
                },
                synthetic=True,
            )
        )

    # ---------------------------------------------------------
    # DOCUMENT EVIDENCE
    # ---------------------------------------------------------

    for document in case.documents:
        items.append(
            EvidenceItem(
                evidence_id=f"EVD-{document.document_id}",
                case_id=case.case_id,
                application_id=case.application.application_id,
                source_system=SourceSystem.DOCUMENTS,
                evidence_type=EvidenceType.DOCUMENT_RECORD,
                source_record_id=document.document_id,
                observed_at=case.application.submitted_at,
                captured_at=captured_at,
                summary=(
                    f"Document record: {document.document_type}."
                ),
                fields={
                    "document_application_id": (
                        document.application_id
                    ),
                    "document_type": document.document_type,
                    "document_status": document.status.value,
                    "required": document.required,
                    "issued_on": (
                        document.issued_on.isoformat()
                        if document.issued_on is not None
                        else None
                    ),
                    "expires_on": (
                        document.expires_on.isoformat()
                        if document.expires_on is not None
                        else None
                    ),
                },
                synthetic=True,
            )
        )

        # ---------------------------------------------------------
    # POLICY EVIDENCE
    # ---------------------------------------------------------

    for policy in case.policy_requirements:
        items.append(
            EvidenceItem(
                evidence_id=f"EVD-{policy.policy_id}",
                case_id=case.case_id,
                application_id=case.application.application_id,
                source_system=SourceSystem.POLICY,
                evidence_type=EvidenceType.POLICY_RULE,
                source_record_id=policy.policy_id,
                observed_at=captured_at,
                captured_at=captured_at,
                summary=policy.name,
                fields={
                    "description": policy.description,
                    "requirement_type": (
                        policy.requirement_type.value
                    ),
                    "required_document_type": (
                        policy.required_document_type
                    ),
                    "requires_valid_document": (
                        policy.requires_valid_document
                    ),
                    "blocking": policy.blocking,
                    "effective_from": (
                        policy.effective_from.isoformat()
                    ),
                    "effective_to": (
                        policy.effective_to.isoformat()
                        if policy.effective_to is not None
                        else None
                    ),
                },
                synthetic=True,
            )
        )

    # ---------------------------------------------------------
    # WORKFLOW EVIDENCE
    # ---------------------------------------------------------

    items.append(
        EvidenceItem(
            evidence_id=f"EVD-{case.workflow.workflow_id}",
            case_id=case.case_id,
            application_id=case.application.application_id,
            source_system=SourceSystem.WORKFLOW,
            evidence_type=EvidenceType.WORKFLOW_STATE,
            source_record_id=case.workflow.workflow_id,
            observed_at=case.workflow.updated_at,
            captured_at=captured_at,
            summary=(
                "Current licensing workflow state."
            ),
            fields={
                "workflow_application_id": (
                    case.workflow.application_id
                ),
                "current_stage": (
                    case.workflow.current_stage.value
                ),
                "expected_next_stage": (
                    case.workflow.expected_next_stage.value
                    if case.workflow.expected_next_stage
                    is not None
                    else None
                ),
                "payment_state": (
                    case.workflow.payment_state.value
                ),
                "assigned_team": (
                    case.workflow.assigned_team
                ),
                "assigned_role": (
                    case.workflow.assigned_role
                ),
            },
            synthetic=True,
        )
    )

    # ---------------------------------------------------------
    # EVENT EVIDENCE
    # ---------------------------------------------------------

    for event in case.events:
        items.append(
            EvidenceItem(
                evidence_id=f"EVD-{event.event_id}",
                case_id=case.case_id,
                application_id=case.application.application_id,
                source_system=SourceSystem.EVENTS,
                evidence_type=EvidenceType.EVENT_RECORD,
                source_record_id=event.event_id,
                observed_at=event.occurred_at,
                captured_at=captured_at,
                summary=event.message,
                fields={
                    "event_source_system": (
                        event.source_system
                    ),
                    "event_type": event.event_type.value,
                    "success": event.success,
                    "details": event.details,
                },
                synthetic=True,
            )
        )

    return EvidenceBundle(
        case_id=case.case_id,
        application_id=case.application.application_id,
        items=items,
        synthetic=True,
    )