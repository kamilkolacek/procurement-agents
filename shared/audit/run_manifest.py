"""Run manifest: one JSON file per pipeline run recording exactly what produced the outputs."""

from __future__ import annotations

import hashlib
import json
import subprocess
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path


def new_run_id(now: datetime | None = None) -> str:
    now = now or datetime.now(UTC)
    return now.strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]


def git_sha(cwd: str | Path = ".") -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(cwd), capture_output=True, text=True, check=True
        )
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], cwd=str(cwd), capture_output=True, text=True
        ).stdout.strip()
        return out.stdout.strip() + ("-dirty" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def file_sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def inputs_hash(paths: list[str | Path]) -> str:
    """Order-independent hash over several input files (name + content hash)."""
    parts = sorted(f"{Path(p).name}:{file_sha256(p)}" for p in paths)
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()


@dataclass
class RunManifest:
    agent: str
    run_id: str = field(default_factory=new_run_id)
    git_sha: str = "unknown"
    model: str = ""
    prompt_hash: str = ""
    taxonomy_version: str = ""
    input_hash: str = ""
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    finished_at: str = ""
    status: str = "running"  # running | succeeded | failed | killed
    cost_usd: str = "0"  # Decimal as string; never float
    tokens_in: int = 0
    tokens_out: int = 0
    llm_calls: int = 0
    notes: list[str] = field(default_factory=list)

    def finish(self, status: str) -> None:
        self.status = status
        self.finished_at = datetime.now(UTC).isoformat()

    def write(self, runs_dir: str | Path) -> Path:
        out = Path(runs_dir) / self.run_id / "run_manifest.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(asdict(self), indent=2, sort_keys=True) + "\n")
        return out
