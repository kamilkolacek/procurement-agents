---
name: governance-checklist
description: Pre-merge and pre-release governance checklist (definition of done, change control, audit, data policy). Load before declaring a phase done, opening a PR, or proposing an autonomy change.
---

# Governance checklist

## Every change
- [ ] `make check` green (lint, tests, scan, prompt-hash, eval smoke).
- [ ] No savings math, ranking or thresholds inside a prompt.
- [ ] Every output number carries query ID, row count, data hash.
- [ ] No reads of `data/real/`, `.env`, credentials; no new outbound channel.
- [ ] Agent `STATUS.md` updated.

## Prompt / taxonomy / threshold change
- [ ] New versioned prompt file; `prompt_manifest --write` run; manifest committed.
- [ ] Eval before/after table in the PR; no metric below target.
- [ ] Change recorded per `governance/CHANGE_CONTROL.md`.

## New design decision
- [ ] ADR in `governance/decisions/NNNN-title.md` (context, decision, consequences).

## Risk
- [ ] Does the change add or alter a risk? Update `governance/RISK_REGISTER.md` (override).

## Phase exit
- [ ] Phase deliverables in `STATUS.md` ticked; next phase listed.
- [ ] Run manifest + decision log produced for any pipeline run in the phase.
- [ ] Audit pack builds (from Phase 5).

## Autonomy promotion
- [ ] Evidence meets the bar in `governance/AUTONOMY_LEVELS.md`.
- [ ] Approver-signed ADR. Never self-promote.
