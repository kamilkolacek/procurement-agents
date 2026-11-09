---
name: brief-writer
description: Rules and template for the monthly savings brief: the LLM writes narrative only from figures handed to it with query IDs. Load when building stage 5-6 or editing the brief prompt.
---

# Brief writer (stages 5-6)

## Contract
- Input to the LLM: a JSON list of facts `{fact_id, query_id, value, unit, row_count,
  data_hash, label}` plus opportunity records. Nothing else numeric.
- The LLM may only state a number by citing its fact: `$412,300 [F12]`. It may not add,
  subtract, round differently, or compute percentages. Needed derived numbers are computed
  in code and passed in as facts.
- A post-check parses every number in the draft. Any number without a valid `[F..]` tag, or
  whose value differs from the fact, fails the run (target: 0 untraceable figures).

## Template: `outputs/savings_brief_YYYY-MM.md`
```
Status: DRAFT | REVIEWED | PUBLISHED   (set by people, never by the agent at L0)
Run: <run_id> · Data hash: <hash> · Taxonomy: <version> · Prompt: <hash>

1. Headline (3 bullets, largest validated opportunities)
2. Spend overview (classified %, review backlog, top categories)
3. Opportunities (table: type, category, vendors, sized savings, confidence, status)
4. Watch list (price creep, new vendors, data quality)
5. Method and limits (what was not reviewed, low-confidence share)
Appendix: fact table (fact_id -> query_id, row_count, data_hash)
```

## Tone
Plain, specific, no hype. Say "estimated" for unvalidated opportunities. Opportunities above
the sign-off threshold are labelled "pending analyst validation" until signed off.
