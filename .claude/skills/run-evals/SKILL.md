---
name: run-evals
description: How to run the eval harness, read the report, add a metric, and handle a regression. Load before running evals, changing targets, or when the Stop hook says the gate failed.
---

# Running evals

```bash
make eval-smoke   # fast gate, the same check the Stop hook runs
make eval         # full run -> evals/reports/latest.json and eval_report.md
```

- Targets: `shared/evals/targets.toml` (direction `min` = higher is better, `max` = lower is better).
- Baseline: `agents/<agent>/evals/reports/baseline.json` (protected). The gate fails when a
  measured metric misses its target, drops versus baseline beyond `tolerance`, or a metric that
  the baseline has stops being measured.
- `not_measured` metrics pass in Phase 0 and are listed as pending.

## Adding a metric
1. Add the target to `targets.toml` (needs override; it is a threshold change).
2. Register a scorer in `shared/evals/harness.py` `SCORERS` that returns a float or `None`.
3. Scorers read `evals/golden/` and run outputs; they never call an LLM.

## When the gate fails
Find which metric moved and why. Do **not** edit golden data, the baseline, or targets to make
it pass. If the change is an intentional trade-off, say so to the human; updating the
baseline is their call (`--update-baseline` with an override).
