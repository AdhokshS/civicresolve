from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from civicresolve.models.inference import ModelInferenceResult
from civicresolve.models.reasoning import ReasoningPacket


class ReasoningProvider(ABC):
    """
    Provider-independent interface for CivicResolve AI reasoning.

    The application depends on this interface rather than directly
    on a specific model runtime.
    """

    @abstractmethod
    def assess(
        self,
        packet: ReasoningPacket,
    ) -> ModelInferenceResult:
        """
        Produce the first structured assessment for a reasoning packet.
        """

    @abstractmethod
    def repair(
        self,
        packet: ReasoningPacket,
        *,
        previous_response: str,
        validation_feedback: Sequence[str],
    ) -> ModelInferenceResult:
        """
        Perform one bounded correction attempt after deterministic
        validation rejects the previous model response.
        """