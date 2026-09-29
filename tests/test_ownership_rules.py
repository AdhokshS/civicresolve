from civicresolve.data.scenarios import (
    build_integration_exception_case,
    build_ownership_exception_case,
    build_policy_exception_case,
)
from civicresolve.models.rule import (
    RuleCategory,
    RuleSeverity,
)
from civicresolve.rules.ownership import (
    detect_missing_workflow_owner,
)
from civicresolve.services.evidence_service import (
    build_evidence_bundle,
)


def test_missing_owner_rule_triggers_for_ownership_case():
    case = build_ownership_exception_case()

    bundle = build_evidence_bundle(case)

    finding = detect_missing_workflow_owner(
        case,
        bundle,
    )

    assert finding.triggered is True
    assert finding.finding_code == "MISSING_WORKFLOW_OWNER"

    assert finding.category == RuleCategory.OWNERSHIP_PROCESS
    assert finding.severity == RuleSeverity.HIGH


def test_missing_owner_rule_cites_workflow_and_event():
    case = build_ownership_exception_case()

    bundle = build_evidence_bundle(case)

    finding = detect_missing_workflow_owner(
        case,
        bundle,
    )

    evidence_ids = {
        reference.evidence_id
        for reference in finding.evidence
    }

    assert "EVD-WF-1061" in evidence_ids
    assert "EVD-EVT-91504" in evidence_ids


def test_missing_owner_rule_does_not_trigger_when_owner_exists():
    case = build_ownership_exception_case()

    case.workflow.assigned_team = "Licensing Administration"
    case.workflow.assigned_role = "Licensing Supervisor"

    bundle = build_evidence_bundle(case)

    finding = detect_missing_workflow_owner(
        case,
        bundle,
    )

    assert finding.triggered is False
    assert finding.evidence == []


def test_missing_owner_rule_does_not_trigger_for_integration_case():
    case = build_integration_exception_case()

    bundle = build_evidence_bundle(case)

    finding = detect_missing_workflow_owner(
        case,
        bundle,
    )

    assert finding.triggered is False


def test_missing_owner_rule_does_not_trigger_for_policy_case():
    case = build_policy_exception_case()

    bundle = build_evidence_bundle(case)

    finding = detect_missing_workflow_owner(
        case,
        bundle,
    )

    assert finding.triggered is False


def test_missing_owner_rule_does_not_choose_specific_person():
    case = build_ownership_exception_case()

    bundle = build_evidence_bundle(case)

    finding = detect_missing_workflow_owner(
        case,
        bundle,
    )

    assert (
        "does not determine why"
        in finding.limitation
    )

    assert (
        "which specific individual"
        in finding.limitation
    )