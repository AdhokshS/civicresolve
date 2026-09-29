from civicresolve.data.data_linkage_scenario import (
    build_data_linkage_exception_case,
)
from civicresolve.data.scenarios import (
    build_integration_exception_case,
    build_policy_exception_case,
)
from civicresolve.rules.engine import run_rule_engine
from civicresolve.services.context_service import (
    build_investigation_context,
)
from civicresolve.services.evidence_service import (
    build_evidence_bundle,
)
from civicresolve.services.reasoning_service import (
    build_reasoning_packet,
)


def _build_packet(case):
    evidence = build_evidence_bundle(case)

    rules = run_rule_engine(
        case,
        evidence,
    )

    context = build_investigation_context(
        case,
        evidence,
        rules,
    )

    return build_reasoning_packet(context)


def test_reasoning_packet_contains_case_identity():
    packet = _build_packet(
        build_integration_exception_case()
    )

    assert packet.case_id == "CASE-1047"

    assert (
        packet.application_id
        == "LIC-2026-1047"
    )


def test_reasoning_packet_contains_deterministic_finding():
    packet = _build_packet(
        build_integration_exception_case()
    )

    assert len(packet.deterministic_findings) == 1

    finding = packet.deterministic_findings[0]

    assert (
        finding.finding_code
        == "PAYMENT_WORKFLOW_STATE_MISMATCH"
    )

    assert finding.category.value == "SYSTEM_INTEGRATION"


def test_reasoning_packet_contains_failed_sync_event():
    packet = _build_packet(
        build_integration_exception_case()
    )

    failed_sync = [
        entry
        for entry in packet.timeline
        if entry.event_type
        == "WORKFLOW_UPDATE_ATTEMPTED"
    ]

    assert len(failed_sync) == 1

    assert failed_sync[0].success is False

    assert (
        failed_sync[0].evidence_id
        == "EVD-EVT-91372"
    )


def test_reasoning_packet_exposes_http_503_evidence():
    packet = _build_packet(
        build_integration_exception_case()
    )

    evidence = next(
        item
        for item in packet.evidence
        if item.evidence_id == "EVD-EVT-91372"
    )

    assert evidence.fields["details"]["http_status"] == 503


def test_reasoning_packet_requires_human_approval():
    packet = _build_packet(
        build_integration_exception_case()
    )

    assert (
        packet.guardrails.human_approval_required
        is True
    )

    assert (
        packet.guardrails.may_execute_workflow_action
        is False
    )

    assert (
        packet.guardrails.may_make_final_government_decision
        is False
    )


def test_reasoning_packet_prohibits_policy_bypass():
    packet = _build_packet(
        build_policy_exception_case()
    )

    assert packet.guardrails.may_bypass_policy is False

    prohibited_text = " ".join(
        packet.guardrails.prohibited_actions
    ).lower()

    assert "bypass" in prohibited_text
    assert "policy" in prohibited_text


def test_reasoning_packet_prohibits_payment_reassignment():
    packet = _build_packet(
        build_data_linkage_exception_case()
    )

    assert (
        packet.guardrails.may_reassign_payment
        is False
    )

    prohibited_text = " ".join(
        packet.guardrails.prohibited_actions
    ).lower()

    assert "reassign" in prohibited_text
    assert "payment" in prohibited_text


def test_reasoning_packet_defines_permitted_output_contract():
    packet = _build_packet(
        build_integration_exception_case()
    )

    expected_outputs = {
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
    }

    assert (
        set(packet.task.permitted_outputs)
        == expected_outputs
    )


def test_reasoning_packet_does_not_expose_business_name():
    packet = _build_packet(
        build_integration_exception_case()
    )

    serialized = packet.model_dump_json()

    assert "Harbor Street Coffee LLC" not in serialized