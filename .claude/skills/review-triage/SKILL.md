---
name: review-triage
description: Review queue triggers, queue file format, reason codes, and how approved corrections flow back into the label cache. Load when building the review queue, the reviewer tool, or processing reviewer decisions.
---

# Review triage

## Triggers (any one sends a line to `review/review_queue.csv`)
| Code | Rule |
|---|---|
| LOW_CONF | classifier confidence < 0.85 |
| CLOSE_CALL | top-1 minus top-2 confidence < 0.15 |
| HIGH_RISK | L2 category has `risk: high` |
| HIGH_DOLLAR | line amount >= $25,000 (start value) |
| NEW_VENDOR | vendor had no approved alias or confident match |
| QA_SAMPLE | 5% seeded random sample of auto-labelled lines |
| INVALID_OUTPUT | LLM output failed schema/enum validation |
| SUSPECT_INPUT | injection filter flagged the text |

## Queue columns
`item_id, run_id, vendor_golden_id, vendor_raw, description, amount, proposed_l2, confidence,
evidence, triggers, reviewer, decision (accept|correct|reject), corrected_l2, reason_code,
reviewed_at`.

## Reason codes for corrections
`WRONG_L1, WRONG_L2, AMBIGUOUS_DESC, VENDOR_MISRESOLVED, TAXONOMY_GAP, OTHER` (free-text note
required for OTHER and TAXONOMY_GAP).

## After review
- Accepted/corrected labels become proposed rows in `data/labels/approved_labels.csv` with
  who, when, run ID, reason. They are promoted via PR that passes the eval gate.
- Every reviewer action is written to the decision log (`shared.audit.decision_log`).
- QA_SAMPLE error rate is tracked per run; rising error is drift and blocks autonomy promotion.
