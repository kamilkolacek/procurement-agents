# STATUS — Spend Classification & Savings Finder (Agent #2)

**Phase:** 1 — Synthetic data and golden set (complete, pending review)
**Autonomy level:** L0 propose-only
**Data:** synthetic only (seed 20261108)
**Last updated:** 2026-11-08

## Done in Phase 1
- Draft taxonomy `taxonomy/taxonomy.yaml` (`2026.1-draft`): 11 L1, 40 L2 plus
  `UNCLASSIFIED.REVIEW`; 8 high-risk categories; UNSPSC crosswalk **unverified**.
- Seeded generator `src/spend_classification/synth/` (`make data`), separate from Agent #1's:
  - AP non-PO invoices (10,430 rows), PO lines (4,960) and P-card (4,568); 19,858 unique lines
    over 18 months.
  - 303 vendors with 927 raw name variants: confusable, related, multi-category, tail and
    duplicate-ERP traps.
  - 24 injection lines, about 6% vague descriptions, 100 duplicated AP rows, and PII/bank
    columns for ingest to strip.
  - 14 contracts.
- Golden answer key in `evals/golden/`: vendor master, alias table, line labels, and 8 planted
  opportunities sized in code (see `evals/golden/README.md`).
- Generator self-checks: only planted categories look fragmented; no background price gaps or
  contract leakage; unique keys.
- Eval harness now fails if golden or synthetic files differ from `answer_key_manifest.json`.
- Tests: reproducibility (committed data = generator output), integrity, scale, export and label
  reconciliation, and the planted signals (creep is 4% per quarter, duplicate vendor has 2 IDs).
- ADR 0004 records the owner's chat approval for the protected writes (taxonomy, golden,
  Makefile).

## Decisions waiting on the owner
- **Approve the draft taxonomy** (or request changes) before Phase 3 uses it as the enum.
- Verify the UNSPSC crosswalk, or drop it.

## Next: Phase 2 — vendor normalization
- Ingest stage 0: parse the three exports, normalize dates and amounts, dedupe exact duplicate
  rows, strip PII and bank fields, hash inputs, write a raw copy.
- Stage 1: cleaning rules, then fuzzy match, then LLM only for ambiguous clusters.
- `vendor_master_golden.csv` output and the `vendor_resolution_f1` scorer (target >= 0.95).

## Not yet built
PII redactor and injection filter (Phase 3, before the first LLM call); classifier; cube;
opportunity engine; brief; audit-pack builder; reviewer app.

## Notes
- This session ran from the home folder, so the hooks did not enforce anything; protected
  writes were approved in chat (ADR 0004). Open Claude Code at the repo root from now on.
- Owner and approver names in the governance docs are still placeholders.
