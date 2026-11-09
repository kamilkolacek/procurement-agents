"""Answer key: ground-truth sizing of planted opportunities, plus generator self-checks.

Sizing follows the `savings-playbook` skill exactly, but runs on *ground truth* (golden vendor
IDs, true categories, deduplicated lines), so a pipeline that misresolves vendors or
misclassifies lines will show sizing error against these numbers. All money is Decimal.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
CONSOLIDATION_RATE = Decimal("0.08")
FRAGMENTATION_TOP_SHARE = Decimal("0.60")


@dataclass(frozen=True)
class TruthLine:
    key: str
    source: str
    date: date
    golden_id: str
    l2: str
    item_code: str
    qty: int
    unit: Decimal
    amount: Decimal
    erp_id: str
    copies: int = 1


@dataclass(frozen=True)
class Window:
    start: date
    end: date
    data_start: date

    def contains(self, d: date) -> bool:
        return self.start <= d <= self.end

    def block(self, d: date) -> int:
        """3-month block index from the first data month (block 0 = first quarter of data)."""
        months = (d.year - self.data_start.year) * 12 + d.month - self.data_start.month
        return months // 3


def q(x: Decimal) -> Decimal:
    return x.quantize(CENT, rounding=ROUND_HALF_UP)


def _wavg(lines: list[TruthLine]) -> Decimal:
    qty = sum(ln.qty for ln in lines)
    return sum((ln.amount for ln in lines), Decimal(0)) / qty


def size_fragmentation(lines: list[TruthLine], l2: str, w: Window) -> tuple[Decimal, int]:
    sel = [ln for ln in lines if ln.l2 == l2 and w.contains(ln.date)]
    by_vendor: dict[str, Decimal] = defaultdict(Decimal)
    for ln in sel:
        by_vendor[ln.golden_id] += ln.amount
    total = sum(by_vendor.values(), Decimal(0))
    top = max(by_vendor.values())
    return q((total - top) * CONSOLIDATION_RATE), len(sel)


def size_price_creep(
    lines: list[TruthLine], gid: str, item: str, w: Window, last_block: int
) -> tuple[Decimal, int]:
    sel = [ln for ln in lines if ln.golden_id == gid and ln.item_code == item]
    baseline = _wavg([ln for ln in sel if w.block(ln.date) == 0])
    current = _wavg([ln for ln in sel if w.block(ln.date) == last_block])
    win = [ln for ln in sel if w.contains(ln.date)]
    return q((current - baseline) * sum(ln.qty for ln in win)), len(win)


def size_price_gap(lines: list[TruthLine], item: str, w: Window) -> tuple[Decimal, int, str]:
    win = [ln for ln in lines if ln.item_code == item and w.contains(ln.date)]
    by_vendor: dict[str, list[TruthLine]] = defaultdict(list)
    for ln in win:
        by_vendor[ln.golden_id].append(ln)
    best_vendor = min(by_vendor, key=lambda g: (_wavg(by_vendor[g]), g))
    best = _wavg(by_vendor[best_vendor])
    extra = sum(
        ((ln.unit - best) * ln.qty for ln in win if ln.golden_id != best_vendor), Decimal(0)
    )
    return q(extra), len(win), best_vendor


def size_off_contract(
    lines: list[TruthLine], item: str, contract_vendor: str, contract_price: Decimal, w: Window
) -> tuple[Decimal, int]:
    win = [ln for ln in lines if ln.item_code == item and w.contains(ln.date)]
    leak = [ln for ln in win if ln.golden_id != contract_vendor or ln.unit > contract_price]
    return q(sum(((ln.unit - contract_price) * ln.qty for ln in leak), Decimal(0))), len(leak)


class SelfCheckError(AssertionError):
    pass


def check_fragmentation_only_where_planted(
    lines: list[TruthLine], planted: set[str], w: Window
) -> dict[str, str]:
    """Every category with >= 3 vendors must have a top share >= 60% unless planted."""
    by_cat: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    for ln in lines:
        if w.contains(ln.date):
            by_cat[ln.l2][ln.golden_id] += ln.amount
    shares = {}
    for l2 in sorted(by_cat):
        spend = by_cat[l2]
        total = sum(spend.values(), Decimal(0))
        top_share = max(spend.values()) / total
        shares[l2] = f"{top_share:.3f}"
        fragmented = len(spend) >= 3 and top_share < FRAGMENTATION_TOP_SHARE
        if fragmented != (l2 in planted):
            raise SelfCheckError(
                f"{l2}: top-vendor share {top_share:.3f} with {len(spend)} vendors; "
                f"planted={l2 in planted}. Background must not look fragmented."
            )
    return shares


def check_items_single_vendor(lines: list[TruthLine], multi_ok: set[str]) -> None:
    vendors: dict[str, set[str]] = defaultdict(set)
    for ln in lines:
        if ln.item_code:
            vendors[ln.item_code].add(ln.golden_id)
    bad = sorted(c for c, vs in vendors.items() if len(vs) > 1 and c not in multi_ok)
    if bad:
        raise SelfCheckError(f"background items bought from several vendors: {bad[:5]}")
