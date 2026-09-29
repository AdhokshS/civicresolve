from __future__ import annotations

from collections.abc import Sequence
from time import perf_counter

from ollama import Client
from pydantic import ValidationError

from civicresolve.ai.prompts import (
    PROMPT_VERSION,
    REPAIR_PROMPT_VERSION,
    SYSTEM_PROMPT,
    build_reasoning_prompt,
    build_repair_prompt,
)
from civicresolve.ai.provider import ReasoningProvider
from civicresolve.models.assessment import ModelAssessmentDraft
from civicresolve.models.inference import ModelInferenceResult
from civicresolve.models.reasoning import ReasoningPacket

DEFAULT_MODEL = "qwen3.5:4b-q4_K_M"


class OllamaInferenceError(RuntimeError):
    """
    Raised when local-model inference fails or produces output
    that does not satisfy the CivicResolve assessment contract.
    """


class OllamaReasoningProvider(ReasoningProvider):
    """
    Local structured-reasoning provider backed by Ollama.

    Model output remains untrusted until CivicResolve performs
    deterministic post-model validation.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        host: str = "http://localhost:11434",
        client: Client | None = None,
    ) -> None:
        self.model_name = model_name

        self.client = (
            client
            if client is not None
            else Client(host=host)
        )

    def _run_inference(
        self,
        packet: ReasoningPacket,
        *,
        user_prompt: str,
        prompt_version: str,
    ) -> ModelInferenceResult:
        schema = ModelAssessmentDraft.model_json_schema()

        started_at = perf_counter()

        try:
            response = self.client.chat(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
                format=schema,
                options={
                    "temperature": 0,
                    "num_ctx": 4096,
                },
                think=False,
                stream=False,
                keep_alive="5m",
            )

            raw_response = response.message.content

            draft = ModelAssessmentDraft.model_validate_json(
                raw_response
            )

        except ValidationError as exc:
            raise OllamaInferenceError(
                "Ollama returned a response that failed "
                "CivicResolve schema validation."
            ) from exc

        except Exception as exc:
            raise OllamaInferenceError(
                f"Ollama inference failed: {exc}"
            ) from exc

        duration_ms = int(
            (perf_counter() - started_at) * 1000
        )

        return ModelInferenceResult(
            provider="ollama",
            model_name=self.model_name,
            prompt_version=prompt_version,
            packet_version=packet.packet_version,
            thinking_enabled=False,
            temperature=0.0,
            duration_ms=duration_ms,
            raw_response=raw_response,
            draft=draft,
        )

    def assess(
        self,
        packet: ReasoningPacket,
    ) -> ModelInferenceResult:
        return self._run_inference(
            packet,
            user_prompt=build_reasoning_prompt(
                packet
            ),
            prompt_version=PROMPT_VERSION,
        )

    def repair(
        self,
        packet: ReasoningPacket,
        *,
        previous_response: str,
        validation_feedback: Sequence[str],
    ) -> ModelInferenceResult:
        return self._run_inference(
            packet,
            user_prompt=build_repair_prompt(
                packet,
                previous_response=previous_response,
                validation_feedback=validation_feedback,
            ),
            prompt_version=REPAIR_PROMPT_VERSION,
        )