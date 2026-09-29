from __future__ import annotations

import pytest

from civicresolve.ai.cached_provider import (
    CachedAssessmentNotFoundError,
    CachedReasoningProvider,
)
from civicresolve.data.scenarios import (
    build_integration_exception_case,
)
from civicresolve.models.assessment import (
    AssessmentCategory,
    RecommendedActionType,
)
from civicresolve.models.assessment_run import (
    AssessmentRunStatus,
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


def test_cached_provider_returns_hero_assessment():
    provider = CachedReasoningProvider()

    result = provider.assess(
        _build_packet()
    )

    assert result.provider == "cached"

    assert (
        result.draft.likely_category
        == AssessmentCategory.SYSTEM_INTEGRATION
    )

    assert (
        result.draft.recommended_action
        == RecommendedActionType.INVESTIGATE_INTEGRATION_SYNC
    )

    assert result.duration_ms == 0


def test_cached_hero_assessment_passes_full_pipeline():
    provider = CachedReasoningProvider()

    result = run_ai_assessment(
        _build_packet(),
        provider,
    )

    assert (
        result.status
        == AssessmentRunStatus.VALIDATED
    )

    assert len(result.attempts) == 1

    assert result.validated_assessment is not None

    assert (
        result.validated_assessment.human_approval_required
        is True
    )


def test_cached_assessment_cites_real_evidence():
    provider = CachedReasoningProvider()

    result = provider.assess(
        _build_packet()
    )

    evidence_ids = set(
        result.draft.supporting_evidence_ids
    )

    assert "EVD-PAY-88219" in evidence_ids
    assert "EVD-WF-1047" in evidence_ids


def test_unknown_case_fails_explicitly():
    packet = _build_packet().model_copy(
        update={
            "case_id": "CASE-NOT-CACHED",
        }
    )

    provider = CachedReasoningProvider()

    with pytest.raises(
        CachedAssessmentNotFoundError,
        match="CASE-NOT-CACHED",
    ):
        provider.assess(packet)


def test_cached_repair_does_not_invent_new_output():
    provider = CachedReasoningProvider()

    packet = _build_packet()

    first = provider.assess(packet)

    second = provider.repair(
        packet,
        previous_response=first.raw_response,
        validation_feedback=[
            "Synthetic validation feedback."
        ],
    )

    assert (
        second.raw_response
        == first.raw_response
    )