# ADR 0003 — Reviewer interface: CSV plus small Streamlit app

Date: 2026-11-08 · Status: Accepted (plan default)

## Decision
The review queue is `review_queue.csv`. Reviewers can edit it directly or use a small local
Streamlit app (Phase 3). Every correction records a reason code, reviewer, and timestamp.

## Why
CSV keeps the loop auditable and tool-free; Streamlit adds convenience without a new outbound
channel. Slack approvals would add an outbound integration, which the data policy avoids.
