# Risk register

Owner: _TBD (named human)_ · Approver: _TBD_ · Reviewed: 2026-11-08 (initial draft)

| ID | Risk | Likelihood | Impact | Controls | Evidence / metric | Status |
|---|---|---|---|---|---|---|
| R1 | **Misclassification** of spend lines skews category totals and savings | Medium | Medium | Tiered classifier; confidence threshold 0.85; review queue; 5% QA sample; blind verifier subagent | L1 >= 95%, L2 >= 90%, high-confidence precision >= 98% | Open (Phase 3) |
| R2 | **Hallucinated or untraceable savings** figures in the brief | Medium | High | LLM never computes; every figure carries query ID + row count + data hash; reconciliation to cube fails the run | Untraceable figures = 0; sizing error <= +/-5% | Open (Phase 4-5) |
| R3 | **Prompt injection** via vendor names / line descriptions | Medium | High | No tools on classifier calls; delimiters; enum-validated output; red-team subagent | Injection test pass rate = 100% | Open (Phase 3, 5) |
| R4 | **Cost overrun** from LLM calls | Low | Medium | Classify unique pairs only; cached taxonomy prefix; per-run cost/token caps; kill switch | Cost and tokens in run manifest | Open (Phase 3) |
| R5 | **Data leakage** of real spend data or PII | Low | High | Synthetic only until approved; `data/real/` gitignored and hook-blocked; PII/bank fields stripped at ingest; secret/PII scan in pre-commit and CI | Scan clean on every PR | Partially controlled (Phase 0) |
| R6 | **Silent self-modification** of labels, prompts or thresholds | Low | Medium | Gated learning via PR + eval gate; protected paths hook; prompt manifest check | CI prompt-hash check | Controlled (Phase 0) |
| R7 | **Eval set contamination** (golden labels edited to make scores pass) | Low | High | `evals/golden/` hook-blocked; changes only by human override, logged | Override log | Controlled (Phase 0) |
