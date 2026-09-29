from __future__ import annotations

from typing import Any

from civicresolve.models.context import InvestigationContext
from civicresolve.models.reasoning import (
    ReasoningEvidence,
    ReasoningFact,
    ReasoningFinding,
    ReasoningGuardrails,
    ReasoningPacket,
    ReasoningTask,
    ReasoningTimelineEntry,
)

PROHIBITED_ACTIONS: tuple[str, ...] = (
    "Issue, approve, deny, suspend, or revoke a government license.",
    "Bypass or waive an explicit policy requirement.",
    "Change workflow state without human authorization.",
    "Automatically reassign a payment to another application.",
    "Invent facts, evidence, policies, or system events.",
    (
        "Claim root-cause certainty when the available evidence "
        "only supports a likely explanation."
    ),
)


REQUIRED_BEHAVIORS: tuple[str, ...] = (
    "Distinguish confirmed facts from interpretation.",
    "Ground important conclusions in supplied evidence IDs.",
    "Use likely-cause language rather than unsupported certainty.",
    "Identify missing or conflicting information when relevant.",
    (
        "Recommend bounded next actions rather than final "
        "government decisions."
    ),
    (
        "Preserve human review before any consequential "
        "workflow action."
    ),
)


PERMITTED_OUTPUTS: tuple[str, ...] = (
    "likely_cause",
    "alternative_hypotheses",
    "confidence_level",
    "confidence_basis",
    "supporting_evidence_ids",
    "conflicting_evidence_ids",
    "missing_information",
    "recommended_action",
    "recommended_owner_role",
    "safety_constraints",
)


AI_EXCLUDED_EVIDENCE_FIELDS: frozenset[str] = frozenset(
    {
        "business_name",
        "applicant_id",
        "applicant_name",
        "email",
        "phone",
        "address",
    }
)


def _sanitize_evidence_fields(
    fields: dict[str, Any],
) -> dict[str, Any]:
    """
    Remove identity fields that are not necessary for exception reasoning.

    The underlying evidence record remains available inside CivicResolve,
    but unnecessary identity data is excluded from the AI reasoning packet.
    """

    return {
        key: value
        for key, value in fields.items()
        if key not in AI_EXCLUDED_EVIDENCE_FIELDS
    }


def _build_reasoning_facts(
    context: InvestigationContext,
) -> list[ReasoningFact]:
    return [
        ReasoningFact(
            fact_id=fact.fact_id,
            statement=fact.statement,
            evidence_ids=[
                reference.evidence_id
                for reference in fact.evidence
            ],
        )
        for fact in context.confirmed_facts
    ]


def _build_reasoning_findings(
    context: InvestigationContext,
) -> list[ReasoningFinding]:
    return [
        ReasoningFinding(
            finding_code=finding.finding_code,
            category=finding.category,
            severity=finding.severity,
            observed_condition=finding.observed_condition,
            limitation=finding.limitation,
            evidence_ids=[
                reference.evidence_id
                for reference in finding.evidence
            ],
        )
        for finding in context.deterministic_findings
    ]


def _build_reasoning_timeline(
    context: InvestigationContext,
) -> list[ReasoningTimelineEntry]:
    return [
        ReasoningTimelineEntry(
            occurred_at=entry.occurred_at,
            event_type=entry.event_type,
            source_system=entry.source_system,
            success=entry.success,
            summary=entry.summary,
            evidence_id=entry.evidence_id,
        )
        for entry in context.timeline
    ]


def _build_reasoning_evidence(
    context: InvestigationContext,
) -> list[ReasoningEvidence]:
    return [
        ReasoningEvidence(
            evidence_id=item.evidence_id,
            source_system=item.source_system.value,
            evidence_type=item.evidence_type.value,
            summary=item.summary,
            fields=_sanitize_evidence_fields(
                item.fields
            ),
        )
        for item in context.evidence_catalog
    ]


def _build_task(
    context: InvestigationContext,
) -> ReasoningTask:
    categories = {
        finding.category.value
        for finding in context.deterministic_findings
    }

    category_text = (
        ", ".join(sorted(categories))
        if categories
        else "NO_DETERMINISTIC_EXCEPTION"
    )

    return ReasoningTask(
        objective=(
            "Assess the most likely operational explanation for "
            "the detected workflow exception and recommend a safe, "
            "bounded next investigation or workflow action for "
            "human review."
        ),
        questions=[
            (
                "What is the most likely cause of the observed "
                "exception given the supplied facts, findings, "
                "timeline, and evidence?"
            ),
            (
                "What alternative explanation remains plausible, "
                "if any?"
            ),
            (
                "What evidence supports or conflicts with the "
                "likely explanation?"
            ),
            (
                "Is important information missing before a human "
                "should act?"
            ),
            (
                "What bounded next action should a human reviewer "
                "consider?"
            ),
            (
                "Which operational role or team should normally "
                "own that next step?"
            ),
            (
                "The deterministic exception category or categories "
                f"for this case are: {category_text}."
            ),
        ],
        permitted_outputs=list(PERMITTED_OUTPUTS),
    )


def _build_guardrails() -> ReasoningGuardrails:
    return ReasoningGuardrails(
        human_approval_required=True,
        may_make_final_government_decision=False,
        may_bypass_policy=False,
        may_execute_workflow_action=False,
        may_reassign_payment=False,
        prohibited_actions=list(PROHIBITED_ACTIONS),
        required_behaviors=list(REQUIRED_BEHAVIORS),
    )


def build_reasoning_packet(
    context: InvestigationContext,
) -> ReasoningPacket:
    """
    Convert deterministic CivicResolve context into a constrained packet
    suitable for future local-model inference.

    No AI inference occurs here.
    """

    return ReasoningPacket(
        case_id=context.identity.case_id,
        application_id=context.identity.application_id,
        current_stage=context.workflow.current_stage.value,
        expected_next_stage=(
            context.workflow.expected_next_stage.value
            if context.workflow.expected_next_stage is not None
            else None
        ),
        confirmed_facts=_build_reasoning_facts(
            context
        ),
        deterministic_findings=_build_reasoning_findings(
            context
        ),
        timeline=_build_reasoning_timeline(
            context
        ),
        evidence=_build_reasoning_evidence(
            context
        ),
        task=_build_task(
            context
        ),
        guardrails=_build_guardrails(),
    )