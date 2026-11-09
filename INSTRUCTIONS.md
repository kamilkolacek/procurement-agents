# Instructions

## Setup
1. Install [uv](https://docs.astral.sh/uv/).
2. `make setup` creates `.venv` with Python 3.12 and the dev tools (pytest, ruff).
3. `make check` should pass on a fresh clone.

## Key commands
| Command | Purpose |
|---|---|
| `make check` | Everything CI runs |
| `make test`, `make lint` | pytest, ruff |
| `make eval`, `make eval-smoke` | Eval report / fast regression gate |
| `make prompt-hash` | Verify the prompt manifest matches the prompt files |
| `make scan` | Secret and PII scan of tracked files |
| `make data`, `make run`, `make review`, `make audit-pack RUN=<id>` | Pipeline targets (later phases) |

## Working with Claude Code
Open the repo root in Claude Code. The project settings in `.claude/settings.json` activate:
- **SessionStart** prints the agent's `STATUS.md` and latest eval scores.
- **PreToolUse** blocks reads of real data and secrets, destructive shell commands, force-push,
  and writes to protected paths.
- **PostToolUse** runs ruff and the relevant tests after every Python edit.
- **Stop** runs the eval smoke gate and will not let Claude finish while scores regress.
- Every tool call is appended to `logs/dev-audit.jsonl` (gitignored).

### Allowing a protected edit
Protected paths (governance, hooks, CI, golden set, taxonomy) need a human override. In your own
terminal (not through Claude):
```bash
echo "governance/RISK_REGISTER.md | add R8 after review" > .claude/OVERRIDE
```
The first field is a path prefix. Delete the file when the edit is done. Each use is logged.

## Caveats
- Synthetic data only until the data policy records an approval.
- Hooks are a strong guard, not a sandbox: shell-command checks are pattern-based. Use the
  permission prompts too.
- Owner and approver names in `governance/` are placeholders; fill them in before any real use.
