from __future__ import annotations

from civicresolve.models.case import (
    BusinessLicenseCase,
    DocumentStatus,
    PolicyRequirementType,
)
from civicresolve.models.evidence import EvidenceBundle, EvidenceReference
from civicresolve.models.rule import (
    RuleCategory,
    RuleFinding,
    RuleSeverity,
)

RULE_ID = "RULE-POL-001"
RULE_VERSION = "1.0"

FINDING_CODE = "REQUIRED_DOCUMENT_POLICY_BLOCKER"


def detect_required_document_policy_blocker(
    case: BusinessLicenseCase,
    evidence_bundle: EvidenceBundle,
) -> RuleFinding:
    """
    Detect whether an explicit blocking policy requires a valid document
    but the corresponding case document is missing, expired, rejected,
    or otherwise not valid.

    The rule only evaluates explicit policy requirements attached to
    the synthetic case. It does not invent policy from model knowledge.
    """

    blocking_policy = None
    matching_document = None

    for policy in case.policy_requirements:
        if (
            policy.requirement_type
            == PolicyRequirementType.REQUIRED_DOCUMENT
            and policy.blocking
            and policy.requires_valid_document
            and policy.required_document_type is not None
        ):
            document = next(
                (
                    item
                    for item in case.documents
                    if item.document_type
                    == policy.required_document_type
                ),
                None,
            )

            if (
                document is None
                or document.status != DocumentStatus.VALID
            ):
                blocking_policy = policy
                matching_document = document
                break

    triggered = blocking_policy is not None

    evidence_references: list[EvidenceReference] = []

    if blocking_policy is not None:
        policy_evidence_id = (
            f"EVD-{blocking_policy.policy_id}"
        )

        if evidence_bundle.contains(policy_evidence_id):
            evidence_references.append(
                EvidenceReference(
                    evidence_id=policy_evidence_id,
                    reason=(
                        "Policy explicitly requires a valid "
                        f"{blocking_policy.required_document_type} "
                        "before the application can advance."
                    ),
                )
            )

        if matching_document is not None:
            document_evidence_id = (
                f"EVD-{matching_document.document_id}"
            )

            if evidence_bundle.contains(document_evidence_id):
                evidence_references.append(
                    EvidenceReference(
                        evidence_id=document_evidence_id,
                        reason=(
                            f"{matching_document.document_type} "
                            "does not have VALID status."
                        ),
                    )
                )

    if triggered and matching_document is None:
        observed_condition = (
            f"Policy requires a valid "
            f"{blocking_policy.required_document_type}, "
            "but no matching document record is present."
        )
    elif triggered and matching_document is not None:
        observed_condition = (
            f"Policy requires a valid "
            f"{blocking_policy.required_document_type}, "
            f"but document {matching_document.document_id} "
            f"has status {matching_document.status.value}."
        )
    else:
        observed_condition = (
            "No explicit blocking required-document policy "
            "was found with an unsatisfied document requirement."
        )

    return RuleFinding(
        rule_id=RULE_ID,
        rule_version=RULE_VERSION,
        finding_code=FINDING_CODE,
        title="Required document policy blocker",
        description=(
            "A blocking policy requires a valid document, "
            "but the corresponding case document does not "
            "satisfy that requirement."
            if triggered
            else (
                "All evaluated blocking required-document policies "
                "are satisfied."
            )
        ),
        category=RuleCategory.POLICY,
        severity=RuleSeverity.HIGH,
        triggered=triggered,
        evidence=evidence_references,
        observed_condition=observed_condition,
        limitation=(
            "This rule identifies whether an explicit synthetic policy "
            "requirement is satisfied. It does not interpret laws, "
            "waive requirements, or authorize the application "
            "to advance."
        ),
    )