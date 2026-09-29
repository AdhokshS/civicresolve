from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from civicresolve.db.audit_repository import (
    AuditRepository,
)
from civicresolve.models.audit import (
    AuditEvent,
    AuditEventType,
    HumanReviewDecision,
)
from civicresolve.services.action_service import (
    ActionNotAuthorizedError,
    build_authorized_action_plan,
    ensure_action_preview_audit_event,
    simulate_controlled_action,
)
from civicresolve.services.audit_service import (
    ensure_ai_assessment_audit_event,
    get_latest_human_review_event,
    record_human_review_decision,
)
from civicresolve.ui.console import (
    CaseWorkspace,
    build_case_workspaces,
)
from civicresolve.ui.insights import (
    render_operational_insights_panel,
)

st.set_page_config(
    page_title="CivicResolve",
    page_icon="C",
    layout="wide",
    initial_sidebar_state="collapsed",
)


ACTION_LABELS = {
    "INVESTIGATE_INTEGRATION_SYNC": "Investigate integration sync",
    "PREPARE_PAYMENT_STATE_RECONCILIATION": (
        "Prepare payment-state reconciliation"
    ),
    "REQUEST_UPDATED_DOCUMENT": "Request updated document",
    "ROUTE_FOR_OWNER_ASSIGNMENT": "Route for owner assignment",
    "RECONCILE_PAYMENT_REFERENCE": "Reconcile payment reference",
    "ESCALATE_FOR_HUMAN_INVESTIGATION": (
        "Escalate for human investigation"
    ),
    "NO_ACTION": "No action",
}

CATEGORY_LABELS = {
    "SYSTEM_INTEGRATION": "Integration failure",
    "POLICY": "Policy blocker",
    "OWNERSHIP_PROCESS": "Ownership gap",
    "DATA": "Data linkage",
    "AMBIGUOUS": "Ambiguous",
}

OWNER_LABELS = {
    "LICENSING_OPERATIONS": "Licensing Operations",
    "LICENSING_SUPERVISOR": "Licensing Supervisor",
    "APPLICANT_SERVICES": "Applicant Services",
    "REVENUE_OPERATIONS": "Revenue Operations",
    "PAYMENT_RECONCILIATION": "Payment Reconciliation",
    "TECHNICAL_OPERATIONS": "Technical Operations",
    "HUMAN_REVIEW": "Human Review",
}

REVIEW_OPTIONS = {
    "Authorize recommended next-step preparation": (
        HumanReviewDecision.AUTHORIZE_NEXT_STEP_PREPARATION
    ),
    "Request additional evidence": (
        HumanReviewDecision.REQUEST_ADDITIONAL_EVIDENCE
    ),
    "Reject recommendation": (
        HumanReviewDecision.REJECT_RECOMMENDATION
    ),
}

REVIEW_LABELS = {
    "AUTHORIZE_NEXT_STEP_PREPARATION": (
        "Authorized next-step preparation"
    ),
    "REQUEST_ADDITIONAL_EVIDENCE": (
        "Additional evidence requested"
    ),
    "REJECT_RECOMMENDATION": (
        "Recommendation rejected"
    ),
}


st.markdown(
    """
    <style>
        .block-container {
            max-width: 1450px;
            padding-top: 1.3rem;
            padding-bottom: 3.5rem;
        }

        h1 {
            letter-spacing: -0.035em;
        }

        h2, h3 {
            letter-spacing: -0.02em;
        }

        .cr-kicker {
            font-size: 0.74rem;
            font-weight: 700;
            letter-spacing: 0.11em;
            text-transform: uppercase;
            opacity: 0.60;
            margin-bottom: 0.25rem;
        }

        .cr-subtitle {
            font-size: 1.04rem;
            line-height: 1.55;
            max-width: 980px;
            opacity: 0.76;
            margin-top: -0.4rem;
            margin-bottom: 0.8rem;
        }

        .cr-badges {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
            margin-bottom: 1.15rem;
        }

        .cr-badge {
            display: inline-block;
            border: 1px solid rgba(128, 128, 128, 0.25);
            border-radius: 999px;
            padding: 0.28rem 0.62rem;
            font-size: 0.76rem;
            opacity: 0.78;
        }

        .cr-flow {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 0.55rem;
            margin: 0.65rem 0 1.3rem 0;
        }

        .cr-flow-step {
            border: 1px solid rgba(128, 128, 128, 0.20);
            border-radius: 8px;
            padding: 0.60rem 0.7rem;
            font-size: 0.80rem;
            font-weight: 650;
            text-align: center;
            opacity: 0.88;
        }

        div[data-testid="stMetric"] {
            border: 1px solid rgba(128, 128, 128, 0.20);
            border-radius: 10px;
            padding: 0.75rem 0.9rem;
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid rgba(128, 128, 128, 0.18);
            border-radius: 8px;
        }

        .cr-section-label {
            font-size: 0.74rem;
            font-weight: 700;
            letter-spacing: 0.09em;
            text-transform: uppercase;
            opacity: 0.58;
            margin-bottom: 0.18rem;
        }

        .cr-case-heading {
            font-size: 1.65rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            margin-bottom: 0.15rem;
        }

        .cr-case-meta {
            font-size: 0.88rem;
            opacity: 0.65;
            margin-bottom: 1rem;
        }

        .cr-signal {
            border: 1px solid rgba(128, 128, 128, 0.22);
            border-radius: 11px;
            padding: 0.95rem 1rem;
            min-height: 132px;
        }

        .cr-signal-label {
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            opacity: 0.56;
            font-weight: 700;
        }

        .cr-signal-value {
            font-size: 1.35rem;
            font-weight: 700;
            margin-top: 0.32rem;
            margin-bottom: 0.25rem;
        }

        .cr-signal-detail {
            font-size: 0.84rem;
            opacity: 0.72;
            line-height: 1.35;
        }

        .cr-success {
            border-top: 4px solid #36a269;
        }

        .cr-warning {
            border-top: 4px solid #d59b2d;
        }

        .cr-danger {
            border-top: 4px solid #d75b5b;
        }

        .cr-neutral {
            border-top: 4px solid #5c8fd6;
        }

        .cr-detection-banner {
            border: 1px solid rgba(213, 155, 45, 0.35);
            border-left: 4px solid #d59b2d;
            border-radius: 8px;
            padding: 0.85rem 1rem;
            margin-top: 0.8rem;
            margin-bottom: 1rem;
            background: rgba(213, 155, 45, 0.07);
        }

        .cr-detection-title {
            font-weight: 700;
            font-size: 1rem;
            margin-bottom: 0.2rem;
        }

        .cr-small {
            font-size: 0.82rem;
            opacity: 0.70;
        }

        .cr-action-card {
            border: 1px solid rgba(92, 143, 214, 0.30);
            border-left: 4px solid #5c8fd6;
            border-radius: 9px;
            padding: 1rem 1.05rem;
            background: rgba(92, 143, 214, 0.06);
        }

        .cr-action-title {
            font-size: 1.18rem;
            font-weight: 700;
            margin-bottom: 0.3rem;
        }

        .cr-human-gate {
            border: 1px solid rgba(92, 143, 214, 0.35);
            border-left: 4px solid #5c8fd6;
            border-radius: 9px;
            padding: 0.9rem 1rem;
            margin-top: 1rem;
            background: rgba(92, 143, 214, 0.07);
        }

        .cr-human-gate strong {
            font-size: 0.93rem;
        }

        .cr-note {
            border: 1px solid rgba(128, 128, 128, 0.22);
            border-radius: 8px;
            padding: 0.75rem 0.9rem;
            opacity: 0.76;
            font-size: 0.84rem;
        }

        .cr-confidence {
            display: inline-block;
            border: 1px solid rgba(54, 162, 105, 0.38);
            background: rgba(54, 162, 105, 0.08);
            border-radius: 999px;
            padding: 0.25rem 0.6rem;
            font-size: 0.78rem;
            font-weight: 700;
            margin-bottom: 0.55rem;
        }

        .cr-integrity-good {
            border-left: 4px solid #36a269;
            border-radius: 7px;
            padding: 0.75rem 0.9rem;
            background: rgba(54, 162, 105, 0.07);
            margin-bottom: 1rem;
        }

        .cr-integrity-bad {
            border-left: 4px solid #d75b5b;
            border-radius: 7px;
            padding: 0.75rem 0.9rem;
            background: rgba(215, 91, 91, 0.07);
            margin-bottom: 1rem;
        }

        .cr-locked {
            border: 1px solid rgba(213, 155, 45, 0.32);
            border-left: 4px solid #d59b2d;
            border-radius: 9px;
            padding: 1rem;
            background: rgba(213, 155, 45, 0.06);
            margin-bottom: 1rem;
        }

        .cr-safe-action {
            border: 1px solid rgba(54, 162, 105, 0.32);
            border-left: 4px solid #36a269;
            border-radius: 9px;
            padding: 1rem;
            background: rgba(54, 162, 105, 0.06);
            margin-bottom: 1rem;
        }

        @media (max-width: 900px) {
            .cr-flow {
                grid-template-columns: 1fr 1fr;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def load_workspaces() -> dict[str, CaseWorkspace]:
    return build_case_workspaces()


@st.cache_resource
def load_audit_repository() -> AuditRepository:
    return AuditRepository()


def humanize(value: str) -> str:
    return value.replace("_", " ").title()


def category_label(value: str) -> str:
    return CATEGORY_LABELS.get(
        value,
        humanize(value),
    )


def action_label(value: str) -> str:
    return ACTION_LABELS.get(
        value,
        humanize(value),
    )


def owner_label(value: str) -> str:
    return OWNER_LABELS.get(
        value,
        humanize(value),
    )


def review_label(value: str) -> str:
    return REVIEW_LABELS.get(
        value,
        humanize(value),
    )


def short_hash(
    value: str | None,
) -> str:
    if not value:
        return "—"

    return f"{value[:12]}…"


def format_case_option(
    case_id: str,
    workspaces: dict[str, CaseWorkspace],
) -> str:
    workspace = workspaces[case_id]

    return (
        f"{case_id} · "
        f"{workspace.case.application.applicant.business_name}"
    )


def build_display_queue(
    workspaces: dict[str, CaseWorkspace],
) -> pd.DataFrame:
    rows: list[dict[str, str]] = []

    for workspace in workspaces.values():
        case = workspace.case
        finding = workspace.primary_finding
        assessment = workspace.validated_assessment

        category = (
            finding.category.value
            if finding is not None
            else "NONE"
        )

        action = (
            assessment.recommended_action.value
            if assessment is not None
            else "ESCALATE_FOR_HUMAN_INVESTIGATION"
        )

        rows.append(
            {
                "Case": case.case_id,
                "Organization": (
                    case.application.applicant.business_name
                ),
                "Pattern": category_label(category),
                "Severity": (
                    finding.severity.value
                    if finding is not None
                    else case.severity.value
                ),
                "Stage": humanize(
                    case.workflow.current_stage.value
                ),
                "Status": humanize(
                    case.status.value
                ),
                "Recommended next step": (
                    action_label(action)
                ),
            }
        )

    return pd.DataFrame(rows)


def render_signal_card(
    *,
    label: str,
    value: str,
    detail: str,
    tone: str,
) -> None:
    st.markdown(
        f"""
        <div class="cr-signal cr-{escape(tone)}">
            <div class="cr-signal-label">
                {escape(label)}
            </div>
            <div class="cr-signal-value">
                {escape(value)}
            </div>
            <div class="cr-signal-detail">
                {escape(detail)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_integration_http_detail(
    workspace: CaseWorkspace,
) -> str:
    retry_event = next(
        (
            event
            for event in workspace.case.events
            if event.event_type.value
            == "RETRY_EXHAUSTED"
        ),
        None,
    )

    if retry_event is None:
        return "Workflow synchronization failed"

    status = (
        retry_event.details.get(
            "final_http_status"
        )
        or retry_event.details.get(
            "http_status"
        )
    )

    if status is not None:
        return f"HTTP {status} · retry exhausted"

    return "Retry exhausted"


def render_case_signals(
    workspace: CaseWorkspace,
) -> None:
    case = workspace.case
    finding = workspace.primary_finding

    category = (
        finding.category.value
        if finding is not None
        else ""
    )

    columns = st.columns(
        3,
        gap="medium",
    )

    if category == "SYSTEM_INTEGRATION":
        with columns[0]:
            render_signal_card(
                label="Payment system",
                value=case.payment.status.value,
                detail=(
                    f"{case.payment.currency} "
                    f"{case.payment.amount} · "
                    f"{humanize(case.payment.reconciliation_state.value)}"
                ),
                tone="success",
            )

        with columns[1]:
            render_signal_card(
                label="Licensing workflow",
                value=humanize(
                    case.workflow.payment_state.value
                ),
                detail=(
                    "Workflow stage · "
                    f"{humanize(case.workflow.current_stage.value)}"
                ),
                tone="warning",
            )

        with columns[2]:
            render_signal_card(
                label="Integration",
                value="Failed",
                detail=get_integration_http_detail(
                    workspace
                ),
                tone="danger",
            )

    elif category == "POLICY":
        expired_document = next(
            (
                document
                for document in case.documents
                if document.status.value == "EXPIRED"
            ),
            case.documents[0],
        )

        policy = case.policy_requirements[0]

        with columns[0]:
            render_signal_card(
                label="Required document",
                value=humanize(
                    expired_document.status.value
                ),
                detail=expired_document.document_type,
                tone="danger",
            )

        with columns[1]:
            render_signal_card(
                label="Policy requirement",
                value="Required",
                detail=policy.name,
                tone="warning",
            )

        with columns[2]:
            render_signal_card(
                label="Workflow",
                value=humanize(
                    case.workflow.current_stage.value
                ),
                detail=(
                    "Next · "
                    f"{humanize(case.workflow.expected_next_stage.value)}"
                ),
                tone="neutral",
            )

    elif category == "OWNERSHIP_PROCESS":
        owner_event = next(
            (
                event
                for event in case.events
                if event.event_type.value
                == "OWNER_REMOVED"
            ),
            None,
        )

        with columns[0]:
            render_signal_card(
                label="Workflow stage",
                value=humanize(
                    case.workflow.current_stage.value
                ),
                detail=(
                    "Next · "
                    f"{humanize(case.workflow.expected_next_stage.value)}"
                ),
                tone="neutral",
            )

        with columns[1]:
            render_signal_card(
                label="Current owner",
                value="Unassigned",
                detail="No assigned team or role",
                tone="danger",
            )

        with columns[2]:
            render_signal_card(
                label="Assignment event",
                value="Owner removed",
                detail=(
                    owner_event.message
                    if owner_event is not None
                    else "Previous ownership cleared"
                ),
                tone="warning",
            )

    elif category == "DATA":
        with columns[0]:
            render_signal_card(
                label="Current application",
                value=case.application.application_id,
                detail="Business-license application",
                tone="neutral",
            )

        with columns[1]:
            render_signal_card(
                label="Payment reference",
                value=case.payment.application_id,
                detail="Does not match current application",
                tone="danger",
            )

        with columns[2]:
            render_signal_card(
                label="Reconciliation",
                value=humanize(
                    case.payment.reconciliation_state.value
                ),
                detail="Human reconciliation required",
                tone="warning",
            )


def detection_headline(
    workspace: CaseWorkspace,
) -> str:
    finding = workspace.primary_finding

    if finding is None:
        return "No deterministic exception detected"

    headlines = {
        "SYSTEM_INTEGRATION": (
            "Cross-system state mismatch detected"
        ),
        "POLICY": (
            "Policy requirement blocks progression"
        ),
        "OWNERSHIP_PROCESS": (
            "Workflow has no accountable owner"
        ),
        "DATA": (
            "Payment reference does not match application"
        ),
    }

    return headlines.get(
        finding.category.value,
        finding.title,
    )


def render_top_metrics(
    workspaces: dict[str, CaseWorkspace],
) -> None:
    total = len(workspaces)

    patterns = {
        workspace.primary_finding.category.value
        for workspace in workspaces.values()
        if workspace.primary_finding is not None
    }

    grounded = sum(
        1
        for workspace in workspaces.values()
        if (
            workspace.validated_assessment is not None
            and bool(
                workspace.validated_assessment
                .supporting_evidence_ids
            )
        )
    )

    col_1, col_2, col_3, col_4 = st.columns(4)

    col_1.metric(
        "Open exceptions",
        total,
    )

    col_2.metric(
        "Exception patterns",
        len(patterns),
    )

    col_3.metric(
        "Demo cases grounded",
        f"{grounded}/{total}",
    )

    col_4.metric(
        "Autonomous decisions",
        0,
        help=(
            "Every consequential next step remains "
            "behind human authorization."
        ),
    )


def render_case_header(
    workspace: CaseWorkspace,
) -> None:
    case = workspace.case
    finding = workspace.primary_finding

    category = (
        category_label(
            finding.category.value
        )
        if finding is not None
        else "No exception"
    )

    st.markdown(
        '<div class="cr-section-label">'
        "Investigation workspace"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        (
            '<div class="cr-case-heading">'
            f"{escape(case.case_id)} · "
            f"{escape(case.application.applicant.business_name)}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    st.markdown(
        (
            '<div class="cr-case-meta">'
            f"{escape(case.application.application_id)}"
            " · "
            f"{escape(case.application.license_type)}"
            " · "
            f"{escape(category)}"
            " · "
            f"{escape(case.severity.value)} severity"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    render_case_signals(
        workspace
    )

    finding_description = (
        finding.observed_condition
        if finding is not None
        else "No deterministic exception detected."
    )

    st.markdown(
        f"""
        <div class="cr-detection-banner">
            <div class="cr-detection-title">
                {escape(detection_headline(workspace))}
            </div>
            <div class="cr-small">
                {escape(finding_description)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_investigation_tab(
    workspace: CaseWorkspace,
) -> None:
    finding = workspace.primary_finding
    assessment = workspace.validated_assessment

    left, right = st.columns(
        [1.45, 1],
        gap="large",
    )

    with left:
        st.markdown(
            "### Deterministic detection"
        )

        if finding is None:
            st.info(
                "No deterministic exception was detected."
            )
        else:
            st.markdown(
                f"**{finding.title}**"
            )

            st.write(
                finding.observed_condition
            )

            st.caption(
                f"Rule {finding.rule_id} · "
                f"version {finding.rule_version}"
            )

            st.markdown(
                "**What this rule establishes**"
            )

            st.info(
                finding.limitation
            )

        st.markdown(
            "### AI interpretation"
        )

        if assessment is None:
            st.error(
                "No AI assessment passed deterministic validation. "
                "Human investigation is required."
            )

            return

        st.markdown(
            '<span class="cr-confidence">'
            f"{escape(assessment.confidence.value)} confidence"
            "</span>",
            unsafe_allow_html=True,
        )

        st.markdown(
            "**Likely operational explanation**"
        )

        st.write(
            assessment.likely_cause
        )

        if assessment.alternative_hypotheses:
            st.markdown(
                "**Alternative explanation considered**"
            )

            for hypothesis in (
                assessment.alternative_hypotheses
            ):
                st.write(
                    f"- {hypothesis}"
                )

        st.markdown(
            "**Evidence grounding**"
        )

        st.caption(
            "The assessment may cite only evidence IDs present "
            "in the reconstructed case packet."
        )

        st.code(
            "\n".join(
                assessment.supporting_evidence_ids
            ),
            language=None,
        )

    with right:
        st.markdown(
            "### Recommended next step"
        )

        if assessment is None:
            st.error(
                "Escalate for human investigation."
            )

            return

        action = action_label(
            assessment.recommended_action.value
        )

        owner = owner_label(
            assessment.recommended_owner_role.value
        )

        st.markdown(
            f"""
            <div class="cr-action-card">
                <div class="cr-section-label">
                    Bounded recommendation
                </div>
                <div class="cr-action-title">
                    {escape(action)}
                </div>
                <div class="cr-small">
                    Recommended owner · {escape(owner)}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            "**Why this action**"
        )

        st.write(
            assessment.recommended_action_rationale
        )

        st.markdown(
            "**Why confidence is "
            f"{assessment.confidence.value.lower()}**"
        )

        for basis in assessment.confidence_basis:
            st.write(
                f"- {basis}"
            )

        st.markdown(
            """
            <div class="cr-human-gate">
                <strong>Human authorization required</strong><br>
                The model can recommend the next operational step.
                It cannot approve or deny the license, bypass policy,
                change workflow state, or modify payment linkage.
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_evidence_tab(
    workspace: CaseWorkspace,
) -> None:
    st.markdown(
        "### Confirmed facts"
    )

    st.caption(
        "Facts are reconstructed from source records before "
        "AI interpretation begins."
    )

    facts = [
        {
            "Confirmed fact": fact.statement,
            "Source evidence": ", ".join(
                reference.evidence_id
                for reference in fact.evidence
            ),
        }
        for fact in workspace.context.confirmed_facts
    ]

    st.dataframe(
        pd.DataFrame(facts),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown(
        "### Event timeline"
    )

    timeline_rows = [
        {
            "Time": entry.occurred_at.strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            ),
            "System": humanize(
                entry.source_system
            ),
            "Event": humanize(
                entry.event_type
            ),
            "Result": (
                "Succeeded"
                if entry.success
                else "Failed"
            ),
            "What happened": entry.summary,
            "Evidence": entry.evidence_id,
        }
        for entry in workspace.context.timeline
    ]

    st.dataframe(
        pd.DataFrame(timeline_rows),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown(
        "### Evidence explorer"
    )

    selected_evidence_id = st.selectbox(
        "Inspect source record",
        options=[
            item.evidence_id
            for item in workspace.evidence.items
        ],
        key=(
            "evidence_selector_"
            f"{workspace.case.case_id}"
        ),
    )

    selected_item = next(
        item
        for item in workspace.evidence.items
        if item.evidence_id == selected_evidence_id
    )

    col_1, col_2, col_3 = st.columns(3)

    col_1.metric(
        "Source system",
        humanize(
            selected_item.source_system.value
        ),
    )

    col_2.metric(
        "Evidence type",
        humanize(
            selected_item.evidence_type.value
        ),
    )

    col_3.metric(
        "Source record",
        selected_item.source_record_id,
    )

    st.markdown(
        "**Source summary**"
    )

    st.write(
        selected_item.summary
    )

    with st.expander(
        "View captured source fields"
    ):
        st.json(
            selected_item.fields
        )

    st.caption(
        "Synthetic evidence · "
        f"Captured {selected_item.captured_at.isoformat()}"
    )


def render_human_review_tab(
    workspace: CaseWorkspace,
    repository: AuditRepository,
) -> None:
    case = workspace.case
    assessment = workspace.validated_assessment

    st.markdown(
        "### Human decision gate"
    )

    st.write(
        "AI can recommend a bounded operational next step. "
        "A reviewer must explicitly decide whether that "
        "recommendation should move forward."
    )

    if assessment is None:
        st.error(
            "No validated AI recommendation is available. "
            "Continue with human investigation."
        )

        return

    action = action_label(
        assessment.recommended_action.value
    )

    owner = owner_label(
        assessment.recommended_owner_role.value
    )

    st.markdown(
        f"""
        <div class="cr-action-card">
            <div class="cr-section-label">
                Recommendation under review
            </div>
            <div class="cr-action-title">
                {escape(action)}
            </div>
            <div class="cr-small">
                Suggested owner · {escape(owner)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "#### Reviewer decision"
    )

    decision_label = st.selectbox(
        "Decision",
        options=[
            "Select a decision...",
            *REVIEW_OPTIONS.keys(),
        ],
        key=(
            "review_choice_"
            f"{case.case_id}"
        ),
        label_visibility="collapsed",
    )

    notes = st.text_area(
        "Reviewer rationale",
        placeholder=(
            "Record why the recommendation is authorized, "
            "rejected, or requires more evidence."
        ),
        key=(
            "review_notes_"
            f"{case.case_id}"
        ),
    )

    st.markdown(
        """
        <div class="cr-note">
            Recording this decision does not approve or deny a
            license and does not execute an external system change.
            Execution is a separate controlled lifecycle step.
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button(
        "Persist human decision",
        type="primary",
        key=(
            "record_review_"
            f"{case.case_id}"
        ),
    ):
        if decision_label == "Select a decision...":
            st.error(
                "Select a reviewer decision before recording."
            )

        else:
            event = record_human_review_decision(
                repository,
                case_id=case.case_id,
                application_id=(
                    case.application.application_id
                ),
                decision=(
                    REVIEW_OPTIONS[
                        decision_label
                    ]
                ),
                rationale=notes,
                reviewer_id="demo-reviewer",
            )

            st.success(
                "Human decision persisted to the audit ledger. "
                "No external workflow action was executed."
            )

            st.caption(
                "Audit event · "
                f"{event.event_id} · "
                f"hash {short_hash(event.event_hash)}"
            )

    latest_review = (
        get_latest_human_review_event(
            repository,
            case.case_id,
        )
    )

    if latest_review is not None:
        st.markdown(
            "### Latest persisted review"
        )

        review_table = pd.DataFrame(
            [
                {
                    "Decision": review_label(
                        latest_review.payload[
                            "decision"
                        ]
                    ),
                    "Reviewer": (
                        latest_review.actor_id
                        or "Unknown"
                    ),
                    "Rationale": (
                        latest_review.payload.get(
                            "rationale"
                        )
                        or "Not provided"
                    ),
                    "Recorded": (
                        latest_review.occurred_at
                        .strftime(
                            "%Y-%m-%d %H:%M:%S UTC"
                        )
                    ),
                    "External action executed": (
                        "No"
                        if not latest_review.payload.get(
                            "external_action_executed",
                            False,
                        )
                        else "Yes"
                    ),
                }
            ]
        )

        st.dataframe(
            review_table,
            use_container_width=True,
            hide_index=True,
        )

        st.caption(
            f"Ledger position "
            f"{latest_review.chain_position} · "
            f"event hash "
            f"{short_hash(latest_review.event_hash)}"
        )


def find_action_event(
    repository: AuditRepository,
    *,
    case_id: str,
    event_type: AuditEventType,
    idempotency_key: str,
) -> AuditEvent | None:
    events = repository.list_case_events(
        case_id
    )

    for event in reversed(events):
        if (
            event.event_type == event_type
            and event.payload.get(
                "idempotency_key"
            )
            == idempotency_key
        ):
            return event

    return None


def render_controlled_action_tab(
    workspace: CaseWorkspace,
    repository: AuditRepository,
) -> None:
    case = workspace.case
    assessment = workspace.validated_assessment

    st.markdown(
        "### Controlled action"
    )

    st.write(
        "CivicResolve separates authorization from execution. "
        "Only an explicitly authorized bounded operation can reach "
        "this stage."
    )

    if assessment is None:
        st.error(
            "No validated assessment exists for this case."
        )
        return

    try:
        plan = build_authorized_action_plan(
            repository,
            case=case,
            assessment=assessment,
        )

    except ActionNotAuthorizedError:
        latest_review = (
            get_latest_human_review_event(
                repository,
                case.case_id,
            )
        )

        st.markdown(
            """
            <div class="cr-locked">
                <strong>Controlled action is locked</strong><br>
                A persisted human authorization is required before
                CivicResolve can prepare an executable action plan.
            </div>
            """,
            unsafe_allow_html=True,
        )

        if latest_review is None:
            st.info(
                "No human review has been recorded yet. "
                "Open the Human Review tab to make a decision."
            )
        else:
            st.info(
                "The latest human review does not authorize "
                "next-step preparation."
            )

        return

    preview_event = find_action_event(
        repository,
        case_id=case.case_id,
        event_type=(
            AuditEventType.ACTION_PREVIEWED
        ),
        idempotency_key=(
            plan.idempotency_key
        ),
    )

    execution_event = find_action_event(
        repository,
        case_id=case.case_id,
        event_type=(
            AuditEventType.ACTION_EXECUTED
        ),
        idempotency_key=(
            plan.idempotency_key
        ),
    )

    st.markdown(
        """
        <div class="cr-safe-action">
            <strong>Human authorization verified</strong><br>
            CivicResolve may now prepare only the bounded operation
            shown below. Government decision authority remains
            outside the action executor.
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_1, col_2, col_3 = st.columns(3)

    col_1.metric(
        "Operation",
        humanize(
            plan.operation.value
        ),
    )

    col_2.metric(
        "Target",
        plan.target_system,
    )

    col_3.metric(
        "Owner",
        owner_label(
            plan.target_owner_role.value
        ),
    )

    st.markdown(
        "### Action preview"
    )

    st.write(
        plan.summary
    )

    state_rows = [
        {
            "Current state": humanize(key),
            "Value": humanize(value),
        }
        for key, value in (
            plan.current_state.items()
        )
    ]

    st.dataframe(
        pd.DataFrame(state_rows),
        use_container_width=True,
        hide_index=True,
    )

    left, right = st.columns(
        2,
        gap="large",
    )

    with left:
        st.markdown(
            "#### Permitted effects"
        )

        for effect in plan.proposed_effects:
            st.write(
                f"- {effect}"
            )

    with right:
        st.markdown(
            "#### Explicitly prohibited"
        )

        for effect in plan.prohibited_effects:
            st.write(
                f"- {effect}"
            )

    st.markdown(
        """
        <div class="cr-note">
            Demo execution prepares a synthetic work item only.
            It does not call a government system, modify workflow
            state, change payment linkage, or make a licensing
            decision.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption(
        f"Plan {plan.plan_id} · "
        f"idempotency key "
        f"{short_hash(plan.idempotency_key)}"
    )

    if preview_event is None:
        if st.button(
            "Record controlled action preview",
            key=(
                "record_preview_"
                f"{case.case_id}"
            ),
        ):
            preview_event = (
                ensure_action_preview_audit_event(
                    repository,
                    plan,
                )
            )

            st.success(
                "Action preview recorded in the audit ledger. "
                "No action was executed."
            )

            st.caption(
                f"Preview event · "
                f"{preview_event.event_id}"
            )

    else:
        st.success(
            "Action preview is recorded in the audit ledger."
        )

        st.caption(
            f"Ledger position "
            f"{preview_event.chain_position} · "
            f"hash "
            f"{short_hash(preview_event.event_hash)}"
        )

    preview_recorded = (
        preview_event is not None
    )

    st.markdown(
        "### Simulation gate"
    )

    st.write(
        "Simulation is enabled only after the controlled-action "
        "preview has been persisted."
    )

    if st.button(
        "Simulate controlled action",
        type="primary",
        disabled=not preview_recorded,
        key=(
            "simulate_action_"
            f"{case.case_id}"
        ),
    ):
        result = simulate_controlled_action(
            repository,
            plan,
        )

        st.success(
            result.message
        )

        execution_event = find_action_event(
            repository,
            case_id=case.case_id,
            event_type=(
                AuditEventType.ACTION_EXECUTED
            ),
            idempotency_key=(
                plan.idempotency_key
            ),
        )

    if execution_event is not None:
        st.markdown(
            "### Persisted execution result"
        )

        result_1, result_2, result_3 = (
            st.columns(3)
        )

        result_1.metric(
            "Execution",
            "Simulated success",
        )

        result_2.metric(
            "External system changed",
            (
                "Yes"
                if execution_event.payload.get(
                    "external_system_changed",
                    False,
                )
                else "No"
            ),
        )

        result_3.metric(
            "Government decision changed",
            (
                "Yes"
                if execution_event.payload.get(
                    "government_decision_changed",
                    False,
                )
                else "No"
            ),
        )

        st.caption(
            f"Execution event · "
            f"ledger position "
            f"{execution_event.chain_position} · "
            f"hash "
            f"{short_hash(execution_event.event_hash)}"
        )


def render_audit_tab(
    workspace: CaseWorkspace,
    repository: AuditRepository,
) -> None:
    case = workspace.case
    assessment_run = workspace.assessment_run

    first_attempt = (
        assessment_run.attempts[0]
        if assessment_run.attempts
        else None
    )

    events = repository.list_case_events(
        case.case_id
    )

    chain_verified = (
        repository.verify_case_chain(
            case.case_id
        )
    )

    latest_review = (
        get_latest_human_review_event(
            repository,
            case.case_id,
        )
    )

    execution_events = [
        event
        for event in events
        if (
            event.event_type
            == AuditEventType.ACTION_EXECUTED
        )
    ]

    external_mutations = sum(
        1
        for event in execution_events
        if event.payload.get(
            "external_system_changed",
            False,
        )
    )

    st.markdown(
        "### Audit & decision provenance"
    )

    metric_1, metric_2, metric_3, metric_4 = (
        st.columns(4)
    )

    metric_1.metric(
        "Persisted events",
        len(events),
    )

    metric_2.metric(
        "Audit chain",
        (
            "Verified"
            if chain_verified
            else "Failed"
        ),
    )

    metric_3.metric(
        "Human review",
        (
            "Recorded"
            if latest_review is not None
            else "Pending"
        ),
    )

    metric_4.metric(
        "External mutations",
        external_mutations,
    )

    if chain_verified:
        st.markdown(
            """
            <div class="cr-integrity-good">
                <strong>Audit chain integrity verified</strong><br>
                Persisted events are present in append order and
                their hash links validate successfully.
            </div>
            """,
            unsafe_allow_html=True,
        )

    else:
        st.markdown(
            """
            <div class="cr-integrity-bad">
                <strong>Audit chain integrity check failed</strong><br>
                One or more persisted records no longer match the
                expected hash-linked provenance chain.
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <div class="cr-note">
            This is a tamper-evident demo ledger, not a claim of
            physical database immutability. Demo-mode AI uses a
            precomputed open-model assessment for responsive UX,
            while the same deterministic post-model validation
            pipeline is used by live local inference.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "### Persisted event ledger"
    )

    if events:
        event_rows = []

        for event in events:
            event_rows.append(
                {
                    "Position": (
                        event.chain_position
                    ),
                    "Event": humanize(
                        event.event_type.value
                    ),
                    "Actor": humanize(
                        event.actor_type.value
                    ),
                    "Actor ID": (
                        event.actor_id or "—"
                    ),
                    "Occurred": (
                        event.occurred_at.strftime(
                            "%Y-%m-%d %H:%M:%S UTC"
                        )
                    ),
                    "Previous hash": short_hash(
                        event.previous_event_hash
                    ),
                    "Event hash": short_hash(
                        event.event_hash
                    ),
                }
            )

        st.dataframe(
            pd.DataFrame(event_rows),
            use_container_width=True,
            hide_index=True,
        )

    else:
        st.info(
            "No persisted audit events are available."
        )

    st.markdown(
        "### Assessment provenance"
    )

    provenance_rows = [
        {
            "Field": "Case",
            "Value": case.case_id,
        },
        {
            "Field": "Application",
            "Value": (
                case.application.application_id
            ),
        },
        {
            "Field": "Data classification",
            "Value": (
                "Synthetic demonstration data"
            ),
        },
        {
            "Field": "Rules evaluated",
            "Value": str(
                workspace.rule_result
                .evaluated_rule_count
            ),
        },
        {
            "Field": "Rules triggered",
            "Value": str(
                workspace.rule_result
                .triggered_rule_count
            ),
        },
        {
            "Field": "Assessment status",
            "Value": (
                assessment_run.status.value
            ),
        },
        {
            "Field": "Human authorization required",
            "Value": (
                "Yes"
                if assessment_run
                .human_review_required
                else "No"
            ),
        },
    ]

    if first_attempt is not None:
        provenance_rows.extend(
            [
                {
                    "Field": "Assessment source",
                    "Value": (
                        "Precomputed open-model assessment"
                        if first_attempt.inference.provider
                        == "cached"
                        else "Live model inference"
                    ),
                },
                {
                    "Field": "Generation model",
                    "Value": (
                        first_attempt.inference.model_name
                    ),
                },
                {
                    "Field": "Runtime mode",
                    "Value": (
                        "Demo replay"
                        if first_attempt.inference.provider
                        == "cached"
                        else "Live inference"
                    ),
                },
                {
                    "Field": "Prompt version",
                    "Value": (
                        first_attempt.inference
                        .prompt_version
                    ),
                },
                {
                    "Field": "Post-model validation",
                    "Value": (
                        "Passed"
                        if first_attempt.validation.is_valid
                        else "Rejected"
                    ),
                },
            ]
        )

    st.dataframe(
        pd.DataFrame(
            provenance_rows
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown(
        "### Post-model validation"
    )

    if first_attempt is None:
        st.info(
            "No model assessment was recorded."
        )

    elif first_attempt.validation.issues:
        for issue in (
            first_attempt.validation.issues
        ):
            st.write(
                f"**{issue.severity.value}** · "
                f"{issue.code} · "
                f"{issue.message}"
            )

    else:
        st.success(
            "Assessment passed deterministic post-model "
            "validation with no recorded issues."
        )

    if first_attempt is not None:
        with st.expander(
            "Inspect structured model assessment"
        ):
            st.code(
                first_attempt.inference.raw_response,
                language="json",
            )

    if latest_review is not None:
        st.markdown(
            "### Latest human review event"
        )

        st.json(
            {
                "decision": review_label(
                    latest_review.payload[
                        "decision"
                    ]
                ),
                "reviewer": (
                    latest_review.actor_id
                ),
                "rationale": (
                    latest_review.payload.get(
                        "rationale"
                    )
                ),
                "external_action_executed": (
                    latest_review.payload.get(
                        "external_action_executed"
                    )
                ),
                "chain_position": (
                    latest_review.chain_position
                ),
                "event_hash": (
                    latest_review.event_hash
                ),
                "previous_event_hash": (
                    latest_review
                    .previous_event_hash
                ),
            }
        )


workspaces = load_workspaces()

audit_repository = (
    load_audit_repository()
)

for workspace in workspaces.values():
    ensure_ai_assessment_audit_event(
        audit_repository,
        case_id=workspace.case.case_id,
        application_id=(
            workspace.case.application
            .application_id
        ),
        assessment_run=(
            workspace.assessment_run
        ),
    )


st.markdown(
    '<div class="cr-kicker">'
    "Government workflow exception control"
    "</div>",
    unsafe_allow_html=True,
)

st.title(
    "CivicResolve"
)

st.markdown(
    """
    <div class="cr-subtitle">
        Detect workflow exceptions, reconstruct what happened,
        interpret likely causes with evidence-grounded AI, and keep
        consequential government decisions under human control.
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="cr-badges">
        <span class="cr-badge">
            Synthetic demo
        </span>
        <span class="cr-badge">
            No real government or Neumo data
        </span>
        <span class="cr-badge">
            Human-in-the-loop
        </span>
        <span class="cr-badge">
            Validated AI reasoning
        </span>
        <span class="cr-badge">
            Tamper-evident audit
        </span>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="cr-flow">
        <div class="cr-flow-step">
            1 · Detect
        </div>
        <div class="cr-flow-step">
            2 · Reconstruct
        </div>
        <div class="cr-flow-step">
            3 · Recommend
        </div>
        <div class="cr-flow-step">
            4 · Human authorizes
        </div>
        <div class="cr-flow-step">
            5 · Bounded action
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

render_top_metrics(
    workspaces
)

st.caption(
    "Demo coverage across four synthetic exception scenarios."
)

st.divider()

queue_heading, case_selector = st.columns(
    [1.6, 1],
    gap="large",
)

with queue_heading:
    st.markdown(
        "## Exception queue"
    )

    st.caption(
        "Operations staff start with detected exceptions, "
        "not with a chatbot."
    )

with case_selector:
    selected_case_id = st.selectbox(
        "Open investigation",
        options=list(
            workspaces.keys()
        ),
        format_func=lambda case_id: (
            format_case_option(
                case_id,
                workspaces,
            )
        ),
    )

queue_df = build_display_queue(
    workspaces
)

st.dataframe(
    queue_df,
    use_container_width=True,
    hide_index=True,
    height=178,
    column_config={
        "Case": st.column_config.TextColumn(
            width="small"
        ),
        "Organization": st.column_config.TextColumn(
            width="medium"
        ),
        "Pattern": st.column_config.TextColumn(
            width="medium"
        ),
        "Severity": st.column_config.TextColumn(
            width="small"
        ),
        "Stage": st.column_config.TextColumn(
            width="small"
        ),
        "Status": st.column_config.TextColumn(
            width="small"
        ),
        "Recommended next step": (
            st.column_config.TextColumn(
                width="large"
            )
        ),
    },
)

selected_workspace = (
    workspaces[selected_case_id]
)

st.divider()

render_case_header(
    selected_workspace
)

(
    investigation_tab,
    evidence_tab,
    human_review_tab,
    controlled_action_tab,
    audit_tab,
) = st.tabs(
    [
        "Investigation",
        "Evidence & Timeline",
        "Human Review",
        "Controlled Action",
        "Audit & Provenance",
    ]
)

with investigation_tab:
    render_investigation_tab(
        selected_workspace
    )

with evidence_tab:
    render_evidence_tab(
        selected_workspace
    )

with human_review_tab:
    render_human_review_tab(
        selected_workspace,
        audit_repository,
    )

with controlled_action_tab:
    render_controlled_action_tab(
        selected_workspace,
        audit_repository,
    )

with audit_tab:
    render_audit_tab(
        selected_workspace,
        audit_repository,
    )

st.divider()

render_operational_insights_panel()