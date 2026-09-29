from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import AwareDatetime, Field

from civicresolve.models.case import StrictModel


class SourceSystem(str, Enum):
    FORMS = "forms"
    PAYMENTS = "payments"
    DOCUMENTS = "documents"
    WORKFLOW = "workflow"
    EVENTS = "events"
    POLICY = "policy"


class EvidenceType(str, Enum):
    FORM_RECORD = "FORM_RECORD"
    PAYMENT_RECORD = "PAYMENT_RECORD"
    DOCUMENT_RECORD = "DOCUMENT_RECORD"
    WORKFLOW_STATE = "WORKFLOW_STATE"
    EVENT_RECORD = "EVENT_RECORD"
    POLICY_RULE = "POLICY_RULE"


class EvidenceItem(StrictModel):
    """
    Normalized evidence captured from a simulated source system.

    EvidenceItem does not represent an AI conclusion.
    It represents an observable record that a rule, reviewer,
    or AI assessment can cite.
    """

    evidence_id: str

    case_id: str
    application_id: str

    source_system: SourceSystem
    evidence_type: EvidenceType

    # Original identifier in the simulated source system.
    source_record_id: str

    # When the source record itself occurred or was last updated.
    observed_at: AwareDatetime

    # When CivicResolve captured the record for investigation.
    captured_at: AwareDatetime

    # Short human-readable explanation of why the record matters.
    summary: str

    # Normalized copy of the relevant source fields.
    fields: dict[str, Any] = Field(default_factory=dict)

    synthetic: bool = True


class EvidenceReference(StrictModel):
    """
    Lightweight citation used by rules and AI assessments.

    Instead of copying an entire EvidenceItem into every conclusion,
    downstream components reference the evidence by ID.
    """

    evidence_id: str
    reason: str


class EvidenceBundle(StrictModel):
    """
    All evidence reconstructed for a single case investigation.
    """

    case_id: str
    application_id: str

    items: list[EvidenceItem] = Field(default_factory=list)

    synthetic: bool = True

    def get(self, evidence_id: str) -> EvidenceItem | None:
        """
        Return an evidence item by ID.
        """
        for item in self.items:
            if item.evidence_id == evidence_id:
                return item

        return None

    def contains(self, evidence_id: str) -> bool:
        """
        Check whether an evidence ID exists in this bundle.
        """
        return self.get(evidence_id) is not None