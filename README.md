# CivicResolve

### Government Workflow Exception Control

**Live demo:** https://civicresolve-7afpdxt2my6phx977hmclj.streamlit.app/

CivicResolve is a working product prototype for investigating and safely resolving exceptions in connected government workflows.

It combines deterministic exception detection, evidence reconstruction, bounded AI interpretation, human authorization, controlled action execution, and audit provenance.

> **Demo scope:** All records, organizations, metrics, and workflow events are synthetic. This project contains no real government, agency, Neumo, customer, or production data.

---

## The Problem

Government workflows often span multiple systems:

- online forms;
- licensing applications;
- payment processors;
- document validation;
- policy requirements;
- approvals;
- ownership queues;
- external integrations.

A workflow can become stuck even when individual systems appear to be working correctly.

For example:

> The payment system shows **SUCCESS**, but the licensing workflow still shows **AWAITING PAYMENT**.

Resolving that exception may require staff to reconstruct events across several systems before they can determine what is safe to do next.

CivicResolve is designed as an **exception-control layer** for that operational gap.

---

## Product Flow

```text
Deterministic detection
        ↓
Evidence reconstruction
        ↓
AI interpretation
        ↓
Deterministic post-model validation
        ↓
Human review
        ↓
Bounded action preview
        ↓
Controlled execution
        ↓
Tamper-evident audit
