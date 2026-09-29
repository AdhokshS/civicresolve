from civicresolve.data.data_linkage_scenario import (
    build_data_linkage_exception_case,
)
from civicresolve.data.scenarios import (
    build_integration_exception_case,
    build_ownership_exception_case,
    build_policy_exception_case,
)
from civicresolve.models.case import WorkflowPaymentState
from civicresolve.rules.engine import run_rule_engine
from civicresolve.services.evidence_service import (
    build_evidence_bundle,
)


def test_rule_engine_evaluates_all_registered_rules():
    case = build_integration_exception_case()

    result = run_rule_engine(
        case,
        build_evidence_bundle(case),
    )

    assert result.evaluated_rule_count == 4
    assert len(result.findings) == 4


def test_rule_engine_identifies_integration_finding():
    case = build_integration_exception_case()

    result = run_rule_engine(
        case,
        build_evidence_bundle(case),
    )

    assert result.triggered_rule_count == 1

    finding = result.triggered_findings[0]

    assert (
        finding.finding_code
        == "PAYMENT_WORKFLOW_STATE_MISMATCH"
    )

    assert finding.category.value == "SYSTEM_INTEGRATION"


def test_rule_engine_identifies_policy_finding():
    case = build_policy_exception_case()

    result = run_rule_engine(
        case,
        build_evidence_bundle(case),
    )

    assert result.triggered_rule_count == 1

    finding = result.triggered_findings[0]

    assert (
        finding.finding_code
        == "REQUIRED_DOCUMENT_POLICY_BLOCKER"
    )

    assert finding.category.value == "POLICY"


def test_rule_engine_identifies_ownership_finding():
    case = build_ownership_exception_case()

    result = run_rule_engine(
        case,
        build_evidence_bundle(case),
    )

    assert result.triggered_rule_count == 1

    finding = result.triggered_findings[0]

    assert finding.finding_code == "MISSING_WORKFLOW_OWNER"

    assert finding.category.value == "OWNERSHIP_PROCESS"


def test_rule_engine_identifies_data_linkage_finding():
    case = build_data_linkage_exception_case()

    result = run_rule_engine(
        case,
        build_evidence_bundle(case),
    )

    assert result.triggered_rule_count == 1

    finding = result.triggered_findings[0]

    assert (
        finding.finding_code
        == "PAYMENT_APPLICATION_REFERENCE_MISMATCH"
    )

    assert finding.category.value == "DATA"


def test_rule_engine_keeps_all_exception_categories_separate():
    cases = [
        build_integration_exception_case(),
        build_policy_exception_case(),
        build_ownership_exception_case(),
        build_data_linkage_exception_case(),
    ]

    expected_codes = [
        "PAYMENT_WORKFLOW_STATE_MISMATCH",
        "REQUIRED_DOCUMENT_POLICY_BLOCKER",
        "MISSING_WORKFLOW_OWNER",
        "PAYMENT_APPLICATION_REFERENCE_MISMATCH",
    ]

    expected_categories = [
        "SYSTEM_INTEGRATION",
        "POLICY",
        "OWNERSHIP_PROCESS",
        "DATA",
    ]

    for case, expected_code, expected_category in zip(
        cases,
        expected_codes,
        expected_categories,
        strict=True,
    ):
        result = run_rule_engine(
            case,
            build_evidence_bundle(case),
        )

        assert result.triggered_rule_count == 1

        finding = result.triggered_findings[0]

        assert finding.finding_code == expected_code
        assert finding.category.value == expected_category


def test_rule_engine_reports_no_trigger_when_integration_case_is_synced():
    case = build_integration_exception_case()

    case.workflow.payment_state = WorkflowPaymentState.CONFIRMED

    result = run_rule_engine(
        case,
        build_evidence_bundle(case),
    )

    assert result.evaluated_rule_count == 4
    assert result.triggered_rule_count == 0

    assert result.has_triggered_findings is False
    assert result.triggered_findings == []


def test_rule_engine_preserves_case_identity():
    case = build_integration_exception_case()

    result = run_rule_engine(
        case,
        build_evidence_bundle(case),
    )

    assert result.case_id == "CASE-1047"
    assert result.application_id == "LIC-2026-1047"