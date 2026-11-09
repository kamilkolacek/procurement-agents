# Human-in-the-loop policy

Agents here are decision support. A named human owns every published output.

## Decisions that require human review
| Decision | Trigger | Who |
|---|---|---|
| Line classification | Confidence < 0.85; small gap between top two categories; high-risk or high-dollar category; new vendor | Procurement analyst (review queue) |
| Drift check | 5% random sample of auto-labelled lines | Procurement analyst (QA) |
| Vendor merge | Any LLM-proposed cluster; any fuzzy match below the auto-merge score | Procurement analyst |
| Opportunity validation | Sized savings above the dollar threshold (set in Phase 4) | Category manager sign-off |
| Brief status | Draft -> Reviewed -> Published, each step by a person | Analyst reviews; approver publishes |
| Promoting labels, aliases, rules | Agent proposals | Approver, via PR that passes the eval gate |
| Prompt, taxonomy, threshold changes | Always | Approver, via PR with eval deltas |
| Autonomy level change | Always | Approver, ADR with evidence |

## When to pause or escalate
The run stops and writes a failure record, rather than producing output, when:
- a savings figure does not reconcile to the cube;
- an LLM output fails schema or taxonomy validation more than the allowed rate;
- per-run cost or token caps are hit, or the kill switch is set;
- input fails schema validation or contains fields that should have been stripped.
Suspected prompt injection is quarantined to the review queue and reported to the owner.

## Overrides
- Reviewers can overrule any label, merge or opportunity; each correction records a reason code
  and becomes a cache entry / few-shot example after approval.
- Protected repo paths change only via the `.claude/OVERRIDE` file created by a human.
- Kill switch: `PROCUREMENT_AGENTS_KILL=1` or a `KILL` file at the repo root.

## Accountability
| Role | Person |
|---|---|
| Agent owner | _TBD_ |
| Approver (promotions, autonomy, publishing) | _TBD_ |
| Reviewers | _TBD_ |
All reviewer actions are written to the hash-chained decision log and included in audit packs.
