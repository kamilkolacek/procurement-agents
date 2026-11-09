"""Stage 0-1 tests: ingest hygiene, cleaning rules, and the vendor merge policy."""

from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path

import pytest
from spend_classification.ingest import IngestError, Line, ingest
from spend_classification.vendors import build_master, clean_name, resolve
from spend_classification.vendors.clean import typo_equal

from shared.evals.harness import EvalContext, pairwise_f1, vendor_resolution_detail

AGENT = Path(__file__).resolve().parents[1]
DATA = AGENT / "data" / "synthetic"


def line(n: int, source: str, raw: str, erp: str = "", amount: str = "10.00") -> Line:
    return Line(f"{source}|{n}", source, "2026-01-01", Decimal(amount), "USD", raw, erp, "x", "OPS")


# ---- cleaning rules ----
@pytest.mark.parametrize("raw,source,key", [
    ("Redwood Logistics Group", "AP", "REDWOOD LOGISTICS"),
    ("REDWOOD LOGISTICS GROUP - REMIT", "AP", "REDWOOD LOGISTICS"),
    ("Zenith Tech Soln LLC", "AP", "ZENITH TECH SOLUTIONS"),
    ("SQ *IRONCLAD LODGE #4176", "PCARD", "IRONCLAD LODGE"),
    ("SQ *REDWOOD TAVERN IL", "PCARD", "REDWOOD TAVERN"),
    ("AMZN Mktp US*2K4AB1", "PCARD", "AMAZON MARKETPLACE"),
    ("Amazon.com*XYZ", "PCARD", "AMAZON MARKETPLACE"),
    ("Metro Office & Tech Supply Co", "AP", "METRO OFFICE AND TECH SUPPLY"),
])
def test_clean_name(raw: str, source: str, key: str) -> None:
    assert clean_name(raw, source).key == key


def test_typo_equal_only_adjacent_swaps() -> None:
    assert typo_equal("ROOK SOFWTARE", "ROOK SOFTWARE")
    assert not typo_equal("REDWOOD LOGISTIX", "REDWOOD LOGISTICS")  # different word, not a typo
    assert not typo_equal("ZENITH TECH SERVICES", "ZENITH TECH SOLUTIONS")


# ---- ingest ----
def test_ingest_dedupes_and_strips_pii() -> None:
    res = ingest(DATA)
    assert sum(res.duplicates_removed.values()) == 100
    assert len({ln.line_key for ln in res.lines}) == len(res.lines) == 19858
    blob = repr(res.lines[:200]) + repr(res.lines[-200:])
    assert "TESTACCT" not in blob and "TESTTIN" not in blob
    assert not hasattr(res.lines[0], "cardholder")


def test_ingest_rejects_conflicting_duplicate_key(tmp_path: Path) -> None:
    for name in ("ap_invoices.csv", "po_lines.csv", "pcard_transactions.csv"):
        (tmp_path / name).write_bytes((DATA / name).read_bytes())
    rows = list(csv.reader((tmp_path / "pcard_transactions.csv").open()))
    rows.append(rows[1][:6] + ["999.99"] + rows[1][7:])  # same Txn ID, different amount
    with (tmp_path / "pcard_transactions.csv").open("w", newline="") as fh:
        csv.writer(fh).writerows(rows)
    with pytest.raises(IngestError):
        ingest(tmp_path)


# ---- merge policy ----
def test_same_erp_id_is_one_vendor_across_spellings() -> None:
    res = resolve([line(1, "AP", "Acme Corp", "S1"), line(2, "AP", "ACME CORPORATION", "S1")])
    assert len(res.entities) == 1


def test_confusable_vendors_are_not_merged_and_are_proposed() -> None:
    res = resolve([line(1, "AP", "Zenith Tech Services", "S1"),
                   line(2, "AP", "Zenith Tech Solutions LLC", "S2")])
    assert len(res.entities) == 2  # clearly different words: separate, nothing to review
    res = resolve([line(1, "AP", "Redwood Logistics Group", "S1"),
                   line(2, "AP", "Redwood Logistix LLC", "S2")])
    assert len(res.entities) == 2  # near-identical strings, no marker: never auto-merged
    assert [r.reason for r in res.review] == ["POSSIBLE_DUPLICATE"]


def test_replacement_marker_merges_duplicate_erp_records() -> None:
    res = resolve([line(1, "AP", "Quill Janitorial Corp", "S1"),
                   line(2, "AP", "QUILL JANITORL CORP (NEW)", "S2")])
    assert len(res.entities) == 1 and res.entities[0].erp_ids == {"S1", "S2"}


def test_card_prefix_match_requires_a_capped_descriptor() -> None:
    # "ZEPHYR AIR" is a different vendor, not a truncation of "ZEPHYR AIRLINES"
    res = resolve([line(1, "AP", "Zephyr Airlines Inc", "S1"),
                   line(2, "PCARD", "SQ *ZEPHYR AIR OR")])
    assert len(res.entities) == 2
    # a 25-character descriptor is a truncation and attaches to the unique vendor
    res = resolve([line(1, "AP", "Willow Creek Stationers Inc", "S1"),
                   line(2, "PCARD", "SQ *WILLOW CREEK STATION")])
    assert len(res.entities) == 1


def test_ambiguous_card_descriptor_stays_separate_and_is_queued() -> None:
    res = resolve([line(1, "AP", "Keystone Facility Care Inc", "S1"),
                   line(2, "AP", "Keystone Facility Care West Inc", "S2"),
                   line(3, "PCARD", "TST* KEYSTONE FACILITY CAR")])
    assert len(res.entities) == 3
    assert [r.reason for r in res.review].count("AMBIGUOUS_MATCH") == 1


def test_approved_alias_overrides_rules() -> None:
    lines = [line(1, "AP", "Acme Corp", "S1")]
    res = resolve(lines, {("AP", "Acme Corp", "S1"): "GV-HUMAN"})
    assert res.alias_to_entity[("AP", "Acme Corp", "S1")] == "GV-HUMAN"


# ---- outputs ----
def test_master_spend_reconciles_to_input_and_carries_query_id() -> None:
    ing = ingest(DATA)
    master = build_master(ing.lines, resolve(ing.lines), ing.input_hash)
    assert sum(Decimal(m["total_spend"]) for m in master) == sum(ln.amount for ln in ing.lines)
    assert sum(int(m["row_count"]) for m in master) == len(ing.lines)
    assert all(m["query_id"].startswith("vendor_spend_") and m["data_hash"] for m in master)


def test_resolution_is_deterministic() -> None:
    lines = ingest(DATA).lines
    assert resolve(lines).alias_to_entity == resolve(lines).alias_to_entity


# ---- eval ----
def test_pairwise_f1_penalises_wrong_merge_and_split() -> None:
    truth = {"a": "1", "b": "1", "c": "2"}
    assert pairwise_f1(dict(truth), truth)["f1"] == 1.0
    assert pairwise_f1({"a": "x", "b": "y", "c": "z"}, truth)["recall"] == 0.0
    assert pairwise_f1({"a": "x", "b": "x", "c": "x"}, truth)["precision"] < 1.0


def test_vendor_resolution_meets_target_on_synthetic_data() -> None:
    d = vendor_resolution_detail(EvalContext(AGENT, "full"))
    assert d["missing"] == 0 and d["f1"] >= 0.95
