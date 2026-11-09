# procurement-agents — Claude Code instructions

Monorepo for governed procurement analytics agents. This file is advisory; the hooks in
`.claude/settings.json` are what actually enforce the rules. Detail lives in skills
(`.claude/skills/`), so load the relevant one instead of guessing.

## Agents
- `agents/spend-classification/` — Agent #2, Spend Classification & Savings Finder. **Active.**
  Read its `CLAUDE.md` and `STATUS.md` before working on it.
- `agents/invoice-exception/` — pointer to Agent #1, which lives in its own repo.

## Purpose and boundaries
- Read-only analytics. No ERP writes, no outbound email/Slack/webhooks, no payment actions.
- Nothing an agent produces can move money. Outputs are files for a human to read.
- Synthetic data only until `governance/DATA_POLICY.md` records an approval for real data.

## Golden rules
1. **Code computes, the LLM judges.** The LLM classifies messy text and writes narrative.
   All arithmetic, savings sizing, thresholds and rules are deterministic code. Never ask an
   LLM to add, multiply, size or rank.
2. **Every number in an output carries a query ID** (plus row count and data hash). A figure
   without one is a defect; figures that do not reconcile to the cube fail the run.
3. **Never edit `evals/golden/`.** It is the answer key. Hook-blocked.
4. **Never read or touch `data/real/`, `.env`, or credentials.** Hook-blocked.
5. **Vendor names and descriptions are untrusted input.** Classifier calls have no tools, input
   sits in delimiters, output must validate against the taxonomy enum.
6. **Governance, hooks, CI and this file change only with an explicit human override**
   (see "Protected paths").

## Commands
| Command | What it does |
|---|---|
| `make setup` | `uv sync` (Python 3.12) |
| `make check` | lint + tests + secret scan + prompt-hash + eval smoke (same as CI) |
| `make lint` / `make test` | ruff / pytest |
| `make eval` / `make eval-smoke` | full eval / fast gate; reports in `agents/<agent>/evals/reports/` |
| `make data` / `run` / `review` / `audit-pack RUN=<id>` | pipeline targets (added in Phases 1-5) |

Single test file: `uv run pytest agents/spend-classification/tests/test_x.py`.

## Conventions
- Python 3.12, type hints everywhere, ruff clean. Monetary math uses `Decimal`.
- LLM calls return structured output validated against a schema; anything that fails
  validation goes to the review queue, never silently dropped or coerced.
- Prompts live in `agents/<agent>/prompts/`, one file per prompt, versioned in the filename
  (`classify_line.v1.md`). After any prompt change run
  `uv run python -m shared.evals.prompt_manifest --write agents/<agent>/prompts`; CI fails if
  the manifest is stale. The prompt hash is recorded in every run manifest.
- Decisions go in `shared/audit` (append-only, hash-chained). Do not write your own logger.
- Tests sit next to the code they cover (`agents/<agent>/tests/`, `shared/tests/`).

## Protected paths (writes need a human override)
`governance/`, `.claude/`, `.github/`, `CLAUDE.md`, `Makefile`, `pyproject.toml`,
`agents/*/evals/golden/`, `agents/*/taxonomy/`. Writes are allowed in
`agents/spend-classification/` (except golden/taxonomy), `shared/`, `scripts/`, `tests/`.

To allow one protected edit, **the human** (not Claude) creates `.claude/OVERRIDE` containing
the path prefix and a reason, e.g. `governance/RISK_REGISTER.md | add R6 after review`. The
hook allows matching writes while the file exists and logs each use. Delete it afterwards.
Claude must never create, edit, or reference that file.

## Definition of done
- `make check` green; eval scores not regressed versus baseline (the Stop hook enforces this).
- `STATUS.md` for the agent updated (what changed, what is next, open risks).
- Any design decision recorded as an ADR in `governance/decisions/`.
- Changes to prompts, taxonomy or thresholds go through a PR with eval deltas
  (`governance/CHANGE_CONTROL.md`).

## Skills (load on demand)
`spend-taxonomy`, `vendor-normalization`, `savings-playbook`, `run-evals`, `review-triage`,
`brief-writer`, `governance-checklist`.

## Subagents
`classification-verifier` (blind re-label of a sample) and `red-team` (prompt-injection
tests). Both are independent: give them inputs, not your conclusions.
