# Agent #2 — Spend Classification & Savings Finder

Read the root `CLAUDE.md` first; its golden rules apply here. Current state is in `STATUS.md`.

## What it does
AP, PO and P-card exports (CSV) in; classified spend, a golden vendor master, sized savings
opportunities and a monthly brief out. Read-only analytics at autonomy level **L0
(propose-only)**: every output is a draft for a human.

## Pipeline -> code
| Stage | Package | Notes |
|---|---|---|
| 0 Ingest & validate | `src/spend_classification/ingest` | schema check, dedupe, input hash; strip PII and bank fields; `raw/` copy never edited |
| 1 Vendor normalization | `.../vendors` | rules + fuzzy match first; LLM only for ambiguous clusters |
| 2 Classification | `.../classify` | tiers: exact cache -> embedding NN -> LLM; classify unique (vendor, description) pairs |
| 3 Category cube | `.../cube` | DuckDB/Parquet, vendor x category x BU x month |
| 4 Opportunities | `.../opportunities` | deterministic SQL rules, sized in code (skill: `savings-playbook`) |
| 5-6 Brief | `.../brief` | LLM writes only from numbers handed to it, each with a query ID |

## Review queue triggers (Phase 3)
Confidence < 0.85; small gap between top two categories; high-risk or high-dollar category;
new vendor; plus a 5% random QA sample of auto-labelled lines.

## Folders
- `prompts/` versioned prompts + `MANIFEST.json` (hashes). `taxonomy/` protected.
- `data/synthetic/` generator output (committed). `data/labels/` human-approved labels and
  aliases (agent memory: rows carry who, when, run ID, reason). `data/real/` never touched.
- `evals/golden/` protected answer key; `evals/cases/` test cases; `evals/reports/` scores.
- `review/` queue and reviewer tool; `runs/` per-run manifests; `outputs/` deliverables.

## Gated learning
The agent may *propose* new labels, aliases or rules. A human approves; promotion is a PR
that passes the eval gate. Nothing self-modifies.
