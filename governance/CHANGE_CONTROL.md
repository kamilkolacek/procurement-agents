# Change control

## What needs a PR with eval deltas
| Change | Extra requirement |
|---|---|
| Prompt (`agents/*/prompts/`) | New versioned file; `MANIFEST.json` regenerated; eval report before/after in the PR |
| Taxonomy (`agents/*/taxonomy/`) | Version bump; crosswalk updated; eval report |
| Thresholds (review queue, opportunity rules, targets) | Rationale in PR; eval report |
| Promoted labels / aliases (`data/labels/`) | Rows carry who, when, run ID, reason |
| Golden set (`evals/golden/`) | Human override; second reviewer; reason recorded in an ADR |
| Governance docs, hooks, CI | Human override; ADR if behaviour changes |
| Autonomy level | ADR signed by approver with eval evidence |

## Gate
CI must pass: lint, tests, secret/PII scan, prompt-hash check, eval gate (no metric below
target once measured, and no regression versus `evals/reports/baseline.json`).

## Emergency kill switch
Set `PROCUREMENT_AGENTS_KILL=1` (or create `KILL` in the repo root) and every pipeline run
refuses to start. Implemented with the run manifest in Phase 3.
