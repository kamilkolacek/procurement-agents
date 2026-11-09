"""PostToolUse hook for Edit/Write: ruff + the touched module's tests, and a change log entry.

Exit 2 feeds the failure back to Claude so it fixes the problem before moving on.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import audit, read_event, rel_to_root, repo_root  # noqa: E402

TIMEOUT = 150


def tests_for(root: Path, rel: str) -> Optional[List[str]]:
    """Pick the narrowest test target for a changed Python file."""
    p = Path(rel)
    if p.name.startswith("test_"):
        return [rel]
    parts = p.parts
    if parts[0] == "agents" and len(parts) > 2:
        tests_dir = root / "agents" / parts[1] / "tests"
        if "spend_classification" in parts:
            idx = parts.index("spend_classification")
            if len(parts) > idx + 2:  # file inside a stage package
                stage = parts[idx + 1]
                hits = sorted(tests_dir.glob(f"test_{stage}*.py"))
                if hits:
                    return [h.relative_to(root).as_posix() for h in hits]
        return [tests_dir.relative_to(root).as_posix()] if tests_dir.exists() else None
    if parts[0] == "shared" and len(parts) > 1:
        hits = sorted((root / "shared" / "tests").glob(f"test_*{p.stem}*.py"))
        target = hits or [root / "shared" / "tests"]
        return [h.relative_to(root).as_posix() for h in target]
    if parts[0] == ".claude":
        return ["tests/hooks"]
    if parts[0] == "scripts":
        return ["tests"]
    return None


def run(cmd: List[str], root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(root), capture_output=True, text=True, timeout=TIMEOUT)


def main() -> None:
    root = repo_root()
    event = read_event()
    ti = event.get("tool_input") or {}
    path = ti.get("file_path") or ti.get("notebook_path") or ""
    rel = rel_to_root(root, path) if path else None
    audit(root, {"hook": "PostToolUse", "tool": event.get("tool_name"), "decision": "changed",
                 "target": rel or path})
    if not rel or not rel.endswith(".py"):
        sys.exit(0)
    if not shutil.which("uv"):
        sys.stderr.write("post_edit: uv not found, skipped ruff/tests\n")
        sys.exit(0)

    problems = []
    lint = run(["uv", "run", "--quiet", "ruff", "check", rel], root)
    if lint.returncode != 0:
        problems.append("ruff:\n" + (lint.stdout + lint.stderr)[-3000:])
    targets = tests_for(root, rel)
    if targets:
        try:
            tst = run(["uv", "run", "--quiet", "pytest", "-q", "-x", *targets], root)
            # exit 5 = no tests collected, which is fine for a new module
            if tst.returncode not in (0, 5):
                problems.append("pytest " + " ".join(targets) + ":\n" + tst.stdout[-3000:])
        except subprocess.TimeoutExpired:
            problems.append(f"pytest timed out after {TIMEOUT}s")
    if problems:
        sys.stderr.write(f"Checks failed after editing {rel}:\n\n" + "\n\n".join(problems))
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
