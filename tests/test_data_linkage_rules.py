from civicresolve.data.data_linkage_scenario import (
    build_data_linkage_exception_case,
)
from civicresolve.data.scenarios import (
    build_integration_exception_case,
    build_ownership_exception_case,
    build_policy_exception_case,
)
from civicresolve.models.rule import (
    RuleCategory,
    RuleSeverity,
)
from civicresolve.rules.data_linkage import (
    detect_payment_application_reference_mismatch,
)
from civicresolve.services.evidence_service import (
    build_evidence_bundle,
)


def test_data_linkage_rule_triggers_for_reference_mismatch():
    case = build_data_linkage_exception_case()

    bundle = build_evidence_bundle(case)

    finding = detect_payment_application_reference_mismatch(
        case,
        bundle,
    )

    assert finding.triggered is True

    assert (
        finding.finding_code
        == "PAYMENT_APPLICATION_REFERENCE_MISMATCH"
    )

    assert finding.category == RuleCategory.DATA
    assert finding.severity == RuleSeverity.HIGH


def test_data_linkage_rule_cites_payment_and_form():
    case = build_data_linkage_exception_case()

    bundle = build_evidence_bundle(case)

    finding = detect_payment_application_reference_mismatch(
        case,
        bundle,
    )

    evidence_ids = {
        reference.evidence_id
        for reference in finding.evidence
    }

    assert "EVD-PAY-88410" in evidence_ids
    assert "EVD-FORM-LIC-2026-1074" in evidence_ids


def test_data_linkage_rule_describes_both_application_ids():
    case = build_data_linkage_exception_case()

    bundle = build_evidence_bundle(case)

    finding = detect_payment_application_reference_mismatch(
        case,
        bundle,
    )

    assert "LIC-2026-0998" in finding.observed_condition
    assert "LIC-2026-1074" in finding.observed_condition


def test_data_linkage_rule_does_not_trigger_for_integration_case():
    case = build_integration_exception_case()

    bundle = build_evidence_bundle(case)

    finding = detect_payment_application_reference_mismatch(
        case,
        bundle,
    )

    assert finding.triggered is False


def test_data_linkage_rule_does_not_trigger_for_policy_case():
    case = build_policy_exception_case()

    bundle = build_evidence_bundle(case)

    finding = detect_payment_application_reference_mismatch(
        case,
        bundle,
    )

    assert finding.triggered is False


def test_data_linkage_rule_does_not_trigger_for_ownership_case():
    case = build_ownership_exception_case()

    bundle = build_evidence_bundle(case)

    finding = detect_payment_application_reference_mismatch(
        case,
        bundle,
    )

    assert finding.triggered is False


def test_data_linkage_rule_does_not_authorize_reassignment():
    case = build_data_linkage_exception_case()

    bundle = build_evidence_bundle(case)

    finding = detect_payment_application_reference_mismatch(
        case,
        bundle,
    )

    assert (
        "does not determine the payment's correct destination"
        in finding.limitation
    )

    assert (
        "authorize automatic reassignment"
        in finding.limitation
    )