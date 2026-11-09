"""Synthetic data generator and answer key: reproducibility, integrity, and planted signals."""

import csv
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

import pytest
from spend_classification.synth.generate import DEFAULT_SEED, generate

from shared.evals.harness import golden_integrity
from shared.guardrails.taxonomy_validator import ESCAPE_CODE, Taxonomy

AGENT = Path(__file__).resolve().parents[1]
GOLDEN = AGENT / "evals" / "golden"
SYNTH = AGENT / "data" / "synthetic"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def regenerate(tmp: Path, seed: int) -> dict:
    return generate(AGENT, seed, tmp / "data" / "synthetic", tmp / "evals" / "golden")


@pytest.fixture(scope="module")
def committed_manifest() -> dict:
    return json.loads((GOLDEN / "answer_key_manifest.json").read_text())


@pytest.fixture(scope="module")
def labels() -> list[dict[str, str]]:
    return rows(GOLDEN / "line_labels.csv")


def test_committed_data_matches_generator(tmp_path, committed_manifest):
    fresh = regenerate(tmp_path, DEFAULT_SEED)
    assert fresh["files"] == committed_manifest["files"], (
        "committed data/golden files differ from the generator; run `make data`"
    )


def test_seed_changes_output(tmp_path, committed_manifest):
    assert regenerate(tmp_path, DEFAULT_SEED + 1)["files"] != committed_manifest["files"]


def test_golden_integrity_passes_and_detects_edits(tmp_path):
    assert golden_integrity(AGENT) == []
    regenerate(tmp_path, DEFAULT_SEED)
    f = tmp_path / "evals" / "golden" / "line_labels.csv"
    f.write_text(f.read_text().replace("IT.SAAS", "IT.CLOUD", 1))
    assert any("line_labels.csv" in p for p in golden_integrity(tmp_path))


def test_scale_matches_plan(committed_manifest):
    c = committed_manifest["counts"]
    assert 19_000 <= c["unique_lines"] <= 21_000
    assert 280 <= c["vendors"] <= 320
    assert c["injections"] == 24 and c["duplicate_rows"] > 0


def test_labels_are_valid_taxonomy_codes(labels):
    tax = Taxonomy.from_yaml(AGENT / "taxonomy" / "taxonomy.yaml")
    assert 38 <= len([c for c in tax.codes if c != ESCAPE_CODE]) <= 45
    assert {r["l2"] for r in labels} <= set(tax.codes)
    assert len({r["line_key"] for r in labels}) == len(labels)


def test_exports_reconcile_to_labels(labels):
    copies = {r["line_key"]: int(r["export_copies"]) for r in labels}
    ap = Counter(f"AP|{r['Invoice ID']}|{r['Line']}" for r in rows(SYNTH / "ap_invoices.csv"))
    po = {f"PO|{r['PO Number']}|{r['PO Line']}" for r in rows(SYNTH / "po_lines.csv")}
    pc = {f"PC|{r['Txn ID']}" for r in rows(SYNTH / "pcard_transactions.csv")}
    assert {k: v for k, v in ap.items()} == {k: v for k, v in copies.items() if k.startswith("AP")}
    assert po == {k for k in copies if k.startswith("PO")}
    assert pc == {k for k in copies if k.startswith("PC")}


def test_aliases_point_to_known_vendors():
    master = {r["golden_id"] for r in rows(GOLDEN / "vendor_master.csv")}
    aliases = rows(GOLDEN / "vendor_aliases.csv")
    assert {a["golden_id"] for a in aliases} <= master
    per_vendor = Counter(a["golden_id"] for a in aliases)
    assert sum(1 for n in per_vendor.values() if n >= 3) > 100, "names should be messy"


def test_planted_opportunities_shape():
    planted = json.loads((GOLDEN / "planted_opportunities.json").read_text())
    opps = planted["opportunities"]
    assert Counter(o["type"] for o in opps) == {
        "fragmentation": 2,
        "price_creep": 2,
        "price_gap": 1,
        "off_contract": 2,
        "duplicate_vendor": 1,
    }
    for o in opps:
        if o["type"] != "duplicate_vendor":
            assert Decimal(o["expected_savings"]) > 0 and o["evidence_lines"] > 0


def test_price_creep_is_about_four_percent_per_quarter():
    planted = json.loads((GOLDEN / "planted_opportunities.json").read_text())
    po = rows(SYNTH / "po_lines.csv")
    for o in (x for x in planted["opportunities"] if x["type"] == "price_creep"):
        by_block = defaultdict(set)
        for r in po:
            if r["Item Code"] == o["item_code"]:
                y, m = int(r["Order Date"][:4]), int(r["Order Date"][5:7])
                by_block[((y - 2025) * 12 + m - 5) // 3].add(Decimal(r["Unit Price"]))
        prices = [min(by_block[b]) for b in sorted(by_block)]
        assert len(prices) == 6
        for a, b in zip(prices, prices[1:], strict=False):
            assert Decimal("1.035") < b / a < Decimal("1.045")


def test_duplicate_vendor_has_two_erp_ids():
    planted = json.loads((GOLDEN / "planted_opportunities.json").read_text())
    dup = next(o for o in planted["opportunities"] if o["type"] == "duplicate_vendor")
    used = {r["Supplier ID"] for r in rows(SYNTH / "ap_invoices.csv")}
    assert len(dup["erp_vendor_ids"]) == 2 and set(dup["erp_vendor_ids"]) <= used


def test_pii_columns_present_for_ingest_to_strip():
    ap = rows(SYNTH / "ap_invoices.csv")
    pc = rows(SYNTH / "pcard_transactions.csv")
    assert any(r["Remit Bank Account"] for r in ap) and any(r["Supplier Tax ID"] for r in ap)
    assert all(r["Cardholder"] for r in pc)
    assert all(r["Remit Bank Account"].startswith(("TESTACCT", "")) for r in ap)
