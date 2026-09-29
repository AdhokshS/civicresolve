from civicresolve.data.scenarios import (
    build_integration_exception_case,
)
from civicresolve.models.case import WorkflowPaymentState
from civicresolve.models.rule import (
    RuleCategory,
    RuleSeverity,
)
from civicresolve.rules.payment import (
    detect_payment_workflow_state_mismatch,
)
from civicresolve.services.evidence_service import (
    build_evidence_bundle,
)


def test_payment_workflow_mismatch_rule_triggers_for_hero_case():
    case = build_integration_exception_case()

    evidence_bundle = build_evidence_bundle(case)

    finding = detect_payment_workflow_state_mismatch(
        case,
        evidence_bundle,
    )

    assert finding.triggered is True

    assert (
        finding.finding_code
        == "PAYMENT_WORKFLOW_STATE_MISMATCH"
    )

    assert (
        finding.category
        == RuleCategory.SYSTEM_INTEGRATION
    )

    assert finding.severity == RuleSeverity.HIGH


def test_payment_workflow_mismatch_rule_cites_payment_and_workflow():
    case = build_integration_exception_case()

    evidence_bundle = build_evidence_bundle(case)

    finding = detect_payment_workflow_state_mismatch(
        case,
        evidence_bundle,
    )

    evidence_ids = {
        reference.evidence_id
        for reference in finding.evidence
    }

    assert "EVD-PAY-88219" in evidence_ids
    assert "EVD-WF-1047" in evidence_ids


def test_payment_workflow_mismatch_rule_does_not_claim_root_cause():
    case = build_integration_exception_case()

    evidence_bundle = build_evidence_bundle(case)

    finding = detect_payment_workflow_state_mismatch(
        case,
        evidence_bundle,
    )

    assert "does not establish the root cause" in finding.limitation


def test_payment_workflow_mismatch_rule_does_not_trigger_when_synced():
    case = build_integration_exception_case()

    case.workflow.payment_state = WorkflowPaymentState.CONFIRMED

    evidence_bundle = build_evidence_bundle(case)

    finding = detect_payment_workflow_state_mismatch(
        case,
        evidence_bundle,
    )

    assert finding.triggered is False
    assert finding.evidence == []


def test_payment_workflow_mismatch_rule_does_not_trigger_on_id_mismatch():
    case = build_integration_exception_case()

    assert case.payment is not None

    case.payment.application_id = "LIC-OTHER-9999"

    evidence_bundle = build_evidence_bundle(case)

    finding = detect_payment_workflow_state_mismatch(
        case,
        evidence_bundle,
    )

    assert finding.triggered is False
    