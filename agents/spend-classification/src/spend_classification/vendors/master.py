"""Vendor master and alias-proposal outputs. All arithmetic is deterministic code (Decimal)."""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

from shared.audit.decision_log import sha256_text
from spend_classification.ingest import Line

from .resolve import Resolution

SPEND_QUERY = "SELECT entity_id, SUM(amount), COUNT(*), MIN(date), MAX(date) FROM lines GROUP BY 1"
MASTER_FIELDS = ["golden_id", "canonical_name", "alias_count", "first_seen", "last_seen",
                 "total_spend", "related_ids", "row_count", "query_id", "data_hash"]
ALIAS_FIELDS = ["source", "raw", "erp_vendor_id", "golden_id", "method", "approved_by",
                "approved_at", "run_id", "reason"]
REVIEW_FIELDS = ["reason", "subject", "candidates", "evidence"]


def query_id(input_hash: str) -> str:
    return "vendor_spend_" + sha256_text(SPEND_QUERY + input_hash)[:12]


def _canonical(names: Counter[str]) -> str:
    # most frequent non-REMIT spelling, longest on ties (keeps the legal suffix)
    ok = {n: c for n, c in names.items() if "REMIT" not in n.upper() and "(NEW)" not in n.upper()}
    pool = ok or names
    return max(pool, key=lambda n: (pool[n], len(n), n))


def build_master(lines: list[Line], res: Resolution, input_hash: str) -> list[dict[str, str]]:
    spend: dict[str, Decimal] = defaultdict(Decimal)
    rows: Counter[str] = Counter()
    first: dict[str, str] = {}
    last: dict[str, str] = {}
    names: dict[str, Counter[str]] = defaultdict(Counter)
    for ln in lines:
        v = res.lines_entity[ln.line_key]
        spend[v] += ln.amount
        rows[v] += 1
        first[v] = min(first.get(v, ln.date), ln.date)
        last[v] = max(last.get(v, ln.date), ln.date)
        names[v][ln.vendor_raw] += 1
    qid = query_id(input_hash)
    alias_count = Counter(res.alias_to_entity.values())
    out = []
    for vid in sorted(spend):
        out.append({
            "golden_id": vid, "canonical_name": _canonical(names[vid]),
            "alias_count": str(alias_count[vid]), "first_seen": first[vid],
            "last_seen": last[vid], "total_spend": f"{spend[vid]:.2f}", "related_ids": "",
            "row_count": str(rows[vid]), "query_id": qid, "data_hash": input_hash,
        })
    return out


def build_alias_proposals(res: Resolution, run_id: str) -> list[dict[str, str]]:
    """Every alias is a proposal: approved_by stays empty until a human signs it off."""
    out = []
    for e in res.entities:
        for (source, raw, erp), (method, why) in sorted(e.aliases.items()):
            out.append({"source": source, "raw": raw, "erp_vendor_id": erp,
                        "golden_id": e.entity_id, "method": method, "approved_by": "",
                        "approved_at": "", "run_id": run_id, "reason": why})
    return out


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
