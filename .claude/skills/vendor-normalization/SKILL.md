---
name: vendor-normalization
description: How raw vendor strings are resolved to golden vendor IDs (cleaning rules, fuzzy matching, when the LLM is allowed, alias table format). Load when working on stage 1 or vendor_master_golden.csv.
---

# Vendor normalization (stage 1)

Goal: every raw vendor string -> one golden vendor ID, with an alias table that humans approve.
Target: vendor resolution F1 >= 0.95.

## Order (cheapest and most deterministic first)
1. **Approved aliases**: exact lookup in `data/labels/vendor_aliases.csv`. Done.
2. **Cleaning rules** (pure code): upper-case; strip card-processor noise
   (`SQ *`, `TST*`, `PAYPAL *`, `AMZN Mktp*2K4` -> `AMAZON MARKETPLACE`), store numbers,
   trailing reference codes, punctuation; drop legal suffixes (INC, LLC, LTD, GMBH, CORP, CO).
3. **Strong keys**: same tax ID or remit-to (if present after PII stripping rules allow it) ->
   same vendor.
4. **Fuzzy match** on cleaned names (token-set ratio). Auto-merge only above a high threshold
   set from the golden set; a middle band becomes an *ambiguous cluster*.
5. **LLM only for ambiguous clusters**: give the cluster's cleaned names and nothing else,
   delimited as untrusted input, and ask for a merge/split decision with evidence. The output
   is a *proposal* that goes to review.

## Rules
- Never merge parent/subsidiary or distributor/manufacturer automatically; flag as "related".
- New vendors (no alias, no confident match) trigger the review queue.
- Alias rows carry: raw, golden_id, method (rule|fuzzy|llm|human), approved_by, approved_at,
  run_id, reason.

## Output
`outputs/vendor_master_golden.csv`: golden_id, canonical_name, alias_count, first_seen,
last_seen, total_spend (computed in code), related_ids.
