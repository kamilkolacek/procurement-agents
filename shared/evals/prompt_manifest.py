"""Prompt manifest: sha256 of every prompt file, checked in CI and recorded in run manifests.

    python -m shared.evals.prompt_manifest --write agents/<agent>/prompts
    python -m shared.evals.prompt_manifest --check agents/<agent>/prompts
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

MANIFEST = "MANIFEST.json"
SKIP = {MANIFEST, "README.md", ".gitkeep"}


def compute(prompts_dir: Path) -> dict[str, str]:
    files = sorted(p for p in prompts_dir.rglob("*") if p.is_file() and p.name not in SKIP)
    return {p.relative_to(prompts_dir).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in files}


def bundle_hash(prompts: dict[str, str]) -> str:
    """Single hash over all prompts, for the run manifest."""
    return hashlib.sha256(json.dumps(prompts, sort_keys=True).encode()).hexdigest()


def write(prompts_dir: Path) -> Path:
    prompts = compute(prompts_dir)
    out = prompts_dir / MANIFEST
    out.write_text(json.dumps({"bundle_hash": bundle_hash(prompts), "prompts": prompts},
                              indent=2, sort_keys=True) + "\n")
    return out


def check(prompts_dir: Path) -> list[str]:
    """Return human-readable problems; empty list means the manifest is current."""
    mf = prompts_dir / MANIFEST
    actual = compute(prompts_dir)
    if not mf.exists():
        return ["MANIFEST.json missing"] if actual else []
    recorded = json.loads(mf.read_text()).get("prompts", {})
    problems = []
    for name in sorted(set(actual) | set(recorded)):
        if name not in recorded:
            problems.append(f"{name}: not in manifest")
        elif name not in actual:
            problems.append(f"{name}: in manifest but file missing")
        elif actual[name] != recorded[name]:
            problems.append(f"{name}: hash changed (edit prompts by adding a new version file)")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", action="store_true")
    g.add_argument("--check", action="store_true")
    ap.add_argument("prompts_dir", type=Path)
    args = ap.parse_args(argv)
    if args.write:
        print(f"wrote {write(args.prompts_dir)}")
        return 0
    problems = check(args.prompts_dir)
    for p in problems:
        print(f"prompt manifest: {p}", file=sys.stderr)
    if not problems:
        print(f"prompt manifest OK ({len(compute(args.prompts_dir))} prompt file(s))")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
