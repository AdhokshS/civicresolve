from civicresolve.data.scenarios import (
    build_integration_exception_case,
    build_policy_exception_case,
)
from civicresolve.models.case import DocumentStatus
from civicresolve.models.rule import (
    RuleCategory,
    RuleSeverity,
)
from civicresolve.rules.policy import (
    detect_required_document_policy_blocker,
)
from civicresolve.services.evidence_service import (
    build_evidence_bundle,
)


def test_policy_blocker_triggers_for_expired_insurance():
    case = build_policy_exception_case()

    evidence_bundle = build_evidence_bundle(case)

    finding = detect_required_document_policy_blocker(
        case,
        evidence_bundle,
    )

    assert finding.triggered is True

    assert (
        finding.finding_code
        == "REQUIRED_DOCUMENT_POLICY_BLOCKER"
    )

    assert finding.category == RuleCategory.POLICY
    assert finding.severity == RuleSeverity.HIGH


def test_policy_blocker_cites_policy_and_document():
    case = build_policy_exception_case()

    evidence_bundle = build_evidence_bundle(case)

    finding = detect_required_document_policy_blocker(
        case,
        evidence_bundle,
    )

    evidence_ids = {
        reference.evidence_id
        for reference in finding.evidence
    }

    assert "EVD-POL-LIC-INS-001" in evidence_ids
    assert "EVD-DOC-4451" in evidence_ids


def test_policy_blocker_observed_condition_mentions_expired_status():
    case = build_policy_exception_case()

    evidence_bundle = build_evidence_bundle(case)

    finding = detect_required_document_policy_blocker(
        case,
        evidence_bundle,
    )

    assert "EXPIRED" in finding.observed_condition
    assert "DOC-4451" in finding.observed_condition


def test_policy_blocker_does_not_trigger_when_document_is_valid():
    case = build_policy_exception_case()

    insurance = next(
        document
        for document in case.documents
        if document.document_type == "Proof of Insurance"
    )

    insurance.status = DocumentStatus.VALID

    evidence_bundle = build_evidence_bundle(case)

    finding = detect_required_document_policy_blocker(
        case,
        evidence_bundle,
    )

    assert finding.triggered is False
    assert finding.evidence == []


def test_policy_blocker_does_not_trigger_for_integration_case():
    case = build_integration_exception_case()

    evidence_bundle = build_evidence_bundle(case)

    finding = detect_required_document_policy_blocker(
        case,
        evidence_bundle,
    )

    assert finding.triggered is False


def test_policy_blocker_does_not_authorize_policy_bypass():
    case = build_policy_exception_case()

    evidence_bundle = build_evidence_bundle(case)

    finding = detect_required_document_policy_blocker(
        case,
        evidence_bundle,
    )

    assert (
        "does not interpret laws"
        in finding.limitation
    )

    assert (
        "waive requirements"
        in finding.limitation
    )