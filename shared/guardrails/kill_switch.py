"""Kill switch: any pipeline run must call `assert_not_killed()` before doing work."""

from __future__ import annotations

import os
from pathlib import Path

ENV_VAR = "PROCUREMENT_AGENTS_KILL"


class KillSwitchEngaged(RuntimeError):
    pass


def kill_switch_engaged(repo_root: str | Path = ".") -> bool:
    if os.environ.get(ENV_VAR, "").strip() not in ("", "0", "false", "False"):
        return True
    return (Path(repo_root) / "KILL").exists()


def assert_not_killed(repo_root: str | Path = ".") -> None:
    if kill_switch_engaged(repo_root):
        raise KillSwitchEngaged(f"kill switch engaged ({ENV_VAR} or KILL file); run refused")
