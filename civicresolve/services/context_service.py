from __future__ import annotations

from civicresolve.models.case import (
    BusinessLicenseCase,
    WorkflowStage,
)
from civicresolve.models.context import (
    CaseIdentity,
    ConfirmedFact,
    InvestigationContext,
    TimelineEntry,
    WorkflowContext,
)
from civicresolve.models.engine import RuleEngineResult
from civicresolve.models.evidence import (
    EvidenceBundle,
    EvidenceReference,
)

EXPECTED_WORKFLOW_PATH: tuple[WorkflowStage, ...] = (
    WorkflowStage.SUBMITTED,
    WorkflowStage.PAYMENT,
    WorkflowStage.REVIEW,
    WorkflowStage.APPROVAL,
    WorkflowStage.COMPLETE,
)


def _validate_context_inputs(
    case: BusinessLicenseCase,
    evidence_bundle: EvidenceBundle,
    rule_result: RuleEngineResult,
) -> None:
    """
    Prevent records from different cases from being accidentally
    combined into one investigation context.
    """

    expected_case_id = case.case_id
    expected_application_id = case.application.application_id

    if evidence_bundle.case_id != expected_case_id:
        raise ValueError(
            "Evidence bundle case_id does not match the case."
        )

    if (
        evidence_bundle.application_id
        != expected_application_id
    ):
        raise ValueError(
            "Evidence bundle application_id does not match the case."
        )

    if rule_result.case_id != expected_case_id:
        raise ValueError(
            "Rule-engine result case_id does not match the case."
        )

    if (
        rule_result.application_id
        != expected_application_id
    ):
        raise ValueError(
            "Rule-engine result application_id "
            "does not match the case."
        )


def _build_stages_reached(
    current_stage: WorkflowStage,
) -> list[WorkflowStage]:
    """
    Return the expected workflow path up to and including the
    current stage.

    This represents stages reached, not proof that every action
    within those stages was successfully completed.
    """

    current_index = EXPECTED_WORKFLOW_PATH.index(
        current_stage
    )

    return list(
        EXPECTED_WORKFLOW_PATH[: current_index + 1]
    )


def _build_application_fact(
    case: BusinessLicenseCase,
    evidence_bundle: EvidenceBundle,
) -> ConfirmedFact:
    evidence_id = (
        f"EVD-FORM-{case.application.application_id}"
    )

    if not evidence_bundle.contains(evidence_id):
        raise ValueError(
            f"Required evidence is missing: {evidence_id}"
        )

    return ConfirmedFact(
        fact_id="FACT-APPLICATION-STATE",
        statement=(
            f"Application {case.application.application_id} "
            f"has status {case.application.status.value}."
        ),
        evidence=[
            EvidenceReference(
                evidence_id=evidence_id,
                reason=(
                    "Application source record provides "
                    "the current application status."
                ),
            )
        ],
    )


def _build_payment_fact(
    case: BusinessLicenseCase,
    evidence_bundle: EvidenceBundle,
) -> ConfirmedFact | None:
    if case.payment is None:
        return None

    evidence_id = f"EVD-{case.payment.transaction_id}"

    if not evidence_bundle.contains(evidence_id):
        raise ValueError(
            f"Required evidence is missing: {evidence_id}"
        )

    return ConfirmedFact(
        fact_id="FACT-PAYMENT-STATE",
        statement=(
            f"Payment {case.payment.transaction_id} has status "
            f"{case.payment.status.value}, references application "
            f"{case.payment.application_id}, and has reconciliation "
            f"state {case.payment.reconciliation_state.value}."
        ),
        evidence=[
            EvidenceReference(
                evidence_id=evidence_id,
                reason=(
                    "Payment source record provides payment status, "
                    "application reference, and reconciliation state."
                ),
            )
        ],
    )


def _build_document_facts(
    case: BusinessLicenseCase,
    evidence_bundle: EvidenceBundle,
) -> list[ConfirmedFact]:
    facts: list[ConfirmedFact] = []

    for index, document in enumerate(
        case.documents,
        start=1,
    ):
        evidence_id = f"EVD-{document.document_id}"

        if not evidence_bundle.contains(evidence_id):
            raise ValueError(
                f"Required evidence is missing: {evidence_id}"
            )

        facts.append(
            ConfirmedFact(
                fact_id=f"FACT-DOCUMENT-{index}",
                statement=(
                    f"{document.document_type} "
                    f"({document.document_id}) has status "
                    f"{document.status.value}."
                ),
                evidence=[
                    EvidenceReference(
                        evidence_id=evidence_id,
                        reason=(
                            "Document source record provides "
                            "the current document status."
                        ),
                    )
                ],
            )
        )

    return facts


def _build_policy_facts(
    case: BusinessLicenseCase,
    evidence_bundle: EvidenceBundle,
) -> list[ConfirmedFact]:
    facts: list[ConfirmedFact] = []

    for index, policy in enumerate(
        case.policy_requirements,
        start=1,
    ):
        evidence_id = f"EVD-{policy.policy_id}"

        if not evidence_bundle.contains(evidence_id):
            raise ValueError(
                f"Required evidence is missing: {evidence_id}"
            )

        requirement = (
            policy.required_document_type
            if policy.required_document_type is not None
            else policy.requirement_type.value
        )

        facts.append(
            ConfirmedFact(
                fact_id=f"FACT-POLICY-{index}",
                statement=(
                    f"Policy {policy.policy_id} requires "
                    f"{requirement}; blocking={policy.blocking}, "
                    f"requires_valid_document="
                    f"{policy.requires_valid_document}."
                ),
                evidence=[
                    EvidenceReference(
                        evidence_id=evidence_id,
                        reason=(
                            "Policy source record defines "
                            "the explicit case requirement."
                        ),
                    )
                ],
            )
        )

    return facts


def _build_workflow_fact(
    case: BusinessLicenseCase,
    evidence_bundle: EvidenceBundle,
) -> ConfirmedFact:
    evidence_id = f"EVD-{case.workflow.workflow_id}"

    if not evidence_bundle.contains(evidence_id):
        raise ValueError(
            f"Required evidence is missing: {evidence_id}"
        )

    assigned_team = (
        case.workflow.assigned_team
        if case.workflow.assigned_team is not None
        else "UNASSIGNED"
    )

    assigned_role = (
        case.workflow.assigned_role
        if case.workflow.assigned_role is not None
        else "UNASSIGNED"
    )

    return ConfirmedFact(
        fact_id="FACT-WORKFLOW-STATE",
        statement=(
            f"Workflow is at {case.workflow.current_stage.value}; "
            f"payment state is "
            f"{case.workflow.payment_state.value}; "
            f"assigned team is {assigned_team}; "
            f"assigned role is {assigned_role}."
        ),
        evidence=[
            EvidenceReference(
                evidence_id=evidence_id,
                reason=(
                    "Workflow source record provides "
                    "the current process state and ownership."
                ),
            )
        ],
    )


def _build_confirmed_facts(
    case: BusinessLicenseCase,
    evidence_bundle: EvidenceBundle,
) -> list[ConfirmedFact]:
    facts = [
        _build_application_fact(
            case,
            evidence_bundle,
        )
    ]

    payment_fact = _build_payment_fact(
        case,
        evidence_bundle,
    )

    if payment_fact is not None:
        facts.append(payment_fact)

    facts.extend(
        _build_document_facts(
            case,
            evidence_bundle,
        )
    )

    facts.extend(
        _build_policy_facts(
            case,
            evidence_bundle,
        )
    )

    facts.append(
        _build_workflow_fact(
            case,
            evidence_bundle,
        )
    )

    return facts


def _build_timeline(
    case: BusinessLicenseCase,
    evidence_bundle: EvidenceBundle,
) -> list[TimelineEntry]:
    timeline: list[TimelineEntry] = []

    for event in sorted(
        case.events,
        key=lambda item: item.occurred_at,
    ):
        evidence_id = f"EVD-{event.event_id}"

        if not evidence_bundle.contains(evidence_id):
            raise ValueError(
                f"Required event evidence is missing: "
                f"{evidence_id}"
            )

        timeline.append(
            TimelineEntry(
                event_id=event.event_id,
                evidence_id=evidence_id,
                occurred_at=event.occurred_at,
                source_system=event.source_system,
                event_type=event.event_type.value,
                success=event.success,
                summary=event.message,
            )
        )

    return timeline


def build_investigation_context(
    case: BusinessLicenseCase,
    evidence_bundle: EvidenceBundle,
    rule_result: RuleEngineResult,
) -> InvestigationContext:
    """
    Build the deterministic investigation packet for one case.

    No AI inference occurs in this function.
    """

    _validate_context_inputs(
        case,
        evidence_bundle,
        rule_result,
    )

    generated_at = (
        case.exception_opened_at
        if case.exception_opened_at is not None
        else case.workflow.updated_at
    )

    workflow_context = WorkflowContext(
        expected_path=list(EXPECTED_WORKFLOW_PATH),
        stages_reached=_build_stages_reached(
            case.workflow.current_stage
        ),
        current_stage=case.workflow.current_stage,
        expected_next_stage=(
            case.workflow.expected_next_stage
        ),
        payment_state=case.workflow.payment_state,
        assigned_team=case.workflow.assigned_team,
        assigned_role=case.workflow.assigned_role,
    )

    return InvestigationContext(
        generated_at=generated_at,
        identity=CaseIdentity(
            case_id=case.case_id,
            application_id=case.application.application_id,
            business_name=(
                case.application.applicant.business_name
            ),
            license_type=case.application.license_type,
            synthetic=case.synthetic,
        ),
        case_status=case.status,
        severity=case.severity,
        workflow=workflow_context,
        confirmed_facts=_build_confirmed_facts(
            case,
            evidence_bundle,
        ),
        deterministic_findings=(
            rule_result.triggered_findings
        ),
        evaluated_rule_count=(
            rule_result.evaluated_rule_count
        ),
        timeline=_build_timeline(
            case,
            evidence_bundle,
        ),
        evidence_catalog=evidence_bundle.items,
    )