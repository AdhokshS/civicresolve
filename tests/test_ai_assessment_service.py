from __future__ import annotations

from collections.abc import Sequence

from civicresolve.ai.prompts import (
    build_repair_prompt,
)
from civicresolve.ai.provider import (
    ReasoningProvider,
)
from civicresolve.data.scenarios import (
    build_integration_exception_case,
)
from civicresolve.models.assessment import (
    AssessmentCategory,
    ModelAssessmentDraft,
    RecommendedActionType,
    RecommendedOwnerRole,
)
from civicresolve.models.assessment_run import (
    AssessmentRunStatus,
)
from civicresolve.models.inference import (
    ModelInferenceResult,
)
from civicresolve.rules.engine import run_rule_engine
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


def _build_packet():
    case = build_integration_exception_case()

    evidence = build_evidence_bundle(case)

    rules = run_rule_engine(
        case,
        evidence,
    )

    context = build_investigation_context(
        case,
        evidence,
        rules,
    )

    return build_reasoning_packet(context)


def _build_valid_draft():
    return ModelAssessmentDraft(
        likely_category=(
            AssessmentCategory.SYSTEM_INTEGRATION
        ),
        likely_cause=(
            "A failed synchronization attempt likely prevented "
            "the confirmed payment state from reaching the workflow."
        ),
        alternative_hypotheses=[],
        supporting_evidence_ids=[
            "EVD-PAY-88219",
            "EVD-WF-1047",
            "EVD-EVT-91372",
        ],
        conflicting_evidence_ids=[],
        missing_information=[],
        recommended_action=(
            RecommendedActionType.INVESTIGATE_INTEGRATION_SYNC
        ),
        recommended_action_rationale=(
            "Review the failed synchronization event before "
            "preparing any workflow reconciliation."
        ),
        recommended_owner_role=(
            RecommendedOwnerRole.TECHNICAL_OPERATIONS
        ),
        safety_constraints=[
            (
                "Human authorization is required before "
                "any workflow state change."
            )
        ],
    )


def _build_invalid_draft():
    return _build_valid_draft().model_copy(
        update={
            "supporting_evidence_ids": [],
        }
    )


def _build_inference(
    draft: ModelAssessmentDraft,
    *,
    prompt_version: str,
) -> ModelInferenceResult:
    return ModelInferenceResult(
        provider="fake",
        model_name="fake-model",
        prompt_version=prompt_version,
        packet_version="1.0",
        thinking_enabled=False,
        temperature=0.0,
        duration_ms=1,
        raw_response=draft.model_dump_json(),
        draft=draft,
    )


class FakeReasoningProvider(
    ReasoningProvider
):
    def __init__(
        self,
        *,
        first_draft: ModelAssessmentDraft,
        repair_draft: ModelAssessmentDraft,
    ) -> None:
        self.first_draft = first_draft
        self.repair_draft = repair_draft

        self.assess_calls = 0
        self.repair_calls = 0

        self.last_previous_response: str | None = None

        self.last_validation_feedback: (
            tuple[str, ...] | None
        ) = None

    def assess(
        self,
        packet,
    ) -> ModelInferenceResult:
        self.assess_calls += 1

        return _build_inference(
            self.first_draft,
            prompt_version="fake-initial",
        )

    def repair(
        self,
        packet,
        *,
        previous_response: str,
        validation_feedback: Sequence[str],
    ) -> ModelInferenceResult:
        self.repair_calls += 1

        self.last_previous_response = (
            previous_response
        )

        self.last_validation_feedback = tuple(
            validation_feedback
        )

        return _build_inference(
            self.repair_draft,
            prompt_version="fake-repair",
        )


def test_valid_first_attempt_does_not_retry():
    provider = FakeReasoningProvider(
        first_draft=_build_valid_draft(),
        repair_draft=_build_valid_draft(),
    )

    result = run_ai_assessment(
        _build_packet(),
        provider,
    )

    assert (
        result.status
        == AssessmentRunStatus.VALIDATED
    )

    assert len(result.attempts) == 1

    assert provider.assess_calls == 1
    assert provider.repair_calls == 0

    assert result.validated_assessment is not None


def test_invalid_first_attempt_gets_one_repair():
    provider = FakeReasoningProvider(
        first_draft=_build_invalid_draft(),
        repair_draft=_build_valid_draft(),
    )

    result = run_ai_assessment(
        _build_packet(),
        provider,
    )

    assert (
        result.status
        == AssessmentRunStatus.VALIDATED
    )

    assert len(result.attempts) == 2

    assert provider.assess_calls == 1
    assert provider.repair_calls == 1

    assert result.validated_assessment is not None


def test_validation_feedback_is_sent_to_repair():
    provider = FakeReasoningProvider(
        first_draft=_build_invalid_draft(),
        repair_draft=_build_valid_draft(),
    )

    run_ai_assessment(
        _build_packet(),
        provider,
    )

    assert (
        provider.last_validation_feedback
        is not None
    )

    assert any(
        "MISSING_SUPPORTING_EVIDENCE"
        in feedback
        for feedback
        in provider.last_validation_feedback
    )


def test_second_invalid_attempt_fails_closed():
    provider = FakeReasoningProvider(
        first_draft=_build_invalid_draft(),
        repair_draft=_build_invalid_draft(),
    )

    result = run_ai_assessment(
        _build_packet(),
        provider,
    )

    assert (
        result.status
        == AssessmentRunStatus.HUMAN_REVIEW_REQUIRED
    )

    assert len(result.attempts) == 2

    assert result.validated_assessment is None

    assert result.failure_reason is not None

    assert result.human_review_required is True


def test_repair_prompt_preserves_privacy_and_feedback():
    packet = _build_packet()

    prompt = build_repair_prompt(
        packet,
        previous_response=(
            '{"supporting_evidence_ids":[]}'
        ),
        validation_feedback=[
            (
                "ERROR: MISSING_SUPPORTING_EVIDENCE: "
                "The model did not cite supporting evidence."
            )
        ],
    )

    assert (
        "MISSING_SUPPORTING_EVIDENCE"
        in prompt
    )

    assert "EVD-PAY-88219" in prompt

    assert (
        '{"supporting_evidence_ids":[]}'
        in prompt
    )

    assert "Harbor Street Coffee LLC" not in prompt