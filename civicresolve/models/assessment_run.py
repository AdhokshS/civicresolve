from __future__ import annotations

from enum import Enum

from pydantic import Field

from civicresolve.models.assessment import ValidatedAssessment
from civicresolve.models.case import StrictModel
from civicresolve.models.inference import ModelInferenceResult
from civicresolve.models.validation import (
    AssessmentValidationResult,
)


class AssessmentRunStatus(str, Enum):
    VALIDATED = "VALIDATED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"


class AssessmentAttempt(StrictModel):
    """
    One model attempt and its deterministic validation result.
    """

    attempt_number: int = Field(ge=1)

    inference: ModelInferenceResult

    validation: AssessmentValidationResult


class AssessmentRunResult(StrictModel):
    """
    Full outcome of the CivicResolve AI assessment process.

    At most one repair attempt is performed.
    """

    status: AssessmentRunStatus

    attempts: list[AssessmentAttempt] = Field(
        default_factory=list
    )

    validated_assessment: ValidatedAssessment | None = None

    failure_reason: str | None = None

    human_review_required: bool = True