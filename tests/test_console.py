from civicresolve.models.assessment import (
    ConfidenceLevel,
)
from civicresolve.models.assessment_run import (
    AssessmentRunStatus,
)
from civicresolve.ui.console import (
    build_case_workspaces,
    build_queue_rows,
)


def test_console_builds_all_four_demo_cases():
    workspaces = build_case_workspaces()

    assert set(workspaces) == {
        "CASE-1047",
        "CASE-1052",
        "CASE-1061",
        "CASE-1074",
    }


def test_every_console_case_has_triggered_finding():
    workspaces = build_case_workspaces()

    assert all(
        workspace.primary_finding is not None
        for workspace in workspaces.values()
    )


def test_every_console_case_has_validated_assessment():
    workspaces = build_case_workspaces()

    for workspace in workspaces.values():
        assert (
            workspace.assessment_run.status
            == AssessmentRunStatus.VALIDATED
        )

        assessment = (
            workspace.validated_assessment
        )

        assert assessment is not None

        assert (
            assessment.human_approval_required
            is True
        )

        assert (
            assessment.confidence
            == ConfidenceLevel.HIGH
        )


def test_queue_contains_four_exception_categories():
    rows = build_queue_rows(
        build_case_workspaces()
    )

    categories = {
        row["Exception"]
        for row in rows
    }

    assert categories == {
        "SYSTEM_INTEGRATION",
        "POLICY",
        "OWNERSHIP_PROCESS",
        "DATA",
    }