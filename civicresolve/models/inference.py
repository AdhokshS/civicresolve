from __future__ import annotations

from pydantic import Field

from civicresolve.models.assessment import ModelAssessmentDraft
from civicresolve.models.case import StrictModel


class ModelInferenceResult(StrictModel):
    """
    Complete record of one model inference attempt.

    This metadata will later become part of the CivicResolve
    audit trail.
    """

    provider: str
    model_name: str

    prompt_version: str
    packet_version: str

    thinking_enabled: bool
    temperature: float

    duration_ms: int = Field(ge=0)

    raw_response: str

    draft: ModelAssessmentDraft