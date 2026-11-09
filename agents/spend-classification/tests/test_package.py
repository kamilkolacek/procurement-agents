import importlib

import spend_classification

STAGES = ["ingest", "vendors", "classify", "cube", "opportunities", "brief"]


def test_version():
    assert spend_classification.__version__


def test_stage_packages_import():
    for stage in STAGES:
        mod = importlib.import_module(f"spend_classification.{stage}")
        assert mod.__doc__, f"{stage} needs a docstring saying which phase builds it"
