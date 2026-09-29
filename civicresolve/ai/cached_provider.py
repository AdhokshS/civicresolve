from __future__ import annotations

from collections.abc import Sequence

from civicresolve.ai.provider import ReasoningProvider
from civicresolve.models.assessment import (
    AssessmentCategory,
    ModelAssessmentDraft,
    RecommendedActionType,
    RecommendedOwnerRole,
)
from civicresolve.models.inference import ModelInferenceResult
from civicresolve.models.reasoning import ReasoningPacket

CACHED_PROMPT_VERSION = "cached-open-model-v0.1"

CACHED_MODEL_NAME = "qwen3.5:4b-q4_K_M"


class CachedAssessmentNotFoundError(LookupError):
    """
    Raised when demo mode has no precomputed assessment for a case.
    """


def _integration_assessment() -> ModelAssessmentDraft:
    return ModelAssessmentDraft(
        likely_category=AssessmentCategory.SYSTEM_INTEGRATION,
        likely_cause=(
            "A failed workflow synchronization likely prevented the "
            "confirmed payment state from reaching the licensing "
            "workflow after the payment completed successfully."
        ),
        alternative_hypotheses=[
            (
                "A delayed asynchronous workflow update could also "
                "explain the temporary state mismatch."
            )
        ],
        supporting_evidence_ids=[
            "EVD-PAY-88219",
            "EVD-WF-1047",
            "EVD-EVT-91372",
            "EVD-EVT-91374",
        ],
        conflicting_evidence_ids=[],
        missing_information=[],
        recommended_action=(
            RecommendedActionType.INVESTIGATE_INTEGRATION_SYNC
        ),
        recommended_action_rationale=(
            "Review the failed synchronization attempt and exhausted "
            "retry sequence. If the payment record remains confirmed, "
            "prepare any required workflow reconciliation for explicit "
            "human authorization."
        ),
        recommended_owner_role=(
            RecommendedOwnerRole.TECHNICAL_OPERATIONS
        ),
        safety_constraints=[
            (
                "Do not change workflow state without explicit human "
                "authorization."
            ),
            (
                "Do not approve or issue the license as part of this "
                "exception-resolution step."
            ),
        ],
    )


def _policy_assessment() -> ModelAssessmentDraft:
    return ModelAssessmentDraft(
        likely_category=AssessmentCategory.POLICY,
        likely_cause=(
            "The application is likely blocked because the required "
            "proof-of-insurance document is expired while the active "
            "policy requires a valid document."
        ),
        alternative_hypotheses=[],
        supporting_evidence_ids=[
            "EVD-POL-LIC-INS-001",
            "EVD-DOC-4451",
        ],
        conflicting_evidence_ids=[],
        missing_information=[],
        recommended_action=(
            RecommendedActionType.REQUEST_UPDATED_DOCUMENT
        ),
        recommended_action_rationale=(
            "Request an updated proof-of-insurance document and keep "
            "the case in human review until the policy requirement "
            "is satisfied."
        ),
        recommended_owner_role=(
            RecommendedOwnerRole.APPLICANT_SERVICES
        ),
        safety_constraints=[
            "Do not waive or bypass the documented policy requirement.",
            (
                "Do not advance or approve the license solely from "
                "the AI assessment."
            ),
        ],
    )


def _ownership_assessment() -> ModelAssessmentDraft:
    return ModelAssessmentDraft(
        likely_category=AssessmentCategory.OWNERSHIP_PROCESS,
        likely_cause=(
            "The workflow likely lost its downstream operational owner "
            "after the prior assignment was removed, leaving the case "
            "without a team or role responsible for the next stage."
        ),
        alternative_hypotheses=[
            (
                "An assignment may exist in an external queue that is "
                "not represented in the supplied evidence."
            )
        ],
        supporting_evidence_ids=[
            "EVD-WF-1061",
            "EVD-EVT-91504",
        ],
        conflicting_evidence_ids=[],
        missing_information=[],
        recommended_action=(
            RecommendedActionType.ROUTE_FOR_OWNER_ASSIGNMENT
        ),
        recommended_action_rationale=(
            "Route the case to a licensing supervisor for human review "
            "and assignment of an appropriate operational owner."
        ),
        recommended_owner_role=(
            RecommendedOwnerRole.LICENSING_SUPERVISOR
        ),
        safety_constraints=[
            (
                "Do not infer or assign a specific individual without "
                "human authorization."
            ),
            (
                "Ownership routing must not itself approve or complete "
                "the licensing workflow."
            ),
        ],
    )


def _data_assessment() -> ModelAssessmentDraft:
    return ModelAssessmentDraft(
        likely_category=AssessmentCategory.DATA,
        likely_cause=(
            "The payment record likely cannot reconcile to this "
            "application because the payment references a different "
            "application identifier."
        ),
        alternative_hypotheses=[
            (
                "The reference mismatch could reflect an upstream "
                "identifier-linkage or data-entry issue."
            )
        ],
        supporting_evidence_ids=[
            "EVD-PAY-88410",
            "EVD-FORM-LIC-2026-1074",
        ],
        conflicting_evidence_ids=[],
        missing_information=[],
        recommended_action=(
            RecommendedActionType.RECONCILE_PAYMENT_REFERENCE
        ),
        recommended_action_rationale=(
            "Send the mismatched payment and application references "
            "to payment-reconciliation staff for human investigation "
            "before any record linkage is changed."
        ),
        recommended_owner_role=(
            RecommendedOwnerRole.PAYMENT_RECONCILIATION
        ),
        safety_constraints=[
            (
                "Do not automatically reassign the payment to another "
                "application."
            ),
            (
                "Do not modify financial or workflow records without "
                "human authorization."
            ),
        ],
    )


CACHED_ASSESSMENTS = {
    "CASE-1047": _integration_assessment(),
    "CASE-1052": _policy_assessment(),
    "CASE-1061": _ownership_assessment(),
    "CASE-1074": _data_assessment(),
}


class CachedReasoningProvider(ReasoningProvider):
    """
    Instant provider for the public demonstration experience.

    Assessments are precomputed from the open local model workflow,
    stored as structured drafts, and still passed through the same
    CivicResolve deterministic validation layer used for live AI.
    """

    def assess(
        self,
        packet: ReasoningPacket,
    ) -> ModelInferenceResult:
        try:
            draft = CACHED_ASSESSMENTS[
                packet.case_id
            ]
        except KeyError as exc:
            raise CachedAssessmentNotFoundError(
                "No cached assessment exists for "
                f"case {packet.case_id}."
            ) from exc

        raw_response = draft.model_dump_json()

        return ModelInferenceResult(
            provider="cached",
            model_name=CACHED_MODEL_NAME,
            prompt_version=CACHED_PROMPT_VERSION,
            packet_version=packet.packet_version,
            thinking_enabled=False,
            temperature=0.0,
            duration_ms=0,
            raw_response=raw_response,
            draft=draft,
        )

    def repair(
        self,
        packet: ReasoningPacket,
        *,
        previous_response: str,
        validation_feedback: Sequence[str],
    ) -> ModelInferenceResult:
        """
        Cached assessments are fixed demo artifacts.

        If deterministic validation rejects one, returning it again
        causes the orchestration layer to fail closed after the one
        permitted repair attempt.
        """

        return self.assess(packet)