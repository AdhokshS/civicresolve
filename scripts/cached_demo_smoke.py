from civicresolve.ai.cached_provider import (
    CachedReasoningProvider,
)
from civicresolve.data.scenarios import (
    build_integration_exception_case,
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


def main() -> None:
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

    packet = build_reasoning_packet(
        context
    )

    result = run_ai_assessment(
        packet,
        CachedReasoningProvider(),
    )

    print()
    print("=== CIVICRESOLVE DEMO MODE ===")
    print()

    print("Status:", result.status.value)
    print("Attempts:", len(result.attempts))
    print(
        "Provider:",
        result.attempts[0].inference.provider,
    )

    assessment = result.validated_assessment

    if assessment is None:
        print("Validated assessment: unavailable")
        return

    print(
        "Category:",
        assessment.likely_category.value,
    )
    print(
        "Confidence:",
        assessment.confidence.value,
    )
    print(
        "Action:",
        assessment.recommended_action.value,
    )
    print(
        "Owner:",
        assessment.recommended_owner_role.value,
    )
    print(
        "Human approval required:",
        assessment.human_approval_required,
    )


if __name__ == "__main__":
    main()