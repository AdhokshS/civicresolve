from __future__ import annotations

from civicresolve.models.case import (
    BusinessLicenseCase,
    PaymentReconciliationState,
    PaymentStatus,
)
from civicresolve.models.evidence import EvidenceBundle, EvidenceReference
from civicresolve.models.rule import (
    RuleCategory,
    RuleFinding,
    RuleSeverity,
)

RULE_ID = "RULE-DATA-001"
RULE_VERSION = "1.0"

FINDING_CODE = "PAYMENT_APPLICATION_REFERENCE_MISMATCH"


def detect_payment_application_reference_mismatch(
    case: BusinessLicenseCase,
    evidence_bundle: EvidenceBundle,
) -> RuleFinding:
    """
    Detect whether a successful payment record references a different
    application ID and remains unmatched during reconciliation.

    This identifies a deterministic linkage inconsistency. It does not
    determine which application the payment should ultimately belong to.
    """

    payment = case.payment

    if payment is None:
        return RuleFinding(
            rule_id=RULE_ID,
            rule_version=RULE_VERSION,
            finding_code=FINDING_CODE,
            title="Payment application reference mismatch",
            description=(
                "No payment record is available, so payment-reference "
                "consistency cannot be evaluated."
            ),
            category=RuleCategory.DATA,
            severity=RuleSeverity.HIGH,
            triggered=False,
            evidence=[],
            observed_condition="No payment record available.",
            limitation=(
                "This rule only evaluates cases containing "
                "a payment record."
            ),
        )

    payment_successful = payment.status == PaymentStatus.SUCCESS

    application_reference_mismatch = (
        payment.application_id
        != case.application.application_id
    )

    reconciliation_unmatched = (
        payment.reconciliation_state
        == PaymentReconciliationState.UNMATCHED
    )

    triggered = (
        payment_successful
        and application_reference_mismatch
        and reconciliation_unmatched
    )

    evidence_references: list[EvidenceReference] = []

    if triggered:
        payment_evidence_id = f"EVD-{payment.transaction_id}"

        form_evidence_id = (
            f"EVD-FORM-{case.application.application_id}"
        )

        if evidence_bundle.contains(payment_evidence_id):
            evidence_references.append(
                EvidenceReference(
                    evidence_id=payment_evidence_id,
                    reason=(
                        "Successful payment record references "
                        f"{payment.application_id} and remains "
                        "UNMATCHED during reconciliation."
                    ),
                )
            )

        if evidence_bundle.contains(form_evidence_id):
            evidence_references.append(
                EvidenceReference(
                    evidence_id=form_evidence_id,
                    reason=(
                        "The case application identifier is "
                        f"{case.application.application_id}, "
                        "which differs from the payment reference."
                    ),
                )
            )

    return RuleFinding(
        rule_id=RULE_ID,
        rule_version=RULE_VERSION,
        finding_code=FINDING_CODE,
        title="Payment application reference mismatch",
        description=(
            "A successful payment record references a different "
            "application identifier and remains unmatched during "
            "reconciliation."
            if triggered
            else (
                "The payment record does not meet the deterministic "
                "conditions for an application-reference mismatch."
            )
        ),
        category=RuleCategory.DATA,
        severity=RuleSeverity.HIGH,
        triggered=triggered,
        evidence=evidence_references,
        observed_condition=(
            f"Payment {payment.transaction_id} is SUCCESS and references "
            f"{payment.application_id}, while the case application is "
            f"{case.application.application_id}; reconciliation state "
            "is UNMATCHED."
            if triggered
            else (
                "The required deterministic payment-reference mismatch "
                "conditions were not all present."
            )
        ),
        limitation=(
            "This rule confirms that the payment and case identifiers "
            "do not align. It does not determine the payment's correct "
            "destination or authorize automatic reassignment."
        ),
    )