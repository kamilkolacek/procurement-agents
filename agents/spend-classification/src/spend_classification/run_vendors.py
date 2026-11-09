"""Run stages 0-1: ingest, resolve vendors, write outputs and the run manifest.

    PYTHONPATH=.:agents/spend-classification/src uv run python -m spend_classification.run_vendors
"""

from __future__ import annotations

import argparse
from pathlib import Path

from shared.audit.decision_log import DecisionLog
from shared.audit.run_manifest import RunManifest, git_sha
from spend_classification.ingest import ingest
from spend_classification.vendors import build_alias_proposals, build_master, resolve
from spend_classification.vendors.master import (
    ALIAS_FIELDS,
    MASTER_FIELDS,
    REVIEW_FIELDS,
    write_csv,
)
from spend_classification.vendors.resolve import load_approved_aliases

AGENT_DIR = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", default=str(AGENT_DIR / "data" / "synthetic"))
    ap.add_argument("--out", default=str(AGENT_DIR / "outputs"))
    args = ap.parse_args(argv)

    manifest = RunManifest(agent="spend-classification", git_sha=git_sha(AGENT_DIR))
    ing = ingest(args.data)
    manifest.input_hash = ing.input_hash
    approved = load_approved_aliases(AGENT_DIR / "data" / "labels" / "vendor_aliases.csv")
    res = resolve(ing.lines, approved)

    out = Path(args.out)
    master = build_master(ing.lines, res, ing.input_hash)
    write_csv(out / "vendor_master_golden.csv", MASTER_FIELDS, master)
    write_csv(out / "vendor_aliases_proposed.csv", ALIAS_FIELDS,
              build_alias_proposals(res, manifest.run_id))
    write_csv(out / "vendor_review_queue.csv", REVIEW_FIELDS,
              [r.__dict__ for r in res.review])

    log = DecisionLog(AGENT_DIR / "runs" / manifest.run_id / "decisions.jsonl")
    log.append({"run_id": manifest.run_id, "stage": "vendors", "decision": "resolved",
                "vendors": len(res.entities), "aliases": len(res.alias_to_entity),
                "review_items": len(res.review), "input_hash": ing.input_hash, "llm_calls": 0})
    manifest.notes.append(f"vendors={len(res.entities)} review_items={len(res.review)}; no LLM")
    manifest.finish("succeeded")
    manifest.write(AGENT_DIR / "runs")
    print(f"run {manifest.run_id}: {len(ing.lines)} lines, {sum(ing.duplicates_removed.values())} "
          f"duplicate rows removed, {len(res.entities)} vendors, {len(res.review)} review items")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
