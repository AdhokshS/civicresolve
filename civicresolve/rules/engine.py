from __future__ import annotations

from collections.abc import Callable

from civicresolve.models.case import BusinessLicenseCase
from civicresolve.models.engine import RuleEngineResult
from civicresolve.models.evidence import EvidenceBundle
from civicresolve.models.rule import RuleFinding
from civicresolve.rules.data_linkage import (
    detect_payment_application_reference_mismatch,
)
from civicresolve.rules.ownership import detect_missing_workflow_owner
from civicresolve.rules.payment import (
    detect_payment_workflow_state_mismatch,
)
from civicresolve.rules.policy import (
    detect_required_document_policy_blocker,
)

RuleFunction = Callable[
    [BusinessLicenseCase, EvidenceBundle],
    RuleFinding,
]


DEFAULT_RULES: tuple[RuleFunction, ...] = (
    detect_payment_workflow_state_mismatch,
    detect_required_document_policy_blocker,
    detect_missing_workflow_owner,
    detect_payment_application_reference_mismatch,
)


def run_rule_engine(
    case: BusinessLicenseCase,
    evidence_bundle: EvidenceBundle,
    rules: tuple[RuleFunction, ...] = DEFAULT_RULES,
) -> RuleEngineResult:
    """
    Run deterministic CivicResolve rules against one case.

    The engine coordinates rule execution only.
    Individual business rules remain isolated in their own modules.
    """

    findings = [
        rule(case, evidence_bundle)
        for rule in rules
    ]

    triggered_rule_count = sum(
        finding.triggered
        for finding in findings
    )

    return RuleEngineResult(
        case_id=case.case_id,
        application_id=case.application.application_id,
        evaluated_rule_count=len(findings),
        triggered_rule_count=triggered_rule_count,
        findings=findings,
    )