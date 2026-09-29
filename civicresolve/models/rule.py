from __future__ import annotations

from enum import Enum

from pydantic import Field

from civicresolve.models.case import StrictModel
from civicresolve.models.evidence import EvidenceReference


class RuleSeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RuleCategory(str, Enum):
    DATA = "DATA"
    POLICY = "POLICY"
    SYSTEM_INTEGRATION = "SYSTEM_INTEGRATION"
    OWNERSHIP_PROCESS = "OWNERSHIP_PROCESS"


class RuleFinding(StrictModel):
    """
    Deterministic finding produced by the CivicResolve rule engine.

    A finding represents an objective condition detected from structured
    records. It does not claim root-cause certainty.
    """

    rule_id: str
    rule_version: str

    finding_code: str
    title: str
    description: str

    category: RuleCategory
    severity: RuleSeverity

    triggered: bool

    evidence: list[EvidenceReference] = Field(default_factory=list)

    # Human-readable statement describing what the rule observed.
    observed_condition: str

    # Explicitly states what the rule does NOT prove.
    limitation: str