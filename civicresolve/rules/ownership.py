from __future__ import annotations

from civicresolve.models.case import (
    BusinessLicenseCase,
    EventType,
    WorkflowStage,
)
from civicresolve.models.evidence import EvidenceBundle, EvidenceReference
from civicresolve.models.rule import (
    RuleCategory,
    RuleFinding,
    RuleSeverity,
)

RULE_ID = "RULE-OWN-001"
RULE_VERSION = "1.0"

FINDING_CODE = "MISSING_WORKFLOW_OWNER"


def detect_missing_workflow_owner(
    case: BusinessLicenseCase,
    evidence_bundle: EvidenceBundle,
) -> RuleFinding:
    """
    Detect whether an application has reached a workflow stage that
    requires continued processing but has no responsible team or role.

    This rule identifies an ownership/process gap. It does not determine
    why the assignment is missing or automatically select a new owner.
    """

    workflow = case.workflow

    stage_requires_owner = (
        workflow.current_stage == WorkflowStage.APPROVAL
        and workflow.expected_next_stage is not None
    )

    owner_missing = (
        workflow.assigned_team is None
        or workflow.assigned_role is None
    )

    triggered = stage_requires_owner and owner_missing

    evidence_references: list[EvidenceReference] = []

    if triggered:
        workflow_evidence_id = f"EVD-{workflow.workflow_id}"

        if evidence_bundle.contains(workflow_evidence_id):
            evidence_references.append(
                EvidenceReference(
                    evidence_id=workflow_evidence_id,
                    reason=(
                        "Workflow is at the approval stage but does "
                        "not contain a complete responsible owner assignment."
                    ),
                )
            )

        ownership_events = [
            event
            for event in case.events
            if event.event_type == EventType.OWNER_REMOVED
        ]

        if ownership_events:
            latest_event = max(
                ownership_events,
                key=lambda event: event.occurred_at,
            )

            event_evidence_id = f"EVD-{latest_event.event_id}"

            if evidence_bundle.contains(event_evidence_id):
                evidence_references.append(
                    EvidenceReference(
                        evidence_id=event_evidence_id,
                        reason=(
                            "Workflow history records that the prior "
                            "assignment was cleared and no downstream "
                            "approval owner was assigned."
                        ),
                    )
                )

    return RuleFinding(
        rule_id=RULE_ID,
        rule_version=RULE_VERSION,
        finding_code=FINDING_CODE,
        title="Missing workflow owner",
        description=(
            "The application has reached an active approval stage "
            "without a complete responsible team and role assignment."
            if triggered
            else (
                "The workflow does not meet the deterministic "
                "conditions for a missing-owner finding."
            )
        ),
        category=RuleCategory.OWNERSHIP_PROCESS,
        severity=RuleSeverity.HIGH,
        triggered=triggered,
        evidence=evidence_references,
        observed_condition=(
            "Workflow stage is APPROVAL and the next stage is defined, "
            "but the responsible team or role is missing."
            if triggered
            else (
                "The required deterministic missing-owner conditions "
                "were not all present."
            )
        ),
        limitation=(
            "This rule confirms an ownership gap in the workflow state. "
            "It does not determine why the assignment is missing or "
            "which specific individual should receive the case."
        ),
    )