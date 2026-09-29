import pytest

from civicresolve.data.data_linkage_scenario import (
    build_data_linkage_exception_case,
)
from civicresolve.data.scenarios import (
    build_integration_exception_case,
    build_ownership_exception_case,
    build_policy_exception_case,
)
from civicresolve.models.case import WorkflowStage
from civicresolve.rules.engine import run_rule_engine
from civicresolve.services.context_service import (
    build_investigation_context,
)
from civicresolve.services.evidence_service import (
    build_evidence_bundle,
)


def _build_context(case):
    evidence_bundle = build_evidence_bundle(case)

    rule_result = run_rule_engine(
        case,
        evidence_bundle,
    )

    return build_investigation_context(
        case,
        evidence_bundle,
        rule_result,
    )


def test_integration_context_contains_identity():
    context = _build_context(
        build_integration_exception_case()
    )

    assert context.identity.case_id == "CASE-1047"

    assert (
        context.identity.application_id
        == "LIC-2026-1047"
    )

    assert (
        context.identity.business_name
        == "Harbor Street Coffee LLC"
    )

    assert context.identity.synthetic is True


def test_integration_context_reconstructs_workflow_position():
    context = _build_context(
        build_integration_exception_case()
    )

    assert (
        context.workflow.current_stage
        == WorkflowStage.PAYMENT
    )

    assert context.workflow.stages_reached == [
        WorkflowStage.SUBMITTED,
        WorkflowStage.PAYMENT,
    ]

    assert context.workflow.expected_path == [
        WorkflowStage.SUBMITTED,
        WorkflowStage.PAYMENT,
        WorkflowStage.REVIEW,
        WorkflowStage.APPROVAL,
        WorkflowStage.COMPLETE,
    ]


def test_integration_context_contains_triggered_finding():
    context = _build_context(
        build_integration_exception_case()
    )

    assert len(context.deterministic_findings) == 1

    finding = context.deterministic_findings[0]

    assert (
        finding.finding_code
        == "PAYMENT_WORKFLOW_STATE_MISMATCH"
    )

    assert finding.category.value == "SYSTEM_INTEGRATION"

    assert context.evaluated_rule_count == 4


def test_integration_context_contains_sorted_timeline():
    context = _build_context(
        build_integration_exception_case()
    )

    assert len(context.timeline) == 5

    timestamps = [
        entry.occurred_at
        for entry in context.timeline
    ]

    assert timestamps == sorted(timestamps)

    assert (
        context.timeline[-1].event_id
        == "EVT-91374"
    )


def test_policy_context_contains_policy_fact():
    context = _build_context(
        build_policy_exception_case()
    )

    policy_facts = [
        fact
        for fact in context.confirmed_facts
        if fact.fact_id.startswith("FACT-POLICY")
    ]

    assert len(policy_facts) == 1

    assert (
        "POL-LIC-INS-001"
        in policy_facts[0].statement
    )

    assert (
        policy_facts[0].evidence[0].evidence_id
        == "EVD-POL-LIC-INS-001"
    )


def test_ownership_context_preserves_unassigned_owner():
    context = _build_context(
        build_ownership_exception_case()
    )

    assert context.workflow.assigned_team is None
    assert context.workflow.assigned_role is None

    workflow_fact = next(
        fact
        for fact in context.confirmed_facts
        if fact.fact_id == "FACT-WORKFLOW-STATE"
    )

    assert "UNASSIGNED" in workflow_fact.statement


def test_data_linkage_context_preserves_reference_mismatch():
    context = _build_context(
        build_data_linkage_exception_case()
    )

    payment_fact = next(
        fact
        for fact in context.confirmed_facts
        if fact.fact_id == "FACT-PAYMENT-STATE"
    )

    assert "LIC-2026-0998" in payment_fact.statement

    assert (
        context.identity.application_id
        == "LIC-2026-1074"
    )


def test_context_builder_rejects_cross_case_evidence():
    integration_case = build_integration_exception_case()

    policy_case = build_policy_exception_case()

    wrong_evidence_bundle = build_evidence_bundle(
        policy_case
    )

    correct_rule_result = run_rule_engine(
        integration_case,
        build_evidence_bundle(integration_case),
    )

    with pytest.raises(
        ValueError,
        match="Evidence bundle case_id",
    ):
        build_investigation_context(
            integration_case,
            wrong_evidence_bundle,
            correct_rule_result,
        )