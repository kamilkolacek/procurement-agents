"""Eval harness and regression gate.

    python -m shared.evals.harness --agent spend-classification --mode smoke|full

Each metric in `targets.toml` has a scorer in `SCORERS` that returns a float, or None while
the stage that produces it is not built. The gate fails (exit 1) when a measured metric misses
its target, regresses versus the baseline beyond its tolerance, or stops being measured while
the baseline has a value. Scorers are deterministic code; they never call an LLM.
"""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
TARGETS_FILE = Path(__file__).with_name("targets.toml")


@dataclass(frozen=True)
class EvalContext:
    agent_dir: Path
    mode: str  # "smoke" or "full"


Scorer = Callable[[EvalContext], float | None]


def _not_built(_: EvalContext) -> float | None:
    return None


# Phase 0: every scorer is a placeholder. Each phase replaces its metrics' scorers.
SCORERS: dict[str, Scorer] = {
    "vendor_resolution_f1": _not_built,
    "category_accuracy_l1": _not_built,
    "category_accuracy_l2": _not_built,
    "high_confidence_precision": _not_built,
    "planted_opportunity_recall": _not_built,
    "savings_sizing_abs_error": _not_built,
    "untraceable_figures": _not_built,
    "injection_pass_rate": _not_built,
}


def load_targets(path: Path = TARGETS_FILE) -> dict[str, dict[str, Any]]:
    with path.open("rb") as fh:
        return tomllib.load(fh)["metrics"]


def _meets(value: float, target: float, direction: str) -> bool:
    return value >= target if direction == "min" else value <= target


def _regressed(value: float, base: float, tol: float, direction: str) -> bool:
    return value < base - tol if direction == "min" else value > base + tol


def gate(
    values: dict[str, float | None],
    targets: dict[str, dict[str, Any]],
    baseline: dict[str, float | None] | None = None,
) -> dict[str, dict[str, Any]]:
    """Pure gate logic: return per-metric result with a status string."""
    baseline = baseline or {}
    out: dict[str, dict[str, Any]] = {}
    for name, spec in targets.items():
        value = values.get(name)
        base = baseline.get(name)
        direction, target, tol = spec["direction"], spec["target"], spec.get("tolerance", 0)
        if value is None:
            status = "missing_vs_baseline" if base is not None else "not_measured"
        elif not _meets(value, target, direction):
            status = "below_target"
        elif base is not None and _regressed(value, base, tol, direction):
            status = "regressed"
        else:
            status = "pass"
        out[name] = {"value": value, "target": target, "direction": direction,
                     "baseline": base, "status": status, "phase": spec.get("phase")}
    return out


FAILING = {"below_target", "regressed", "missing_vs_baseline"}


def render_markdown(agent: str, results: dict[str, dict[str, Any]], generated_at: str) -> str:
    lines = [f"# Eval report — {agent}", "", f"Generated: {generated_at}", "",
             "| Metric | Value | Target | Baseline | Status | Phase |", "|---|---|---|---|---|---|"]
    for name, r in results.items():
        op = ">=" if r["direction"] == "min" else "<="
        val = "—" if r["value"] is None else r["value"]
        base = "—" if r["baseline"] is None else r["baseline"]
        lines.append(f"| {name} | {val} | {op} {r['target']} | {base} "
                     f"| {r['status']} | {r['phase']} |")
    return "\n".join(lines) + "\n"


def golden_integrity(agent_dir: Path) -> list[str]:
    """Compare committed data and golden files with the generator's manifest hashes.

    An edited answer key (or exports changed by hand) fails the gate; regenerate with
    `make data` instead. Returns a list of problems; empty means intact (or no manifest yet).
    """
    import hashlib

    mf = agent_dir / "evals" / "golden" / "answer_key_manifest.json"
    if not mf.exists():
        return []
    problems = []
    for rel, digest in json.loads(mf.read_text()).get("files", {}).items():
        f = agent_dir / rel
        if not f.exists():
            problems.append(f"{rel}: missing")
        elif hashlib.sha256(f.read_bytes()).hexdigest() != digest:
            problems.append(f"{rel}: hash differs from answer_key_manifest.json")
    return problems


def run(agent: str, mode: str, update_baseline: bool = False) -> int:
    agent_dir = REPO_ROOT / "agents" / agent
    if not agent_dir.is_dir():
        print(f"unknown agent: {agent}", file=sys.stderr)
        return 2
    reports = agent_dir / "evals" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    targets = load_targets()
    missing = set(targets) - set(SCORERS)
    if missing:
        print(f"no scorer registered for: {sorted(missing)}", file=sys.stderr)
        return 2

    integrity = golden_integrity(agent_dir)
    for problem in integrity:
        print(f"golden integrity: {problem}", file=sys.stderr)
    if integrity:
        print("EVAL GATE FAILED: golden set or synthetic data does not match its manifest",
              file=sys.stderr)
        return 1

    ctx = EvalContext(agent_dir=agent_dir, mode=mode)
    values = {name: SCORERS[name](ctx) for name in targets}
    baseline_file = reports / "baseline.json"
    baseline = json.loads(baseline_file.read_text())["values"] if baseline_file.exists() else {}
    results = gate(values, targets, baseline)
    generated_at = datetime.now(UTC).isoformat(timespec="seconds")
    payload = {"agent": agent, "mode": mode, "generated_at": generated_at, "metrics": results}

    if mode == "full":
        (reports / "latest.json").write_text(json.dumps(payload, indent=2) + "\n")
        (reports / "eval_report.md").write_text(render_markdown(agent, results, generated_at))
    else:
        (reports / "smoke.json").write_text(json.dumps(payload, indent=2) + "\n")

    failing = {k: v for k, v in results.items() if v["status"] in FAILING}
    for name, r in results.items():
        print(f"{r['status']:>20}  {name} = {r['value']} "
              f"(target {r['target']}, base {r['baseline']})")
    if failing:
        print(f"\nEVAL GATE FAILED: {sorted(failing)}", file=sys.stderr)
        return 1
    if update_baseline:
        baseline_file.write_text(json.dumps(
            {"generated_at": generated_at, "values": values}, indent=2) + "\n")
        print(f"baseline updated: {baseline_file}")
    pending = sum(r["status"] == "not_measured" for r in results.values())
    print(f"\neval gate passed ({pending} metric(s) not measured yet)")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--agent", required=True)
    ap.add_argument("--mode", choices=["smoke", "full"], default="smoke")
    ap.add_argument("--update-baseline", action="store_true",
                    help="human-only: record current values as the new baseline")
    args = ap.parse_args(argv)
    return run(args.agent, args.mode, args.update_baseline)


if __name__ == "__main__":
    sys.exit(main())
