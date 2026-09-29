from __future__ import annotations

from pydantic import Field

from civicresolve.models.case import StrictModel
from civicresolve.models.rule import RuleFinding


class RuleEngineResult(StrictModel):
    """
    Result of running CivicResolve's deterministic rule engine
    against one case snapshot.
    """

    case_id: str
    application_id: str

    evaluated_rule_count: int
    triggered_rule_count: int

    findings: list[RuleFinding] = Field(default_factory=list)

    @property
    def triggered_findings(self) -> list[RuleFinding]:
        """
        Return only rules that detected a condition.
        """

        return [
            finding
            for finding in self.findings
            if finding.triggered
        ]

    @property
    def has_triggered_findings(self) -> bool:
        """
        Indicate whether at least one deterministic rule triggered.
        """

        return self.triggered_rule_count > 0