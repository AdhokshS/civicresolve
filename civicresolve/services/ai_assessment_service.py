from __future__ import annotations

from civicresolve.ai.provider import ReasoningProvider
from civicresolve.models.assessment_run import (
    AssessmentAttempt,
    AssessmentRunResult,
    AssessmentRunStatus,
)
from civicresolve.models.reasoning import ReasoningPacket
from civicresolve.models.validation import (
    AssessmentValidationResult,
)
from civicresolve.services.assessment_validation_service import (
    validate_model_assessment,
)


def _build_validation_feedback(
    validation: AssessmentValidationResult,
) -> tuple[str, ...]:
    return tuple(
        (
            f"{issue.severity.value}: "
            f"{issue.code}: "
            f"{issue.message}"
        )
        for issue in validation.issues
    )


def run_ai_assessment(
    packet: ReasoningPacket,
    provider: ReasoningProvider,
) -> AssessmentRunResult:
    """
    Run a bounded CivicResolve model-assessment cycle.

    Process:
    1. Run the initial model assessment.
    2. Deterministically validate the result.
    3. If rejected, provide validation feedback to the model.
    4. Allow exactly one correction attempt.
    5. If correction still fails, reject the AI result and require
       human investigation.

    The model never receives unlimited retry opportunities.
    """

    attempts: list[AssessmentAttempt] = []

    first_inference = provider.assess(
        packet
    )

    first_validation = validate_model_assessment(
        packet,
        first_inference.draft,
    )

    attempts.append(
        AssessmentAttempt(
            attempt_number=1,
            inference=first_inference,
            validation=first_validation,
        )
    )

    if (
        first_validation.is_valid
        and first_validation.assessment is not None
    ):
        return AssessmentRunResult(
            status=AssessmentRunStatus.VALIDATED,
            attempts=attempts,
            validated_assessment=(
                first_validation.assessment
            ),
            failure_reason=None,
            human_review_required=True,
        )

    feedback = _build_validation_feedback(
        first_validation
    )

    repair_inference = provider.repair(
        packet,
        previous_response=(
            first_inference.raw_response
        ),
        validation_feedback=feedback,
    )

    repair_validation = validate_model_assessment(
        packet,
        repair_inference.draft,
    )

    attempts.append(
        AssessmentAttempt(
            attempt_number=2,
            inference=repair_inference,
            validation=repair_validation,
        )
    )

    if (
        repair_validation.is_valid
        and repair_validation.assessment is not None
    ):
        return AssessmentRunResult(
            status=AssessmentRunStatus.VALIDATED,
            attempts=attempts,
            validated_assessment=(
                repair_validation.assessment
            ),
            failure_reason=None,
            human_review_required=True,
        )

    return AssessmentRunResult(
        status=(
            AssessmentRunStatus.HUMAN_REVIEW_REQUIRED
        ),
        attempts=attempts,
        validated_assessment=None,
        failure_reason=(
            "AI assessment failed deterministic validation "
            "after one bounded correction attempt."
        ),
        human_review_required=True,
    )