AGENT ?= spend-classification
RUN   ?=
UV    := uv run --quiet

.PHONY: help setup lint test check scan prompt-hash eval eval-smoke data run review audit-pack

help:
	@echo "setup        install deps (uv sync)"
	@echo "lint         ruff check"
	@echo "test         pytest"
	@echo "check        lint + test + scan + prompt-hash + eval-smoke (what CI runs)"
	@echo "scan         secret and PII scan of tracked files"
	@echo "prompt-hash  verify prompts/MANIFEST.json matches prompt files"
	@echo "eval         full eval run -> evals/reports/"
	@echo "eval-smoke   fast eval gate (used by Stop hook)"
	@echo "data         generate synthetic data          (Phase 1)"
	@echo "run          run the pipeline on synthetic data (Phases 2-5)"
	@echo "review       open the reviewer tool           (Phase 3)"
	@echo "audit-pack   RUN=<id> build an audit pack     (Phase 5)"

setup:
	uv sync

lint:
	$(UV) ruff check .

test:
	$(UV) pytest

scan:
	$(UV) python scripts/scan_secrets.py

prompt-hash:
	$(UV) python -m shared.evals.prompt_manifest --check agents/$(AGENT)/prompts

eval:
	$(UV) python -m shared.evals.harness --agent $(AGENT) --mode full

eval-smoke:
	$(UV) python -m shared.evals.harness --agent $(AGENT) --mode smoke

check: lint test scan prompt-hash eval-smoke

data run review audit-pack:
	@echo "make $@: not built yet (see agents/$(AGENT)/STATUS.md for the phase that adds it)"; exit 1
