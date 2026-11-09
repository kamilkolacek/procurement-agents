"""Seeded synthetic spend generator (Phase 1).

Produces three messy exports (AP non-PO invoices, PO lines, P-card), a contracts file, and a
golden answer key: vendor master, alias table, true line labels, and planted opportunities
sized in code. Same seed -> byte-identical files.
"""

from __future__ import annotations

import calendar
import csv
import hashlib
import json
import math
import random
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

from shared.guardrails.taxonomy_validator import Taxonomy
from spend_classification.synth import answer_key as ak
from spend_classification.synth.catalog import (
    ABBREVIATIONS,
    CATALOG,
    CITIES,
    INJECTIONS,
    VAGUE_TEMPLATES,
    CategoryProfile,
)
from spend_classification.synth.vendors import Vendor, VendorFactory, person_names

GENERATOR_VERSION = "1.0.0"
DEFAULT_SEED = 20261108
DATA_START = date(2025, 5, 1)
N_MONTHS = 18
AS_OF = date(2026, 10, 31)
WINDOW = ak.Window(start=date(2025, 11, 1), end=AS_OF, data_start=DATA_START)
LAST_BLOCK = (N_MONTHS - 1) // 3
BASE_LINES = 18_600
N_TAIL_VENDORS = 30
N_INJECTIONS = 24
DUPLICATE_INVOICE_RATE = 0.01
VAGUE_RATE = 0.06

BUS = {
    "CORP": ("CC-100", "CC-110", "CC-120"),
    "SALES": ("CC-200", "CC-210"),
    "RND": ("CC-300", "CC-310"),
    "OPS": ("CC-400", "CC-410"),
    "MFG": ("CC-500", "CC-510", "CC-520"),
}
BU_BIAS = {
    "DIR": {"MFG": 0.9, "OPS": 0.1},
    "LOG": {"OPS": 0.6, "MFG": 0.4},
    "MKT": {"SALES": 0.85, "CORP": 0.15},
    "TRV": {"SALES": 0.5, "CORP": 0.2, "RND": 0.3},
    "FAC": {"CORP": 0.6, "OPS": 0.4},
}

# Planted fragmentation: vendor shares for the category (the three-vendor split).
FRAGMENTED = {
    "OFF.SUPPLIES": (0.33, 0.30, 0.27, 0.04, 0.03, 0.03),
    "LOG.COURIER": (0.38, 0.33, 0.29),
}

AP_COLS = [
    "Invoice ID",
    "Line",
    "Invoice Date",
    "Supplier ID",
    "Supplier Name",
    "Line Description",
    "Amount",
    "Currency",
    "Business Unit",
    "Cost Center",
    "Remit Bank Account",
    "Supplier Tax ID",
]
PO_COLS = [
    "PO Number",
    "PO Line",
    "Order Date",
    "Vendor No",
    "Vendor",
    "Item Code",
    "Item Description",
    "Qty",
    "Unit Price",
    "Extended Amount",
    "BU",
    "Cost Ctr",
    "Buyer",
]
PC_COLS = ["Txn ID", "Post Date", "Cardholder", "Merchant", "MCC", "Description", "Amount", "Dept"]


@dataclass
class Line:
    source: str
    vendor: Vendor
    d: date
    l2: str
    description: str
    amount: Decimal
    qty: int = 1
    unit: Decimal = Decimal(0)
    item_code: str = ""
    erp_idx: int = 0
    bu: str = ""
    cc: str = ""
    mcc: str = "5999"
    injection: bool = False
    vague: bool = False
    planted: str = ""
    card_name: str = ""
    key: str = ""
    doc_fields: dict[str, str] = field(default_factory=dict)


def money(x: float | Decimal) -> Decimal:
    return ak.q(Decimal(str(x)))


class Generator:
    def __init__(self, seed: int, taxonomy: Taxonomy) -> None:
        self.seed = seed
        self.rng = random.Random(seed)  # noqa: S311 - seeded synthetic data, not security
        self.tax = taxonomy
        self.vf = VendorFactory(self.rng)
        self.lines: list[Line] = []
        self.by_cat: dict[str, list[Vendor]] = {}
        self.profiles = {p.code: p for p in CATALOG}
        self.contracts: list[dict[str, str]] = []
        self.contracted: set[str] = set()
        self.opportunities: list[dict[str, object]] = []
        self.multi_vendor_items: set[str] = set()
        self._item_seq = 1000
        missing = set(self.profiles) - set(taxonomy.codes)
        if missing:
            raise ValueError(f"catalog codes not in taxonomy: {sorted(missing)}")

    # ------------------------------------------------------------------ helpers
    def new_item_code(self, l2: str) -> str:
        self._item_seq += self.rng.randrange(1, 9)
        return f"{l2.split('.')[0]}-{self._item_seq:05d}"

    def rand_date(self, month_idx: int | None = None) -> date:
        m = self.rng.randrange(N_MONTHS) if month_idx is None else month_idx
        y, mo = (
            DATA_START.year + (DATA_START.month - 1 + m) // 12,
            (DATA_START.month - 1 + m) % 12 + 1,
        )
        return date(y, mo, self.rng.randint(1, calendar.monthrange(y, mo)[1]))

    def fill(self, template: str, d: date, item: str = "") -> str:
        r = self.rng
        return template.format(
            month=f"{calendar.month_abbr[d.month]} {d.year}",
            n=r.randint(2, 40),
            ref=f"{r.randrange(1000, 99999)}",
            item=item,
            city=r.choice(CITIES),
            qtr=f"Q{(d.month - 1) // 3 + 1} {d.year}",
        )

    def service_amount(self, p: CategoryProfile, scale: float = 1.0) -> Decimal:
        return money(max(5.0, self.rng.lognormvariate(math.log(p.median * scale), 0.6)))

    def assign_bu(self, line: Line) -> None:
        bias = BU_BIAS.get(line.l2.split(".")[0])
        if bias:
            bu = self.rng.choices(list(bias), weights=list(bias.values()))[0]
        else:
            bu = self.rng.choice(list(BUS))
        line.bu, line.cc = bu, self.rng.choice(BUS[bu])

    def make_line(
        self,
        v: Vendor,
        l2: str,
        d: date | None = None,
        source: str | None = None,
        scale: float = 1.0,
    ) -> Line:
        p = self.profiles[l2]
        r = self.rng
        d = d or self.rand_date()
        if source is None:
            source = r.choices(("AP", "PO", "PC"), weights=p.sources)[0]
        if source == "PO" and not v.skus:
            source = "AP"
        if source == "PO":
            code = r.choice(list(v.skus))
            name, price = v.skus[code]
            unit = (
                price
                if code in self.contracted
                else money(price * Decimal(str(1 + r.uniform(-0.01, 0.01))))
            )
            target = r.lognormvariate(math.log(p.median), 0.6)
            qty = max(1, round(r.lognormvariate(math.log(max(target / float(unit), 1.0)), 0.4)))
            desc = self.fill(r.choice(p.templates), d, item=name)
            ln = Line("PO", v, d, l2, desc, money(unit * qty), qty, unit, code)
        else:
            item = r.choice(p.items)[0] if p.items else ""
            desc = self.fill(r.choice(p.templates), d, item=item)
            amt = self.service_amount(
                p, scale * (0.25 if source == "PC" and p.median > 1000 else 1)
            )
            ln = Line(source, v, d, l2, desc, amt, 1, amt)
        ln.mcc = p.mcc
        self.assign_bu(ln)
        self.lines.append(ln)
        return ln

    # ------------------------------------------------------------------ vendors
    def build_vendors(self) -> None:
        r = self.rng
        for p in CATALOG:
            n = len(FRAGMENTED[p.code]) if p.code in FRAGMENTED else p.n_vendors
            vs = [self.vf.add(p.code) for _ in range(n)]
            for v in vs:
                for item_name, lo, hi in r.sample(p.items, min(len(p.items), r.randint(2, 4))):
                    price = (
                        money(r.uniform(lo, hi)) if hi >= 1 else Decimal(f"{r.uniform(lo, hi):.2f}")
                    )
                    v.skus[self.new_item_code(p.code)] = (item_name, max(price, Decimal("0.01")))
            self.by_cat[p.code] = vs

        # 12 background contracts, bought fully on contract (must not be flagged).
        goods = [(v, c) for code in self.by_cat for v in self.by_cat[code] for c in v.skus]
        for v, code in r.sample(goods, 12):
            self.add_contract(v, code, v.skus[code][1])

    def add_contract(self, v: Vendor, item_code: str, price: Decimal) -> str:
        cid = f"CT-{len(self.contracts) + 1:04d}"
        self.contracts.append(
            {
                "contract_id": cid,
                "supplier_id": v.erp_ids[0],
                "item_code": item_code,
                "contract_price": f"{price:.2f}",
                "start_date": DATA_START.isoformat(),
                "end_date": "2027-04-30",
            }
        )
        self.contracted.add(item_code)
        return cid

    def shares(self, l2: str) -> list[float]:
        n = len(self.by_cat[l2])
        if l2 in FRAGMENTED:
            return list(FRAGMENTED[l2])
        if n == 1:
            return [1.0]
        dom = self.rng.uniform(0.72, 0.82)
        tail = [1 / (i + 1) for i in range(n - 1)]
        s = sum(tail)
        return [dom] + [(1 - dom) * t / s for t in tail]

    # ------------------------------------------------------------------ spend
    def background(self) -> None:
        total_w = sum(p.weight for p in CATALOG)
        for p in CATALOG:
            vs, w = self.by_cat[p.code], self.shares(p.code)
            for _ in range(round(p.weight / total_w * BASE_LINES)):
                self.make_line(self.rng.choices(vs, weights=w)[0], p.code)

    def specials(self) -> None:
        r = self.rng
        amazon = self.vf.add(
            "OFF.SUPPLIES", kind="multi", name=("Amazon Marketplace", ""), n_erp_names=1
        )
        amazon.erp_names = ["Amazon Marketplace", "AMAZON.COM SERVICES", "Amazon Business"]
        amazon.card_names = []  # generated per transaction
        mix = {"OFF.SUPPLIES": 0.4, "IT.HARDWARE": 0.25, "OFF.KITCHEN": 0.2, "MKT.EVENTS": 0.15}
        for i in range(150):
            l2 = r.choices(list(mix), weights=list(mix.values()))[0]
            ln = self.make_line(amazon, l2, source="PC" if i % 5 else "AP", scale=0.3)
            if ln.source == "PC":
                code = "".join(r.choice("ABCDEFGHJKLMNPQRSTUVWXYZ0123456789") for _ in range(9))
                ln.card_name = r.choice(("AMZN Mktp US*", "Amazon.com*", "AMZN MKTP US*")) + code

        metro = self.vf.add(
            "OFF.SUPPLIES", kind="multi", name=("Metro Office & Tech Supply Co", "Co")
        )
        mix = {"OFF.SUPPLIES": 0.5, "IT.HARDWARE": 0.3, "OFF.FURNITURE": 0.2}
        for _ in range(80):
            self.make_line(metro, r.choices(list(mix), weights=list(mix.values()))[0], source="AP")

        service_cats = [
            p.code
            for p in CATALOG
            if not p.items and p.code not in ("FAC.RENT", "FIN.INSURANCE", "HR.BENEFITS")
        ]
        for _ in range(N_TAIL_VENDORS):
            l2 = r.choice(service_cats)
            v = self.vf.add(l2, kind="tail")
            for _ in range(r.randint(1, 4)):
                self.make_line(v, l2, scale=0.4)

        for l2 in ("FAC.CLEAN", "LOG.FREIGHT", "IT.SERVICES", "PROF.CONSULT"):
            twin = self.vf.confusable_of(self.by_cat[l2][1])
            for _ in range(r.randint(10, 25)):
                self.make_line(twin, l2)

        for parent_l2, child_l2, word in (
            ("LOG.FREIGHT", "LOG.WAREHOUSE", "Distribution"),
            ("IT.SERVICES", "IT.SECURITY", "Cyber"),
            ("PROF.CONSULT", "PROF.RECRUIT", "Talent"),
            ("FAC.MAINT", "FAC.SECURITY", "Protection"),
        ):
            child = self.vf.related_of(self.by_cat[parent_l2][0], child_l2, word)
            for _ in range(r.randint(15, 30)):
                self.make_line(child, child_l2)

    # ------------------------------------------------------------------ planted
    def _po_series(
        self,
        opp: str,
        l2: str,
        item_code: str,
        item_name: str,
        per_month: int,
        qty_range: tuple[int, int],
        pick,
    ) -> int:
        """Monthly PO lines; `pick(month_idx)` returns (vendor, unit_price)."""
        n = 0
        for m in range(N_MONTHS):
            for _ in range(per_month):
                v, unit = pick(m)
                qty = self.rng.randint(*qty_range)
                d = self.rand_date(m)
                ln = Line(
                    "PO", v, d, l2, item_name, money(unit * qty), qty, unit, item_code, planted=opp
                )
                self.assign_bu(ln)
                self.lines.append(ln)
                n += 1
        return n

    def plant(self) -> None:
        r = self.rng
        opp = self.opportunities

        for l2 in FRAGMENTED:
            opp.append(
                {
                    "id": f"FRAG-{l2}",
                    "type": "fragmentation",
                    "l2": l2,
                    "golden_vendor_ids": [v.golden_id for v in self.by_cat[l2][:3]],
                }
            )

        for oid, l2, name, base, per, qr in (
            ("CREEP-1", "IT.HARDWARE", "USB-C dock pro 12-port", "182.00", 9, (4, 18)),
            ("CREEP-2", "DIR.COMPONENTS", "Sensor module SM-40", "41.50", 10, (40, 160)),
        ):
            v = self.by_cat[l2][0]
            code = self.new_item_code(l2)
            v.skus[code] = (name, Decimal(base))
            prices = [money(Decimal(base) * Decimal("1.04") ** b) for b in range(LAST_BLOCK + 1)]
            self._po_series(
                oid, l2, code, name, per, qr, lambda m, v=v, prices=prices: (v, prices[m // 3])
            )
            opp.append(
                {
                    "id": oid,
                    "type": "price_creep",
                    "l2": l2,
                    "item_code": code,
                    "golden_vendor_ids": [v.golden_id],
                    "planted_rate": "4% per quarter",
                }
            )

        a, b = self.by_cat["DIR.MRO"][0], self.by_cat["DIR.MRO"][1]
        code = self.new_item_code("DIR.MRO")
        self.multi_vendor_items.add(code)
        self._po_series(
            "PRICEGAP-1",
            "DIR.MRO",
            code,
            "Nitrile gloves L box 100",
            8,
            (20, 60),
            lambda m: (a, Decimal("8.40")) if r.random() < 0.55 else (b, Decimal("9.95")),
        )
        opp.append(
            {
                "id": "PRICEGAP-1",
                "type": "price_gap",
                "l2": "DIR.MRO",
                "item_code": code,
                "golden_vendor_ids": [a.golden_id, b.golden_id],
            }
        )

        cv, other = self.by_cat["DIR.COMPONENTS"][1], self.by_cat["DIR.COMPONENTS"][2]
        code = self.new_item_code("DIR.COMPONENTS")
        cv.skus[code] = ("Bearing 6204-2RS", Decimal("3.10"))
        cid = self.add_contract(cv, code, Decimal("3.10"))
        self.multi_vendor_items.add(code)
        self._po_series(
            "OFFCON-1",
            "DIR.COMPONENTS",
            code,
            "Bearing 6204-2RS",
            10,
            (200, 800),
            lambda m: (cv, Decimal("3.10")) if r.random() < 0.78 else (other, Decimal("3.62")),
        )
        opp.append(
            {
                "id": "OFFCON-1",
                "type": "off_contract",
                "l2": "DIR.COMPONENTS",
                "item_code": code,
                "contract_id": cid,
                "contract_price": "3.10",
                "golden_vendor_ids": [cv.golden_id, other.golden_id],
                "also_matches": ["price_gap"],
                "notes": "Non-contract vendor at a higher price; also a same-item price gap. "
                "Report once (larger figure) per the playbook overlap rule.",
            }
        )

        pv = self.by_cat["LOG.PACKAGING"][0]
        code = self.new_item_code("LOG.PACKAGING")
        pv.skus[code] = ("Corrugated box 24x18x12", Decimal("2.45"))
        cid = self.add_contract(pv, code, Decimal("2.45"))
        self.contracted.discard(code)  # its price deliberately drifts above contract
        self._po_series(
            "OFFCON-2",
            "LOG.PACKAGING",
            code,
            "Corrugated box 24x18x12",
            8,
            (300, 1500),
            lambda m: (pv, Decimal("2.45") if r.random() < 0.72 else Decimal("2.69")),
        )
        opp.append(
            {
                "id": "OFFCON-2",
                "type": "off_contract",
                "l2": "LOG.PACKAGING",
                "item_code": code,
                "contract_id": cid,
                "contract_price": "2.45",
                "golden_vendor_ids": [pv.golden_id],
                "notes": "Contract vendor billing above contract price.",
            }
        )

        dv = self.by_cat["FAC.CLEAN"][0]
        dv.erp_ids.append(self.vf.new_erp_id())
        alt = dv.canonical.upper()
        for x, y in (("SERVICES", "SVCS"), ("CLEANING", "CLNG"), ("JANITORIAL", "JANITORL")):
            alt = alt.replace(x, y)
        dv.alt_erp_names = [alt, alt + " (NEW)"]
        for ln in self.lines:
            if ln.vendor is dv and ln.source == "AP" and r.random() < 0.4:
                ln.erp_idx = 1
        opp.append(
            {
                "id": "DUP-1",
                "type": "duplicate_vendor",
                "l2": "FAC.CLEAN",
                "golden_vendor_ids": [dv.golden_id],
                "erp_vendor_ids": list(dv.erp_ids),
                "notes": "Same supplier under two ERP IDs; not sized as savings.",
            }
        )

    def enforce_dominance(self, floor: float = 0.66) -> None:
        """Small categories can drift below the fragmentation line by chance. Top up the
        leading vendor (in-window lines) so only planted categories look fragmented."""
        first_window_month = (
            (WINDOW.start.year - DATA_START.year) * 12 + WINDOW.start.month - DATA_START.month
        )
        for p in CATALOG:
            if p.code in FRAGMENTED:
                continue
            for _ in range(500):
                spend: dict[str, Decimal] = defaultdict(Decimal)
                owner: dict[str, Vendor] = {}
                for ln in self.lines:
                    if ln.l2 == p.code and WINDOW.contains(ln.d):
                        spend[ln.vendor.golden_id] += ln.amount
                        owner[ln.vendor.golden_id] = ln.vendor
                total = sum(spend.values(), Decimal(0))
                top = max(spend, key=lambda g: (spend[g], g))
                if len(spend) < 3 or spend[top] / total >= Decimal(str(floor)):
                    break
                m = self.rng.randrange(first_window_month, N_MONTHS)
                self.make_line(owner[top], p.code, d=self.rand_date(m))

    # ------------------------------------------------------------------ messiness
    def mess_up(self) -> None:
        r = self.rng
        candidates = [ln for ln in self.lines if not ln.planted and ln.source in ("AP", "PC")]
        for ln in r.sample(candidates, N_INJECTIONS):
            ln.description = f"{ln.description} -- {r.choice(INJECTIONS)}"
            ln.injection = True
        for ln in self.lines:
            if ln.injection or ln.planted:
                continue
            if ln.source == "AP" and not ln.item_code and r.random() < VAGUE_RATE:
                ln.description = self.fill(r.choice(VAGUE_TEMPLATES), ln.d)
                ln.vague = True
            elif r.random() < 0.08:
                for a, b in ABBREVIATIONS:
                    ln.description = ln.description.replace(a, b)
            elif r.random() < 0.03 and len(ln.description) > 8:
                i = r.randrange(1, len(ln.description) - 2)
                s = ln.description
                ln.description = s[:i] + s[i + 1] + s[i] + s[i + 2 :]

    # ------------------------------------------------------------------ documents
    def build_documents(self) -> tuple[list[dict], list[dict], list[dict]]:
        r = self.rng
        self.lines.sort(key=lambda ln: (ln.d, ln.source, ln.vendor.golden_id, ln.description))
        cardholders = person_names(r, 60)
        buyers = person_names(r, 8)
        bank = {}
        tin = {}
        ap_rows, po_rows, pc_rows = [], [], []

        groups: dict[tuple, list[Line]] = defaultdict(list)
        for ln in self.lines:
            if ln.source in ("AP", "PO"):
                erp = ln.vendor.erp_ids[ln.erp_idx]
                groups[(ln.source, erp, ln.d.year, ln.d.month)].append(ln)
        inv_no, po_no, txn_no = (
            r.randrange(100000, 200000),
            r.randrange(400000, 500000),
            r.randrange(10_000_000, 20_000_000),
        )
        for (source, erp, _, _), lns in groups.items():
            i = 0
            while i < len(lns):
                size = r.choice((1, 1, 1, 2, 2, 3)) if source == "AP" else r.randint(1, 5)
                chunk, i = lns[i : i + size], i + size
                head = chunk[0]
                names = head.vendor.erp_names if head.erp_idx == 0 else head.vendor.alt_erp_names
                name = names[0] if r.random() < 0.7 or len(names) == 1 else r.choice(names[1:])
                if source == "AP":
                    inv_no += r.randrange(1, 7)
                    doc = f"INV-{inv_no:06d}"
                    bank.setdefault(erp, f"TESTACCT{r.randrange(10**7, 10**8)}")
                    tin.setdefault(erp, f"TESTTIN{r.randrange(10**6, 10**7)}")
                    copies = 2 if r.random() < DUPLICATE_INVOICE_RATE else 1
                    for n, ln in enumerate(chunk, 1):
                        ln.d, ln.bu, ln.cc = head.d, head.bu, head.cc
                        ln.key = f"AP|{doc}|{n}"
                        row = {
                            "Invoice ID": doc,
                            "Line": n,
                            "Invoice Date": ln.d.strftime("%m/%d/%Y"),
                            "Supplier ID": erp,
                            "Supplier Name": name,
                            "Line Description": ln.description,
                            "Amount": f"{ln.amount:.2f}",
                            "Currency": "USD",
                            "Business Unit": ln.bu,
                            "Cost Center": ln.cc,
                            "Remit Bank Account": bank[erp] if r.random() < 0.85 else "",
                            "Supplier Tax ID": tin[erp] if r.random() < 0.6 else "",
                        }
                        ln.doc_fields = {"copies": str(copies), "erp": erp, "name": name}
                        ap_rows.extend([row] * copies)
                else:
                    po_no += r.randrange(1, 5)
                    doc = f"PO-{po_no:06d}"
                    buyer = r.choice(buyers)
                    for n, ln in enumerate(chunk, 1):
                        ln.d, ln.bu, ln.cc = head.d, head.bu, head.cc
                        ln.key = f"PO|{doc}|{n}"
                        name_desc = ln.vendor.skus.get(ln.item_code, (ln.description,))[0]
                        po_rows.append(
                            {
                                "PO Number": doc,
                                "PO Line": n,
                                "Order Date": ln.d.isoformat(),
                                "Vendor No": erp,
                                "Vendor": name,
                                "Item Code": ln.item_code,
                                "Item Description": ln.description
                                if ln.planted
                                else name_desc
                                if r.random() < 0.5
                                else ln.description,
                                "Qty": ln.qty,
                                "Unit Price": f"{ln.unit:.2f}",
                                "Extended Amount": f"{ln.amount:.2f}",
                                "BU": ln.bu,
                                "Cost Ctr": ln.cc,
                                "Buyer": buyer,
                            }
                        )
                        ln.doc_fields = {"copies": "1", "erp": erp, "name": name}

        for ln in self.lines:
            if ln.source != "PC":
                continue
            txn_no += r.randrange(1, 50)
            ln.key = f"PC|PCT{txn_no}"
            merchant = ln.card_name or r.choice(ln.vendor.card_names)
            pc_rows.append(
                {
                    "Txn ID": f"PCT{txn_no}",
                    "Post Date": ln.d.strftime("%d-%b-%Y"),
                    "Cardholder": r.choice(cardholders),
                    "Merchant": merchant,
                    "MCC": ln.mcc,
                    "Description": ln.description,
                    "Amount": f"{ln.amount:.2f}",
                    "Dept": ln.bu,
                }
            )
            ln.doc_fields = {"copies": "1", "erp": "", "name": merchant}
        return ap_rows, po_rows, pc_rows

    # ------------------------------------------------------------------ answer key
    def truth(self) -> list[ak.TruthLine]:
        return [
            ak.TruthLine(
                ln.key,
                ln.source,
                ln.d,
                ln.vendor.golden_id,
                ln.l2,
                ln.item_code,
                ln.qty,
                ln.unit,
                ln.amount,
                ln.doc_fields["erp"],
                int(ln.doc_fields["copies"]),
            )
            for ln in self.lines
        ]

    def size_opportunities(self, truth: list[ak.TruthLine]) -> None:
        for o in self.opportunities:
            t = o["type"]
            if t == "fragmentation":
                val, n = ak.size_fragmentation(truth, o["l2"], WINDOW)
                formula = "(category spend - top vendor spend) x 0.08, trailing 12 months"
            elif t == "price_creep":
                val, n = ak.size_price_creep(
                    truth, o["golden_vendor_ids"][0], o["item_code"], WINDOW, LAST_BLOCK
                )
                formula = (
                    "(last-block qty-weighted unit price - block-0 qty-weighted unit "
                    "price) x trailing-12-month qty; blocks are 3-month periods from "
                    f"{DATA_START.isoformat()}"
                )
            elif t == "price_gap":
                val, n, _ = ak.size_price_gap(truth, o["item_code"], WINDOW)
                formula = (
                    "sum over non-best-vendor lines of (unit price - best vendor "
                    "qty-weighted unit price) x qty, trailing 12 months"
                )
            elif t == "off_contract":
                vid = o["golden_vendor_ids"][0]
                val, n = ak.size_off_contract(
                    truth, o["item_code"], vid, Decimal(o["contract_price"]), WINDOW
                )
                formula = (
                    "sum over lines from a non-contract vendor or above contract price "
                    "of (unit price - contract price) x qty, trailing 12 months"
                )
            else:
                o["expected_savings"] = None
                o["evidence_lines"] = sum(1 for x in truth if x.golden_id in o["golden_vendor_ids"])
                continue
            o["expected_savings"] = f"{val:.2f}"
            o["evidence_lines"] = n
            o["sizing"] = formula

    def self_check(self, truth: list[ak.TruthLine]) -> dict[str, str]:
        shares = ak.check_fragmentation_only_where_planted(truth, set(FRAGMENTED), WINDOW)
        ak.check_items_single_vendor(truth, self.multi_vendor_items)
        for ln in self.lines:
            if ln.item_code in self.contracted and not ln.planted:
                price = next(c for c in self.contracts if c["item_code"] == ln.item_code)
                if f"{ln.unit:.2f}" != price["contract_price"]:
                    raise ak.SelfCheckError(f"background contract leak on {ln.item_code}")
        keys = [ln.key for ln in self.lines]
        if len(keys) != len(set(keys)) or "" in keys:
            raise ak.SelfCheckError("line keys are not unique")
        return shares

    # ------------------------------------------------------------------ run
    def run(self) -> dict[str, object]:
        self.build_vendors()
        self.background()
        self.specials()
        self.plant()
        self.enforce_dominance()
        self.mess_up()
        ap, po, pc = self.build_documents()
        truth = self.truth()
        shares = self.self_check(truth)
        self.size_opportunities(truth)
        return {"ap": ap, "po": po, "pc": pc, "truth": truth, "shares": shares}


# ---------------------------------------------------------------------- writing
def _write_csv(path: Path, cols: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate(
    agent_dir: Path,
    seed: int = DEFAULT_SEED,
    out_dir: Path | None = None,
    golden_dir: Path | None = None,
) -> dict[str, object]:
    """Generate everything. `out_dir`/`golden_dir` default to the agent's committed folders."""
    tax = Taxonomy.from_yaml(agent_dir / "taxonomy" / "taxonomy.yaml")
    out = out_dir or agent_dir / "data" / "synthetic"
    gold = golden_dir or agent_dir / "evals" / "golden"
    g = Generator(seed, tax)
    res = g.run()

    _write_csv(out / "ap_invoices.csv", AP_COLS, res["ap"])
    _write_csv(out / "po_lines.csv", PO_COLS, res["po"])
    _write_csv(out / "pcard_transactions.csv", PC_COLS, res["pc"])
    _write_csv(out / "contracts.csv", list(g.contracts[0]), g.contracts)

    label_rows = [
        {
            "line_key": ln.key,
            "source": ln.source,
            "golden_vendor_id": ln.vendor.golden_id,
            "l1": ln.l2.split(".")[0],
            "l2": ln.l2,
            "export_copies": ln.doc_fields["copies"],
            "injection": int(ln.injection),
            "vague": int(ln.vague),
            "planted_opportunity": ln.planted,
        }
        for ln in g.lines
    ]
    _write_csv(gold / "line_labels.csv", list(label_rows[0]), label_rows)

    vm = [
        {
            "golden_id": v.golden_id,
            "canonical_name": v.canonical,
            "primary_l2": v.l2,
            "erp_vendor_ids": ";".join(v.erp_ids),
            "kind": v.kind,
            "related_to": v.related_to,
        }
        for v in g.vf.vendors
    ]
    _write_csv(gold / "vendor_master.csv", list(vm[0]), vm)

    seen: dict[tuple[str, str, str], str] = {}
    for ln in g.lines:
        src = "PCARD" if ln.source == "PC" else ln.source
        seen.setdefault((src, ln.doc_fields["name"], ln.doc_fields["erp"]), ln.vendor.golden_id)
    aliases = [
        {"source": s, "raw_name": n, "erp_vendor_id": e, "golden_id": gid}
        for (s, n, e), gid in sorted(seen.items())
    ]
    _write_csv(gold / "vendor_aliases.csv", list(aliases[0]), aliases)

    planted = {
        "as_of": AS_OF.isoformat(),
        "window": {"start": WINDOW.start.isoformat(), "end": WINDOW.end.isoformat()},
        "rules": "savings-playbook (fragmentation rate 8%; creep >3%/quarter; gap >10%)",
        "matching": "a detection matches when type and l2 agree and, where present, "
        "item_code agrees; recall = matched / planted",
        "opportunities": g.opportunities,
    }
    (gold / "planted_opportunities.json").write_text(json.dumps(planted, indent=2) + "\n")

    files = sorted([*out.glob("*.csv"), *gold.glob("*.csv"), gold / "planted_opportunities.json"])
    base = out.parent.parent  # agent dir layout: data/synthetic and evals/golden
    counts = {
        "ap_rows": len(res["ap"]),
        "po_rows": len(res["po"]),
        "pcard_rows": len(res["pc"]),
        "unique_lines": len(g.lines),
        "vendors": len(g.vf.vendors),
        "aliases": len(aliases),
        "contracts": len(g.contracts),
        "injections": sum(ln.injection for ln in g.lines),
        "duplicate_rows": len(res["ap"]) - sum(1 for ln in g.lines if ln.source == "AP"),
    }
    manifest = {
        "generator": "spend_classification.synth",
        "generator_version": GENERATOR_VERSION,
        "seed": seed,
        "taxonomy_version": tax.version,
        "as_of": AS_OF.isoformat(),
        "counts": counts,
        "top_vendor_share_by_l2": res["shares"],
        "files": {f.relative_to(base).as_posix(): sha256(f) for f in files},
    }
    (gold / "answer_key_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest
