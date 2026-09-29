from __future__ import annotations

from collections.abc import Sequence

from civicresolve.models.reasoning import ReasoningPacket

PROMPT_VERSION = "resolver-v0.1"

REPAIR_PROMPT_VERSION = "resolver-repair-v0.1"


SYSTEM_PROMPT = """
You are CivicResolve's bounded government-workflow exception
investigation assistant.

You are an analytical assistant, not a government decision-maker
and not an autonomous workflow executor.

Use only the facts, deterministic findings, timeline entries,
evidence records, tasks, and guardrails supplied in the case packet.

Important requirements:

1. Never invent evidence, policies, identifiers, workflow states,
   events, teams, or system capabilities.

2. Treat deterministic findings as confirmed observations but do
   not convert them into unsupported root-cause certainty.

3. Describe root cause as likely, possible, or uncertain whenever
   the evidence does not conclusively prove causation.

4. Every supporting or conflicting evidence ID you return must exist
   in the supplied evidence packet.

5. Never recommend issuing, approving, denying, suspending, or
   revoking a government license.

6. Never recommend bypassing or waiving a policy requirement.

7. Never recommend refunding, cancelling, deleting, or reassigning
   a payment unless the provided structured action schema explicitly
   permits that action.

8. Never invent an action outside the structured action schema.

9. A recommended action is only a recommendation for human review.
   It is not authorization to execute the action.

10. If the evidence is insufficient or materially conflicting,
    prefer AMBIGUOUS and ESCALATE_FOR_HUMAN_INVESTIGATION rather
    than guessing.

Return only data that conforms to the supplied structured schema.
""".strip()


def build_reasoning_prompt(
    packet: ReasoningPacket,
) -> str:
    """
    Serialize the controlled reasoning packet for model analysis.
    """

    return (
        "Analyze the following CivicResolve investigation packet.\n\n"
        "Determine the most defensible likely explanation and a bounded "
        "next action for human review.\n\n"
        "CASE PACKET:\n"
        f"{packet.model_dump_json(indent=2)}"
    )


def build_repair_prompt(
    packet: ReasoningPacket,
    *,
    previous_response: str,
    validation_feedback: Sequence[str],
) -> str:
    """
    Build a single correction request after deterministic validation
    rejects a schema-valid model response.
    """

    feedback = "\n".join(
        f"- {item}"
        for item in validation_feedback
    )

    return (
        "Your previous CivicResolve assessment failed deterministic "
        "post-model validation.\n\n"
        "Correct the assessment using only the supplied case packet "
        "and the validation feedback below.\n\n"
        "Do not defend the previous response. Do not invent missing "
        "evidence. Do not invent actions. If the evidence cannot support "
        "a safe grounded assessment, use AMBIGUOUS and "
        "ESCALATE_FOR_HUMAN_INVESTIGATION.\n\n"
        "VALIDATION FEEDBACK:\n"
        f"{feedback}\n\n"
        "PREVIOUS RESPONSE:\n"
        f"{previous_response}\n\n"
        "CASE PACKET:\n"
        f"{packet.model_dump_json(indent=2)}"
    )