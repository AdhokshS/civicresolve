from __future__ import annotations

from dataclasses import dataclass

from civicresolve.ai.cached_provider import (
    CachedReasoningProvider,
)
from civicresolve.data.data_linkage_scenario import (
    build_data_linkage_exception_case,
)
from civicresolve.data.scenarios import (
    build_integration_exception_case,
    build_ownership_exception_case,
    build_policy_exception_case,
)
from civicresolve.models.assessment import (
    ValidatedAssessment,
)
from civicresolve.models.assessment_run import (
    AssessmentRunResult,
)
from civicresolve.models.case import (
    BusinessLicenseCase,
)
from civicresolve.models.context import (
    InvestigationContext,
)
from civicresolve.models.engine import (
    RuleEngineResult,
)
from civicresolve.models.evidence import (
    EvidenceBundle,
)
from civicresolve.models.reasoning import (
    ReasoningPacket,
)
from civicresolve.models.rule import (
    RuleFinding,
)
from civicresolve.rules.engine import (
    run_rule_engine,
)
from civicresolve.services.ai_assessment_service import (
    run_ai_assessment,
)
from civicresolve.services.context_service import (
    build_investigation_context,
)
from civicresolve.services.evidence_service import (
    build_evidence_bundle,
)
from civicresolve.services.reasoning_service import (
    build_reasoning_packet,
)


@dataclass(frozen=True)
class CaseWorkspace:
    """
    Complete read model for one CivicResolve investigation workspace.
    """

    case: BusinessLicenseCase

    evidence: EvidenceBundle

    rule_result: RuleEngineResult

    context: InvestigationContext

    reasoning_packet: ReasoningPacket

    assessment_run: AssessmentRunResult

    @property
    def primary_finding(
        self,
    ) -> RuleFinding | None:
        findings = self.rule_result.triggered_findings

        if not findings:
            return None

        return findings[0]

    @property
    def validated_assessment(
        self,
    ) -> ValidatedAssessment | None:
        return self.assessment_run.validated_assessment


def _build_workspace(
    case: BusinessLicenseCase,
    provider: CachedReasoningProvider,
) -> CaseWorkspace:
    evidence = build_evidence_bundle(
        case
    )

    rule_result = run_rule_engine(
        case,
        evidence,
    )

    context = build_investigation_context(
        case,
        evidence,
        rule_result,
    )

    reasoning_packet = build_reasoning_packet(
        context
    )

    assessment_run = run_ai_assessment(
        reasoning_packet,
        provider,
    )

    return CaseWorkspace(
        case=case,
        evidence=evidence,
        rule_result=rule_result,
        context=context,
        reasoning_packet=reasoning_packet,
        assessment_run=assessment_run,
    )


def build_case_workspaces() -> dict[str, CaseWorkspace]:
    """
    Build the four synthetic demo investigations.

    Demo-mode AI uses cached structured assessments, but every
    assessment still passes through the same deterministic validation
    service used for live local-model inference.
    """

    provider = CachedReasoningProvider()

    cases = (
        build_integration_exception_case(),
        build_policy_exception_case(),
        build_ownership_exception_case(),
        build_data_linkage_exception_case(),
    )

    workspaces = [
        _build_workspace(
            case,
            provider,
        )
        for case in cases
    ]

    return {
        workspace.case.case_id: workspace
        for workspace in workspaces
    }


def build_queue_rows(
    workspaces: dict[str, CaseWorkspace],
) -> list[dict[str, str]]:
    """
    Convert investigation workspaces into operations-queue rows.
    """

    rows: list[dict[str, str]] = []

    for workspace in workspaces.values():
        case = workspace.case
        finding = workspace.primary_finding
        assessment = workspace.validated_assessment

        rows.append(
            {
                "Case": case.case_id,
                "Application": (
                    case.application.application_id
                ),
                "Business": (
                    case.application.applicant.business_name
                ),
                "Exception": (
                    finding.category.value
                    if finding is not None
                    else "NONE"
                ),
                "Severity": (
                    finding.severity.value
                    if finding is not None
                    else case.severity.value
                ),
                "Stage": (
                    case.workflow.current_stage.value
                ),
                "Status": case.status.value,
                "AI validation": (
                    workspace.assessment_run.status.value
                ),
                "Confidence": (
                    assessment.confidence.value
                    if assessment is not None
                    else "UNAVAILABLE"
                ),
                "Recommended action": (
                    assessment.recommended_action.value
                    if assessment is not None
                    else "HUMAN_INVESTIGATION"
                ),
            }
        )

    return rows