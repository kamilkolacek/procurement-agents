# ADR 0002 — Custom two-level taxonomy with UNSPSC crosswalk

Date: 2026-11-08 · Status: Accepted (plan default)

## Decision
Use a custom two-level taxonomy (~10 L1, ~40 L2 categories) stored in
`agents/spend-classification/taxonomy/taxonomy.yaml` with a version string, plus an optional
UNSPSC crosswalk. Each L2 carries a `risk` flag (low/high) that the review queue uses.

## Why
UNSPSC is too deep for analyst reporting and for a reliable LLM enum; a small custom taxonomy
keeps the label set short and stable while the crosswalk preserves interoperability.

## Consequences
Taxonomy is a protected path; changes go through change control with eval deltas. The first
draft is produced in Phase 1 for human approval.
