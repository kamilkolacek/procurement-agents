import json

import pytest

from shared.audit.decision_log import GENESIS, DecisionLog, verify
from shared.audit.run_manifest import RunManifest, inputs_hash


def test_chain_links_and_verifies(tmp_path):
    log = DecisionLog(tmp_path / "decisions.jsonl")
    a = log.append({"item": "L1", "label": "IT.SAAS", "confidence": 0.97})
    b = log.append({"item": "L2", "label": "FAC.CLEAN", "confidence": 0.62})
    assert a["prev_hash"] == GENESIS and b["prev_hash"] == a["hash"]
    assert (a["seq"], b["seq"]) == (1, 2)
    assert verify(tmp_path / "decisions.jsonl").ok


def test_reopen_continues_chain(tmp_path):
    p = tmp_path / "d.jsonl"
    first = DecisionLog(p).append({"x": 1})
    second = DecisionLog(p).append({"x": 2})
    assert second["prev_hash"] == first["hash"] and second["seq"] == 2
    assert verify(p).records == 2


def test_edit_is_detected(tmp_path):
    p = tmp_path / "d.jsonl"
    log = DecisionLog(p)
    for i in range(3):
        log.append({"i": i, "label": "IT.SAAS"})
    lines = p.read_text().splitlines()
    rec = json.loads(lines[1])
    rec["label"] = "LEGAL.OUTSIDE"
    lines[1] = json.dumps(rec)
    p.write_text("\n".join(lines) + "\n")
    res = verify(p)
    assert not res.ok and res.first_bad_seq == 2 and "edited" in res.reason


def test_deletion_is_detected(tmp_path):
    p = tmp_path / "d.jsonl"
    log = DecisionLog(p)
    for i in range(3):
        log.append({"i": i})
    lines = p.read_text().splitlines()
    p.write_text("\n".join([lines[0], lines[2]]) + "\n")
    assert not verify(p).ok


def test_reserved_keys_rejected(tmp_path):
    with pytest.raises(ValueError):
        DecisionLog(tmp_path / "d.jsonl").append({"hash": "forged"})


def test_run_manifest_written(tmp_path):
    src = tmp_path / "ap.csv"
    src.write_text("vendor,amount\nACME,10.00\n")
    m = RunManifest(agent="spend-classification", input_hash=inputs_hash([src]))
    m.finish("succeeded")
    out = m.write(tmp_path / "runs")
    data = json.loads(out.read_text())
    assert data["status"] == "succeeded" and data["run_id"] in str(out)
    assert isinstance(data["cost_usd"], str)  # money never stored as float
