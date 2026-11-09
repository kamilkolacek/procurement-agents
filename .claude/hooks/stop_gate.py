"""Stop hook: run the eval smoke gate; refuse to finish while scores regress.

Exit 2 keeps Claude working and shows it the gate output. `stop_hook_active` prevents loops:
if the gate already blocked once this turn, the second stop is allowed and the failure is
reported to the human instead of looping forever.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import audit, read_event, repo_root  # noqa: E402

AGENT = "spend-classification"


def main() -> None:
    root = repo_root()
    event = read_event()
    if not shutil.which("uv"):
        sys.stderr.write("stop_gate: uv not found, eval gate skipped\n")
        sys.exit(0)
    try:
        res = subprocess.run(
            ["uv", "run", "--quiet", "python", "-m", "shared.evals.harness",
             "--agent", AGENT, "--mode", "smoke"],
            cwd=str(root), capture_output=True, text=True, timeout=240,
        )
        ok, output = res.returncode == 0, (res.stdout + res.stderr)[-3000:]
    except subprocess.TimeoutExpired:
        ok, output = False, "eval smoke gate timed out"
    audit(root, {"hook": "Stop", "decision": "pass" if ok else "regressed"})
    if ok:
        sys.exit(0)
    if event.get("stop_hook_active"):
        sys.stderr.write("Eval gate still failing; stopping so the human can decide.\n" + output)
        sys.exit(0)
    sys.stderr.write("Not done: eval smoke gate failed (scores below target or regressed).\n"
                     "Fix the regression, or explain it to the human. Do not edit golden data "
                     "or the baseline to make it pass.\n\n" + output)
    sys.exit(2)


if __name__ == "__main__":
    main()
