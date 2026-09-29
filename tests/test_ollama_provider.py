from __future__ import annotations

from types import SimpleNamespace

import pytest

from civicresolve.ai.ollama_provider import (
    OllamaInferenceError,
    OllamaReasoningProvider,
)
from civicresolve.ai.prompts import build_reasoning_prompt
from civicresolve.data.scenarios import (
    build_integration_exception_case,
)
from civicresolve.models.assessment import (
    AssessmentCategory,
    ModelAssessmentDraft,
    RecommendedActionType,
    RecommendedOwnerRole,
)
from civicresolve.rules.engine import run_rule_engine
from civicresolve.services.context_service import (
    build_investigation_context,
)
from civicresolve.services.evidence_service import (
    build_evidence_bundle,
)
from civicresolve.services.reasoning_service import (
    build_reasoning_packet,
)


class FakeOllamaClient:
    def __init__(
        self,
        response_content: str,
    ) -> None:
        self.response_content = response_content
        self.last_request = None

    def chat(self, **kwargs):
        self.last_request = kwargs

        return SimpleNamespace(
            message=SimpleNamespace(
                content=self.response_content
            )
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


def _build_valid_response() -> str:
    draft = ModelAssessmentDraft(
        likely_category=(
            AssessmentCategory.SYSTEM_INTEGRATION
        ),
        likely_cause=(
            "The failed synchronization event likely prevented "
            "the confirmed payment state from reaching the workflow."
        ),
        alternative_hypotheses=[
            (
                "A delayed asynchronous workflow update "
                "could still be pending."
            )
        ],
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
            "preparing any payment-state reconciliation."
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

    return draft.model_dump_json()


def test_ollama_provider_returns_structured_result():
    client = FakeOllamaClient(
        _build_valid_response()
    )

    provider = OllamaReasoningProvider(
        client=client,
    )

    result = provider.assess(
        _build_packet()
    )

    assert result.provider == "ollama"

    assert (
        result.model_name
        == "qwen3.5:4b-q4_K_M"
    )

    assert result.thinking_enabled is False
    assert result.temperature == 0.0

    assert (
        result.draft.likely_category
        == AssessmentCategory.SYSTEM_INTEGRATION
    )


def test_ollama_provider_uses_structured_schema():
    client = FakeOllamaClient(
        _build_valid_response()
    )

    provider = OllamaReasoningProvider(
        client=client,
    )

    provider.assess(
        _build_packet()
    )

    request = client.last_request

    assert request is not None

    assert (
        request["format"]["title"]
        == "ModelAssessmentDraft"
    )

    assert request["think"] is False
    assert request["stream"] is False

    assert (
        request["options"]["temperature"]
        == 0
    )


def test_reasoning_prompt_does_not_contain_business_name():
    packet = _build_packet()

    prompt = build_reasoning_prompt(
        packet
    )

    assert "Harbor Street Coffee LLC" not in prompt

    assert "EVD-PAY-88219" in prompt
    assert "EVD-EVT-91372" in prompt


def test_ollama_provider_rejects_invalid_model_output():
    client = FakeOllamaClient(
        '{"recommended_action":"REFUND_PAYMENT"}'
    )

    provider = OllamaReasoningProvider(
        client=client,
    )

    with pytest.raises(
        OllamaInferenceError,
        match="schema validation",
    ):
        provider.assess(
            _build_packet()
        )