from civicresolve.ai.ollama_provider import (
    OllamaReasoningProvider,
)
from civicresolve.data.scenarios import (
    build_integration_exception_case,
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

    provider = OllamaReasoningProvider()

    result = provider.assess(
        packet
    )

    print()
    print("=== CIVICRESOLVE LIVE AI TEST ===")
    print()

    print("Provider:", result.provider)
    print("Model:", result.model_name)
    print("Prompt:", result.prompt_version)
    print("Duration ms:", result.duration_ms)

    print()
    print("=== STRUCTURED ASSESSMENT ===")
    print()

    print(
        result.draft.model_dump_json(
            indent=2
        )
    )


if __name__ == "__main__":
    main()