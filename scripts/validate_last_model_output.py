from civicresolve.data.scenarios import (
    build_integration_exception_case,
)
from civicresolve.models.assessment import (
    ModelAssessmentDraft,
)
from civicresolve.rules.engine import run_rule_engine
from civicresolve.services.assessment_validation_service import (
    validate_model_assessment,
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

    packet = build_reasoning_packet(context)

    draft = ModelAssessmentDraft(
        likely_category="SYSTEM_INTEGRATION",
        likely_cause=(
            "The licensing workflow system failed to receive or "
            "process the state update from the payment processor, "
            "resulting in a cross-system state inconsistency where "
            "the payment is confirmed but the workflow remains "
            "stuck at AWAITING_PAYMENT."
        ),
        alternative_hypotheses=[],
        supporting_evidence_ids=[],
        conflicting_evidence_ids=[],
        missing_information=[],
        recommended_action=(
            "ESCALATE_FOR_HUMAN_INVESTIGATION"
        ),
        recommended_action_rationale=(
            "Automated retry mechanisms were exhausted after an "
            "HTTP 503 error. Human investigation is required."
        ),
        recommended_owner_role=(
            "LICENSING_OPERATIONS"
        ),
        safety_constraints=[
            (
                "Do not manually update the workflow state "
                "without explicit human authorization."
            ),
            (
                "Do not bypass the AWAITING_PAYMENT "
                "stage requirement."
            ),
        ],
    )

    result = validate_model_assessment(
        packet,
        draft,
    )

    print()
    print("=== POST-MODEL VALIDATION ===")
    print()

    print("Accepted:", result.is_valid)
    print()

    for issue in result.issues:
        print(
            f"{issue.severity.value}: "
            f"{issue.code} - {issue.message}"
        )

    print()
    print(
        "Validated assessment available:",
        result.assessment is not None,
    )


if __name__ == "__main__":
    main()