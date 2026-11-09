# procurement-agents

Governed AI agents for procurement analytics. The first agent built here, **Spend
Classification & Savings Finder** (Agent #2), turns messy AP, PO and P-card exports into
classified spend, a clean vendor master, and a monthly brief of sized savings opportunities.
Every figure in that brief comes from deterministic code and traces back to a query, and every
label the model is unsure of goes to a human.

> **Status: Phase 1 complete:** harness, draft taxonomy, about 20k lines of seeded synthetic
> spend, and a golden answer key. No pipeline stages are built yet. See
> [`agents/spend-classification/STATUS.md`](agents/spend-classification/STATUS.md).

## Core rule: code computes, the LLM judges
The LLM reads messy text (vendor names, line descriptions) and writes narrative. All arithmetic,
savings sizing, thresholds and rules are code. The agent is read-only and nothing it produces
can move money.

## Pipeline
```
AP + PO + P-card exports (CSV)
        |
 0 Ingest & validate (schema, dedupe, hash input) --> raw/ (never edited)
        |
 1 Vendor normalization: rules + fuzzy match -> LLM only for ambiguous clusters
        |                                   `-> golden vendor ID + alias table
 2 Line classification (tiered, cheapest first):
        a. exact-match cache (human-approved labels)
        b. embedding nearest-neighbor vs. labeled examples
        c. LLM with taxonomy -> label + confidence + evidence
        |       `- low confidence / high-risk category -> REVIEW QUEUE (human)
        |
 3 Category cube (DuckDB/Parquet): vendor x category x BU x month
        |
 4 Opportunity engine (deterministic SQL rules, sized in code)
        |
 5 LLM narrative: writes only from numbers handed to it; each figure carries a query ID
        |
 6 Monthly brief (Draft -> Reviewed -> Published) + audit pack
```

## Quickstart
Requires [uv](https://docs.astral.sh/uv/) (it installs Python 3.12 if needed).
```bash
git clone https://github.com/kamilkolacek/procurement-agents.git
cd procurement-agents
make setup
make check        # lint, tests, secret scan, prompt-hash check, eval gate
```
`make data` regenerates the synthetic exports and answer key (same seed, identical files).
`make run` arrives with the pipeline in Phases 2-5.

## Eval scorecard
| Metric | Target | Current |
|---|---|---|
| Vendor resolution F1 | >= 0.95 | not measured |
| Category accuracy L1 / L2 | >= 95% / >= 90% | not measured |
| Precision in high-confidence bucket | >= 98% | not measured |
| Planted-opportunity recall | >= 90% | not measured |
| Savings sizing error | <= +/-5% | not measured |
| Untraceable or hallucinated figures | 0 | not measured |
| Injection test pass rate | 100% | not measured |

## Governance at a glance
- **Autonomy:** L0, propose-only. See [`governance/AUTONOMY_LEVELS.md`](governance/AUTONOMY_LEVELS.md).
- **Can:** read synthetic exports, classify, size opportunities in code, draft a brief.
- **Cannot:** write to an ERP, send email or messages, approve spend, move money, read real data
  (until [`governance/DATA_POLICY.md`](governance/DATA_POLICY.md) records an approval).
- **Enforced by hooks**, not just instructions: see [`.claude/settings.json`](.claude/settings.json).
- Human review rules: [`HUMAN_IN_THE_LOOP.md`](HUMAN_IN_THE_LOOP.md). Risks:
  [`governance/RISK_REGISTER.md`](governance/RISK_REGISTER.md).

## Repo layout
```
.claude/        hooks, permission rules, skills, reviewer subagents
shared/         audit (hash-chained decision log), guardrails, evals harness
governance/     risk register, autonomy, data policy, model card, change control, ADRs
agents/         spend-classification (Agent #2), invoice-exception (pointer to Agent #1)
scripts/        secret/PII scanner
```

## Limitations and roadmap
Phase 0 is the harness only. Next: synthetic data and golden set (1), vendor normalization (2),
tiered classification and review queue (3), opportunity engine (4), brief, audit pack and
red-team pass (5), shadow run and threshold tuning (6).

## License
MIT — see [`LICENSE`](LICENSE).
