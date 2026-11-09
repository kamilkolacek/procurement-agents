# ADR 0001 — Monorepo for procurement agents

Date: 2026-11-08 · Status: Accepted (plan default)

## Context
The plan calls for shared governance (audit log, guardrails, evals, hooks) across agents.
Agent #1 (invoice-exception) already exists as its own public repo with CI and history.

## Decision
Create `procurement-agents/` as a monorepo. Agent #2 is built here. Agent #1 stays in its own
repo for now; `agents/invoice-exception/` is a pointer only.

## Consequences
- Shared code and hooks are written once.
- Agent #1 does not get the shared harness until a migration is planned (separate ADR).
- CI must scope tests per agent as more agents are added.
