"""SessionStart hook: put the active agent's STATUS.md and latest eval scores into context."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import audit, read_event, read_overrides, repo_root  # noqa: E402

AGENT = "spend-classification"


def main() -> None:
    root = repo_root()
    read_event()
    agent_dir = root / "agents" / AGENT
    out = []

    status = agent_dir / "STATUS.md"
    if status.exists():
        out.append("=== " + status.relative_to(root).as_posix() + " ===\n" + status.read_text())

    reports = agent_dir / "evals" / "reports"
    for name in ("latest.json", "smoke.json"):
        f = reports / name
        if f.exists():
            try:
                data = json.loads(f.read_text())
                lines = [f"=== latest eval scores ({name}, {data.get('generated_at', '?')}) ==="]
                for m, r in sorted(data.get("metrics", {}).items()):
                    lines.append(f"- {m}: {r.get('value')} "
                                 f"(target {r.get('target')}, {r.get('status')})")
                out.append("\n".join(lines))
            except (OSError, ValueError):
                out.append(f"(could not parse {name})")
            break
    else:
        out.append("=== eval scores: none yet (run `make eval`) ===")

    overrides = read_overrides(root)
    if overrides:
        out.append("WARNING: .claude/OVERRIDE is present; protected edits allowed for: "
                   + ", ".join(o["prefix"] for o in overrides)
                   + ". Remind the human to delete it when done.")

    audit(root, {"hook": "SessionStart", "decision": "context_loaded"})
    print("\n\n".join(out))


if __name__ == "__main__":
    main()
