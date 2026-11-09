"""Shared helpers for the Claude Code hooks.

Hooks run under whatever `python3` is on PATH (possibly 3.9), so this file sticks to the
standard library and avoids 3.10+ syntax.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional


def repo_root() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[2]


def read_event() -> Dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def load_policy(root: Path) -> Dict[str, List[str]]:
    policy_file = root / ".claude" / "hooks" / "policy.json"
    if not policy_file.exists():  # fall back to the policy shipped next to this file
        policy_file = Path(__file__).resolve().parent / "policy.json"
    with policy_file.open() as fh:
        return json.load(fh)


def audit(root: Path, record: Dict[str, Any]) -> None:
    """Append one line to logs/dev-audit.jsonl. Never raises: logging must not block work."""
    try:
        log_dir = root / "logs"
        log_dir.mkdir(exist_ok=True)
        record = dict(record)
        record["ts"] = datetime.now(timezone.utc).isoformat()
        with (log_dir / "dev-audit.jsonl").open("a") as fh:
            fh.write(json.dumps(record, sort_keys=True) + "\n")
    except OSError:
        pass


def rel_to_root(root: Path, path_str: str) -> Optional[str]:
    """Repo-relative POSIX path, or None if the path is outside the repo."""
    p = Path(path_str)
    if not p.is_absolute():
        p = root / p
    try:
        resolved = p.resolve()
    except OSError:
        resolved = p
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError:
        return None


def matches(rel: str, pattern: str) -> bool:
    """Match a repo-relative path against a policy pattern.

    - Trailing '/' means "this directory and everything under it".
    - A pattern without '/' matches the basename anywhere in the tree.
    - Otherwise segments are compared one by one with fnmatch-style wildcards.
    """
    from fnmatch import fnmatchcase

    rel = rel.strip("/")
    if "/" not in pattern.rstrip("/") and not pattern.endswith("/"):
        return fnmatchcase(PurePosixPath(rel).name, pattern)
    is_dir = pattern.endswith("/")
    pat_parts = pattern.strip("/").split("/")
    rel_parts = rel.split("/") if rel else []
    if is_dir:
        if len(rel_parts) < len(pat_parts):
            return False
        rel_parts = rel_parts[: len(pat_parts)]
    elif len(rel_parts) != len(pat_parts):
        return False
    return all(fnmatchcase(r, p) for r, p in zip(rel_parts, pat_parts))


def any_match(rel: str, patterns: List[str]) -> Optional[str]:
    for pat in patterns:
        if matches(rel, pat):
            return pat
    return None


def read_overrides(root: Path) -> List[Dict[str, str]]:
    """Parse .claude/OVERRIDE: one `path-prefix | reason` per line.

    Lines without a reason are ignored.
    """
    f = root / ".claude" / "OVERRIDE"
    if not f.exists():
        return []
    out = []
    for line in f.read_text().splitlines():
        if "|" not in line:
            continue
        prefix, reason = (s.strip() for s in line.split("|", 1))
        if prefix and reason:
            out.append({"prefix": prefix.strip("/"), "reason": reason})
    return out


def block(root: Path, event: Dict[str, Any], reason: str) -> None:
    audit(root, {"hook": "PreToolUse", "tool": event.get("tool_name"), "decision": "block",
                 "reason": reason, "target": summarize(event)})
    sys.stderr.write("BLOCKED by procurement-agents policy: " + reason + "\n")
    sys.exit(2)


def summarize(event: Dict[str, Any]) -> str:
    ti = event.get("tool_input") or {}
    for key in ("file_path", "notebook_path", "path", "command", "pattern", "url"):
        if key in ti and ti[key]:
            return str(ti[key])[:300]
    return ""
