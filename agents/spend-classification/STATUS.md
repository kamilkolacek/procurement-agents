# STATUS — Spend Classification & Savings Finder (Agent #2)

**Phase:** 0 — Harness (complete, pending review)
**Autonomy level:** L0 propose-only
**Data:** synthetic only (none generated yet)
**Last updated:** 2026-11-08

## Done in Phase 0
- Monorepo layout, `pyproject.toml` (uv, Python 3.12), `Makefile`.
- Root and agent `CLAUDE.md`; README; governance docs and ADRs 0001-0003.
- Hooks: path guards (real data, secrets, golden set, protected paths), destructive-command
  guard, post-edit ruff + tests, Stop-time eval gate, SessionStart status loader, dev audit log.
- Skills (7) and subagents (classification-verifier, red-team) as starting playbooks.
- `shared/audit`: hash-chained append-only decision log and run manifest.
- `shared/guardrails`: taxonomy enum validator, untrusted-input delimiter wrapper.
- `shared/evals`: metric targets, eval harness skeleton (all metrics `not_measured`),
  regression gate, prompt manifest check.
- CI: lint, tests, secret/PII scan, prompt-hash check, eval gate.

## Next: Phase 1 — synthetic data and golden set
- Seeded generator (new, not the invoice one): ~20k lines, 18 months, ~300 vendors with messy
  variants, planted opportunities (three-vendor split, 4%/quarter price creep, off-contract).
- Answer key written to `evals/golden/` (needs a human override for the first write).
- Draft `taxonomy/taxonomy.yaml` (~40 two-level categories) for approval.
- `make data` target.

## Not yet built
PII redactor and injection filter (Phase 3, before the first LLM call); cube; opportunity
engine; brief; audit-pack builder; reviewer app.

## Open risks
See `governance/RISK_REGISTER.md`. Owner/approver names in governance docs are placeholders
until filled in by a human.
