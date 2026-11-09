---
name: savings-playbook
description: Opportunity types, detection rules, thresholds and sizing formulas for the deterministic opportunity engine (stage 4). Load before writing or changing any opportunity rule or savings figure.
---

# Savings playbook (stage 4)

All of this is SQL/Python over the category cube. **The LLM never sizes or ranks.** Every
opportunity row carries `query_id`, `row_count`, `data_hash`, and the evidence row IDs.
Thresholds below are starting values; tune them in Phase 6 through change control.

Spend window: trailing 12 months unless stated. Money is `Decimal`, rounded at the end only.

| Type | Detect | Size (annualised) |
|---|---|---|
| **Fragmentation** | One L2 category with >= 3 vendors and the top vendor < 60% of category spend | `(spend not with top vendor) x consolidation_rate` (default 8%) |
| **Price gap (same item, multi-vendor)** | Same normalized item bought from >= 2 vendors, unit-price spread > 10% | `sum over non-best purchases of (unit_price - best_unit_price) x qty` |
| **Off-contract** | Vendor or item has an active contract, but the line was bought from a non-contract vendor or above contract price | `sum of (paid_price - contract_price) x qty`; for non-contract vendor use contract price for the same item |
| **Price creep** | Same vendor + item, unit price rising > 3% per quarter over >= 3 quarters (OLS slope on quarter index) | `(current_price - baseline_price) x trailing_12m_qty`, baseline = first-quarter average |
| **Tail spend** | Vendors that together form the bottom 20% of category spend but > 50% of vendor count | `tail_spend x tail_rate` (default 5%), plus count of vendors to retire |
| **Duplicate / related vendors** | Golden vendors flagged related, or same normalized name with different IDs | Not sized as savings; reported as a data-quality and leverage finding |

## Confidence
`high` when evidence rows >= 10 and the rule margin is at least 2x the threshold; `medium`
otherwise; `low` when any input row is unreviewed low-confidence classification.

## Reconciliation (run fails if it does not hold)
- Sum of category spend in opportunities never exceeds cube category spend.
- Every figure re-computes from its `query_id` to the cent.
- Opportunities do not double count: if a line backs more than one opportunity, the brief
  reports the larger and notes the overlap.

## Planted opportunities in the synthetic data (eval)
Three-vendor split, 4%/quarter price creep, off-contract buying. Recall target >= 90%, sizing
error <= +/-5% against the answer key.
