# STATUS — Spend Classification & Savings Finder (Agent #2)

**Phase:** 2 — Vendor normalization (built, pending review)
**Autonomy level:** L0 propose-only
**Data:** synthetic only (seed 20261108)
**Last updated:** 2026-11-09

## Done in Phase 2
- Stage 0 `ingest/`: parses AP, PO and P-card exports to one line schema (ISO dates, `Decimal`
  amounts), drops cardholder, buyer, bank and tax-ID fields, removes the 100 exact duplicate AP
  rows, raises on a repeated key with different content, hashes the inputs.
- Stage 1 `vendors/`: cleaning rules, then ERP-ID clusters, then P-card matching. **No LLM calls**
  (the injection filter is a Phase 3 prerequisite, so the LLM step for ambiguous clusters waits).
  - Same ERP ID is one vendor. Two ERP IDs merge only on an explicit "(NEW)"-style marker plus
    near-identical names; otherwise they become a POSSIBLE_DUPLICATE proposal.
  - A card descriptor attaches on an exact key, an adjacent-letter typo, or (only if it hit the
    25-character descriptor cap) a unique prefix. Anything else is AMBIGUOUS_MATCH, kept separate.
  - `python -m spend_classification.run_vendors` writes `outputs/vendor_master_golden.csv` (spend
    in `Decimal`, with row count, query ID, data hash), `vendor_aliases_proposed.csv` (approved_by
    empty) and `vendor_review_queue.csv`, plus a run manifest and hash-chained decision log.
- `vendor_resolution_f1` scorer in `shared/evals/harness.py` (pairwise F1 over the 927 golden
  alias keys; the pipeline never reads the golden files). **Result: 1.0** (target 0.95), 309 vendors
  against 303 golden, 8 review items.
- `tests/test_vendors.py`: cleaning, ingest hygiene, each merge-policy rule, spend reconciliation,
  determinism, scorer. `make check` green (115 tests).

## Caveats
- F1 = 1.0 is on synthetic data whose noise I read while writing the rules (suffix list,
  abbreviations, 25-character cap, "(NEW)" marker). Treat it as proof the rules work on this
  generator, not as a forecast for real exports.
- `related_ids` is empty: parent/subsidiary links cannot be derived from names, so they need a human.
- The "(NEW)" cue is what merges the one duplicate vendor; its two ERP records have different tax
  IDs, so tax ID could not be used as a strong key.

## Needs a human (protected paths, so not done in this session)
- Record `vendor_resolution_f1` in `evals/reports/baseline.json` (baseline updates are human-only).
- ADR for the merge policy in `governance/decisions/` (proposed: ADR 0005, marker-only auto-merge).
- Wire `make run` to `spend_classification.run_vendors` in the Makefile.
- Review `outputs/vendor_aliases_proposed.csv`; approved rows go to `data/labels/vendor_aliases.csv`.
- Verify the UNSPSC crosswalk, or drop it.

## Next: Phase 3 — PII redactor, injection filter, classifier
- Redactor and injection filter before the first LLM call; classifier tiers (cache, embedding, LLM);
  review queue; then the optional LLM pass for ambiguous vendor clusters (via `shared/guardrails`).

## Done in Phase 1 (earlier)
- Taxonomy `taxonomy/taxonomy.yaml` (`2026.1-draft`, **approved by the owner 2026-11-09**): 11 L1, 40 L2 plus
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

## Not yet built
Classifier; PII redactor and injection filter (Phase 3); cube; opportunity engine; brief;
audit-pack builder; reviewer app.

## Notes
- This session ran from the home folder, so the hooks did not enforce anything; protected
  writes were approved in chat (ADR 0004). Open Claude Code at the repo root from now on.
- Owner and approver names in the governance docs are still placeholders.
