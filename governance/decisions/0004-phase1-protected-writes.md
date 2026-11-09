# ADR 0004 — Phase 1 approval for writes to protected paths

Date: 2026-11-08 · Status: Accepted · Approved by: repo owner (in the Claude Code chat)

## Context
Phase 1 had to create the first taxonomy and golden answer key and add a `make data` target.
All three paths are protected. The Claude Code session ran from the home folder, not the repo
root, so the project hooks were not loaded and the `.claude/OVERRIDE` mechanism could not be
used.

## Decision
The owner approved these protected writes in chat, scoped to Phase 1:
1. `agents/spend-classification/taxonomy/taxonomy.yaml`: first draft (`2026.1-draft`).
2. `agents/spend-classification/evals/golden/`: initial answer key, written by the generator.
3. `Makefile`: `data` target.
4. This ADR, which records the approval.

No other protected path was changed.

## Consequences
- The taxonomy is still a **draft**. The owner approves it, or asks for changes, before Phase 3
  uses it as the classifier enum. The UNSPSC crosswalk has not been verified.
- Later golden changes come only from re-running the generator, and need
  `golden-change-approved` in the PR body.
- Future sessions should open Claude Code at the repo root, so the hooks enforce the policy
  rather than relying on chat approval.
