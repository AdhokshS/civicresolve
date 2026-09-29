from __future__ import annotations

from enum import Enum

from pydantic import Field

from civicresolve.models.assessment import ValidatedAssessment
from civicresolve.models.case import StrictModel


class ValidationSeverity(str, Enum):
    WARNING = "WARNING"
    ERROR = "ERROR"


class AssessmentValidationIssue(StrictModel):
    code: str
    severity: ValidationSeverity
    message: str


class AssessmentValidationResult(StrictModel):
    """
    Result of deterministic validation applied after model inference.

    A schema-valid model response is not automatically considered
    trustworthy. It must also pass CivicResolve evidence, action,
    category, and safety checks.
    """

    is_valid: bool

    issues: list[AssessmentValidationIssue] = Field(
        default_factory=list
    )

    assessment: ValidatedAssessment | None = None