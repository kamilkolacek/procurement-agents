# Model card — Spend Classification & Savings Finder

_Draft. Sections marked TBD are filled in as phases complete._

## Intended use
Classify procurement spend lines into a two-level internal taxonomy, normalize vendor names,
and narrate deterministic savings findings for procurement analysts. Decision support only.

## Out of scope
Approving spend, contacting vendors, changing ERP records, legal or contract interpretation,
any figure not computed by code.

## Model
- Provider/model: Claude (Anthropic). Exact model ID recorded in every run manifest.
- The LLM is used for: ambiguous vendor clusters, line classification (tier c), brief narrative.
- The LLM is **not** used for: arithmetic, sizing, ranking, thresholds, rule evaluation.

## Inputs
Vendor name and line description (untrusted text, delimited), taxonomy enum, few-shot examples
from human-approved labels. No PII, no bank fields.

## Outputs
Category label + confidence + evidence (validated against the enum); narrative text that may
only reference figures passed in with a query ID.

## Evaluation
Targets in `shared/evals/targets.toml`. Results: TBD (Phase 1 builds the golden set).

## Known limitations
TBD after shadow run (Phase 6).
