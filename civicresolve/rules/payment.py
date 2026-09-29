from __future__ import annotations

from civicresolve.models.case import (
    BusinessLicenseCase,
    PaymentStatus,
    WorkflowPaymentState,
)
from civicresolve.models.evidence import EvidenceBundle, EvidenceReference
from civicresolve.models.rule import (
    RuleCategory,
    RuleFinding,
    RuleSeverity,
)

RULE_ID = "RULE-PAY-001"
RULE_VERSION = "1.0"

FINDING_CODE = "PAYMENT_WORKFLOW_STATE_MISMATCH"


def detect_payment_workflow_state_mismatch(
    case: BusinessLicenseCase,
    evidence_bundle: EvidenceBundle,
) -> RuleFinding:
    """
    Detect whether payment is confirmed in the payment system while the
    licensing workflow still reports that payment is outstanding.

    This is a deterministic state-consistency check.
    """

    payment = case.payment

    if payment is None:
        return RuleFinding(
            rule_id=RULE_ID,
            rule_version=RULE_VERSION,
            finding_code=FINDING_CODE,
            title="Payment / workflow state mismatch",
            description=(
                "No payment record is available, so the payment/workflow "
                "consistency rule cannot be triggered."
            ),
            category=RuleCategory.SYSTEM_INTEGRATION,
            severity=RuleSeverity.HIGH,
            triggered=False,
            evidence=[],
            observed_condition="No payment record available.",
            limitation=(
                "This rule only evaluates cases that contain a payment record."
            ),
        )

    payment_id_matches = (
        payment.application_id
        == case.application.application_id
    )

    payment_successful = (
        payment.status
        == PaymentStatus.SUCCESS
    )

    workflow_waiting_for_payment = (
        case.workflow.payment_state
        == WorkflowPaymentState.AWAITING_PAYMENT
    )

    triggered = (
        payment_id_matches
        and payment_successful
        and workflow_waiting_for_payment
    )

    evidence_references: list[EvidenceReference] = []

    if triggered:
        payment_evidence_id = f"EVD-{payment.transaction_id}"
        workflow_evidence_id = f"EVD-{case.workflow.workflow_id}"

        if evidence_bundle.contains(payment_evidence_id):
            evidence_references.append(
                EvidenceReference(
                    evidence_id=payment_evidence_id,
                    reason=(
                        "Payment system reports a successful transaction "
                        "for the same application."
                    ),
                )
            )

        if evidence_bundle.contains(workflow_evidence_id):
            evidence_references.append(
                EvidenceReference(
                    evidence_id=workflow_evidence_id,
                    reason=(
                        "Licensing workflow still reports "
                        "AWAITING_PAYMENT."
                    ),
                )
            )

    return RuleFinding(
        rule_id=RULE_ID,
        rule_version=RULE_VERSION,
        finding_code=FINDING_CODE,
        title="Payment / workflow state mismatch",
        description=(
            "The payment system confirms successful payment for the "
            "application, while the licensing workflow still reports "
            "that payment is outstanding."
            if triggered
            else (
                "The payment system and licensing workflow do not meet "
                "the conditions for this mismatch rule."
            )
        ),
        category=RuleCategory.SYSTEM_INTEGRATION,
        severity=RuleSeverity.HIGH,
        triggered=triggered,
        evidence=evidence_references,
        observed_condition=(
            "Payment status is SUCCESS, the payment references the same "
            "application, and workflow payment state is AWAITING_PAYMENT."
            if triggered
            else (
                "The required deterministic mismatch conditions "
                "were not all present."
            )
        ),
        limitation=(
            "This rule confirms a cross-system state inconsistency. "
            "It does not establish the root cause of the inconsistency."
        ),
    )