"""Stage 0: parse the three exports into one normalized, PII-free line schema.

Dates become ISO, amounts become `Decimal`. Cardholder, buyer, bank account and tax ID are
dropped here and never leave this module. Exact duplicate rows are removed (counted in the
report); a repeated line key with different content is a data error and raises.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from shared.audit.run_manifest import inputs_hash

EXPORTS = ("ap_invoices.csv", "po_lines.csv", "pcard_transactions.csv")


@dataclass(frozen=True)
class Line:
    line_key: str
    source: str  # AP | PO | PCARD
    date: str  # ISO yyyy-mm-dd
    amount: Decimal
    currency: str
    vendor_raw: str
    erp_vendor_id: str  # "" for P-card
    description: str
    business_unit: str


@dataclass(frozen=True)
class IngestResult:
    lines: list[Line]
    input_hash: str
    rows_read: dict[str, int]
    duplicates_removed: dict[str, int]


class IngestError(ValueError):
    pass


def _amount(raw: str, where: str) -> Decimal:
    try:
        return Decimal(raw.replace(",", "").strip())
    except Exception as exc:  # decimal.InvalidOperation
        raise IngestError(f"{where}: bad amount {raw!r}") from exc


def _date(raw: str, fmt: str, where: str) -> str:
    try:
        return datetime.strptime(raw.strip(), fmt).date().isoformat()
    except ValueError as exc:
        raise IngestError(f"{where}: bad date {raw!r}") from exc


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _ap(r: dict[str, str]) -> Line:
    key = f"AP|{r['Invoice ID']}|{r['Line']}"
    return Line(key, "AP", _date(r["Invoice Date"], "%m/%d/%Y", key), _amount(r["Amount"], key),
                r["Currency"], r["Supplier Name"].strip(), r["Supplier ID"].strip(),
                r["Line Description"], r["Business Unit"])


def _po(r: dict[str, str]) -> Line:
    key = f"PO|{r['PO Number']}|{r['PO Line']}"
    return Line(key, "PO", _date(r["Order Date"], "%Y-%m-%d", key),
                _amount(r["Extended Amount"], key), "USD", r["Vendor"].strip(),
                r["Vendor No"].strip(), r["Item Description"], r["BU"])


def _pc(r: dict[str, str]) -> Line:
    key = f"PC|{r['Txn ID']}"
    return Line(key, "PCARD", _date(r["Post Date"], "%d-%b-%Y", key), _amount(r["Amount"], key),
                "USD", r["Merchant"].strip(), "", r["Description"], r["Dept"])


_PARSERS = {"ap_invoices.csv": _ap, "po_lines.csv": _po, "pcard_transactions.csv": _pc}


def ingest(data_dir: str | Path) -> IngestResult:
    """Read every export under `data_dir`; return deduplicated lines in file order."""
    data_dir = Path(data_dir)
    lines: list[Line] = []
    seen: dict[str, tuple[dict[str, str], Line]] = {}
    rows_read: dict[str, int] = {}
    dups: dict[str, int] = {}
    for name in EXPORTS:
        rows = _read(data_dir / name)
        rows_read[name] = len(rows)
        dups[name] = 0
        for row in rows:
            line = _PARSERS[name](row)
            prior = seen.get(line.line_key)
            if prior is None:
                seen[line.line_key] = (row, line)
                lines.append(line)
            elif prior[0] == row:
                dups[name] += 1
            else:
                raise IngestError(f"{line.line_key}: repeated key with different content")
    return IngestResult(lines, inputs_hash([data_dir / n for n in EXPORTS]), rows_read, dups)
