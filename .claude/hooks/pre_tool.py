"""PreToolUse hook: path guards, destructive-command guard, dev audit log.

Exit 0 allows the call; exit 2 blocks it and shows the reason to Claude.

- Read/Grep/Glob/Bash: block real data, secrets, and the override token.
- Bash: block `rm -rf`, force-push, `--no-verify`, and shell writes to protected paths.
- Edit/Write/NotebookEdit: writes outside the repo are blocked; protected paths need a human
  override in `.claude/OVERRIDE`; everything else must sit under a writable root.

Shell checks are pattern-based and best-effort. They back up permission prompts, they do not
replace them. Claude's Grep/Glob honour .gitignore, which also hides data/real/.
"""

from __future__ import annotations

import re
import shlex
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import (  # noqa: E402
    any_match,
    audit,
    block,
    load_policy,
    read_event,
    read_overrides,
    rel_to_root,
    repo_root,
    summarize,
)

READ_TOOLS = {"Read", "Grep", "Glob", "NotebookRead"}
WRITE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}

RM_RF = re.compile(
    r"\brm\s+(?:[^|;&]*\s)?(-[a-zA-Z]*[rR][a-zA-Z]*f[a-zA-Z]*|-[a-zA-Z]*f[a-zA-Z]*[rR][a-zA-Z]*"
    r"|--recursive\s+--force|--force\s+--recursive|-r\s+-f|-f\s+-r|-R\s+-f|-f\s+-R)\b"
)
FORCE_PUSH = re.compile(r"\bgit\s+push\b[^|;&]*(\s--force\b|\s-f\b|\s--force-with-lease\b|\s\+\S)")
NO_VERIFY = re.compile(r"\bgit\s+(commit|push)\b[^|;&]*\s(--no-verify|-n\b)")
WRITE_OPS = re.compile(
    r"(>|\btee\b|\bsed\s+-i|\bperl\s+-[a-z]*i|\bmv\b|\bcp\b|\brm\b|\btruncate\b|\bdd\b"
    r"|\bgit\s+(checkout|restore|reset|rm|mv)\b|\bchmod\b|\bln\b|\binstall\b|\bpatch\b)"
)
SECRET_WORDS = re.compile(r"(^|[\s/'\"=])\.env(\.[\w-]+)?($|[\s'\";|&])|\bid_rsa\b|\.aws/|\.ssh/")


def tool_paths(event: Dict[str, Any]) -> List[str]:
    ti = event.get("tool_input") or {}
    paths = []
    for key in ("file_path", "notebook_path", "path"):
        if ti.get(key):
            paths.append(str(ti[key]))
    return paths


def check_read(root: Path, policy: Dict[str, List[str]], event: Dict[str, Any]) -> None:
    ti = event.get("tool_input") or {}
    for p in tool_paths(event):
        rel = rel_to_root(root, p)
        target = rel if rel is not None else Path(p).name
        hit = any_match(target, policy["blocked_always"])
        if hit:
            block(root, event, f"reading '{p}' is not allowed (matches '{hit}'): real data, "
                               "secrets and the override token are off limits.")
    for key in ("glob", "pattern"):
        val = str(ti.get(key) or "")
        if "data/real" in val or ".env" in val:
            block(root, event, f"search pattern '{val}' targets real data or secrets.")


def shell_tokens(command: str) -> List[str]:
    try:
        toks = shlex.split(command, posix=True)
    except ValueError:
        toks = command.split()
    out = []
    for t in toks:
        t = t.lstrip("<>&|;(").rstrip(";|&)")
        if t.startswith(("1>", "2>")):
            t = t[2:].lstrip(">")
        if t:
            out.append(t)
    return out


def check_bash(root: Path, policy: Dict[str, List[str]], event: Dict[str, Any]) -> None:
    cmd = str((event.get("tool_input") or {}).get("command") or "")
    if RM_RF.search(cmd):
        block(root, event, "recursive force delete (rm -rf) is blocked. Delete specific files, "
                           "or ask the human to run it.")
    if FORCE_PUSH.search(cmd):
        block(root, event, "force-push is blocked.")
    if NO_VERIFY.search(cmd):
        block(root, event, "skipping git hooks (--no-verify) is blocked.")
    if "--update-baseline" in cmd:
        block(root, event, "updating the eval baseline is a human decision; "
                           "ask the human to run it.")
    if "OVERRIDE" in cmd and ".claude" in cmd:
        block(root, event, "the override token is for humans only; Claude must not touch it.")
    if "data/real" in cmd or SECRET_WORDS.search(cmd):
        block(root, event, "commands touching real data, .env or credentials are blocked.")

    writes = bool(WRITE_OPS.search(cmd))
    for tok in shell_tokens(cmd):
        if "/" not in tok and "." not in tok:
            continue
        rel = rel_to_root(root, tok)
        if rel is None:
            continue
        hit = any_match(rel, policy["blocked_always"])
        if hit:
            block(root, event, f"'{tok}' matches blocked pattern '{hit}'.")
        if writes:
            hit = any_match(rel, policy["protected_need_override"])
            if hit and not override_for(root, rel):
                block(root, event, f"shell command may modify protected path '{rel}' "
                                   f"(matches '{hit}'). Use Edit/Write with a human override.")


def override_for(root: Path, rel: str) -> Dict[str, str]:
    for ov in read_overrides(root):
        prefix = ov["prefix"]
        if prefix in ("", ".", "*"):
            continue
        if rel == prefix or rel.startswith(prefix + "/"):
            return ov
    return {}


def check_write(root: Path, policy: Dict[str, List[str]], event: Dict[str, Any]) -> None:
    for p in tool_paths(event):
        rel = rel_to_root(root, p)
        if rel is None:
            block(root, event, f"writes outside the repo are blocked ('{p}').")
        hit = any_match(rel, policy["blocked_always"])
        if hit:
            block(root, event, f"'{rel}' can never be written by Claude (matches '{hit}').")
        hit = any_match(rel, policy["protected_need_override"])
        if hit:
            ov = override_for(root, rel)
            if not ov:
                block(root, event, f"'{rel}' is protected (matches '{hit}'). A human must add "
                                   f"'{rel} | <reason>' to .claude/OVERRIDE to allow this edit.")
            audit(root, {"hook": "PreToolUse", "tool": event.get("tool_name"),
                         "decision": "allow_override", "target": rel, "override": ov})
            continue
        if not any_match(rel, policy["writable_roots"]):
            block(root, event, f"'{rel}' is outside the writable roots "
                               f"{policy['writable_roots']}. Ask the human for an override.")


def main() -> None:
    root = repo_root()
    event = read_event()
    policy = load_policy(root)
    tool = event.get("tool_name", "")
    if tool in READ_TOOLS:
        check_read(root, policy, event)
    elif tool == "Bash":
        check_bash(root, policy, event)
    elif tool in WRITE_TOOLS:
        check_write(root, policy, event)
    audit(root, {"hook": "PreToolUse", "tool": tool, "decision": "allow",
                 "target": summarize(event)})
    sys.exit(0)


if __name__ == "__main__":
    main()
