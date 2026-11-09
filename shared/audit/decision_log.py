"""Append-only, hash-chained JSONL decision log.

Each record gets `seq`, `ts`, `prev_hash` and `hash`, where
`hash = sha256(canonical_json(record_without_hash))` and `prev_hash` is the previous record's
hash (64 zeros for the first). Editing, deleting or reordering any line breaks the chain, which
`verify()` reports with the first bad sequence number.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

GENESIS = "0" * 64


def canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def record_hash(record: dict[str, Any]) -> str:
    body = {k: v for k, v in record.items() if k != "hash"}
    return sha256_text(canonical(body))


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    records: int
    first_bad_seq: int | None = None
    reason: str = ""


class DecisionLog:
    """Hash-chained append-only log. Safe to reopen: the chain continues from the last line."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._seq, self._prev = self._tail()

    def _tail(self) -> tuple[int, str]:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return 0, GENESIS
        last = None
        with self.path.open(encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    last = line
        rec = json.loads(last) if last else None
        if rec is None:
            return 0, GENESIS
        return int(rec["seq"]), str(rec["hash"])

    def append(self, record: dict[str, Any]) -> dict[str, Any]:
        reserved = {"seq", "ts", "prev_hash", "hash"} & record.keys()
        if reserved:
            raise ValueError(f"reserved keys in record: {sorted(reserved)}")
        full = dict(record)
        full["seq"] = self._seq + 1
        full["ts"] = datetime.now(UTC).isoformat()
        full["prev_hash"] = self._prev
        full["hash"] = record_hash(full)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(canonical(full) + "\n")
        self._seq, self._prev = full["seq"], full["hash"]
        return full


def verify(path: str | Path) -> VerifyResult:
    """Walk the chain; report the first record whose hash or link does not match."""
    p = Path(path)
    if not p.exists():
        return VerifyResult(ok=True, records=0)
    prev, expected_seq, n = GENESIS, 1, 0
    with p.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                return VerifyResult(False, n, expected_seq, "unparseable line")
            seq = rec.get("seq")
            if seq != expected_seq:
                return VerifyResult(False, n, expected_seq, f"sequence gap (found {seq})")
            if rec.get("prev_hash") != prev:
                return VerifyResult(False, n, seq, "prev_hash does not link")
            if rec.get("hash") != record_hash(rec):
                return VerifyResult(False, n, seq, "hash mismatch (record edited)")
            prev, expected_seq, n = rec["hash"], expected_seq + 1, n + 1
    return VerifyResult(ok=True, records=n)
