from shared.evals import harness, prompt_manifest
from shared.evals.harness import FAILING, gate, load_targets

T = {
    "acc": {"target": 0.9, "direction": "min", "tolerance": 0.01},
    "err": {"target": 0.05, "direction": "max", "tolerance": 0.0},
}


def status(values, baseline=None):
    return {k: v["status"] for k, v in gate(values, T, baseline).items()}


def test_not_measured_passes():
    assert status({"acc": None, "err": None}) == {"acc": "not_measured", "err": "not_measured"}


def test_target_both_directions():
    assert status({"acc": 0.89, "err": 0.06}) == {"acc": "below_target", "err": "below_target"}
    assert status({"acc": 0.95, "err": 0.01}) == {"acc": "pass", "err": "pass"}


def test_regression_vs_baseline_with_tolerance():
    base = {"acc": 0.97, "err": 0.02}
    assert status({"acc": 0.965, "err": 0.02}, base)["acc"] == "pass"  # within tolerance
    assert status({"acc": 0.95, "err": 0.03}, base) == {"acc": "regressed", "err": "regressed"}


def test_metric_disappearing_is_a_failure():
    assert status({"acc": None, "err": 0.01}, {"acc": 0.97})["acc"] == "missing_vs_baseline"
    assert "missing_vs_baseline" in FAILING


def test_every_target_has_a_scorer():
    assert set(load_targets()) <= set(harness.SCORERS)


def test_phase0_gate_passes_for_agent():
    assert harness.run("spend-classification", "smoke") == 0


def test_prompt_manifest_roundtrip(tmp_path):
    (tmp_path / "classify_line.v1.md").write_text("Classify {line}")
    assert prompt_manifest.check(tmp_path) == ["MANIFEST.json missing"]
    prompt_manifest.write(tmp_path)
    assert prompt_manifest.check(tmp_path) == []
    (tmp_path / "classify_line.v1.md").write_text("Classify {line} and add up totals")
    assert any("hash changed" in p for p in prompt_manifest.check(tmp_path))
    (tmp_path / "brief.v1.md").write_text("x")
    assert any("not in manifest" in p for p in prompt_manifest.check(tmp_path))
