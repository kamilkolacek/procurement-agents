---
name: spend-taxonomy
description: Structure and rules of the two-level spend taxonomy (L1/L2, risk flags, UNSPSC crosswalk). Load when drafting or changing taxonomy.yaml, writing classification prompts, or validating labels.
---

# Spend taxonomy

Source of truth: `agents/spend-classification/taxonomy/taxonomy.yaml` (protected path; changes
follow `governance/CHANGE_CONTROL.md`). Decision: ADR 0002.

## Shape
```yaml
version: "2026.1"          # bump on any change; recorded in every run manifest
categories:
  - l1: IT
    name: Information Technology
    l2:
      - code: IT.SAAS
        name: Software subscriptions (SaaS)
        risk: low            # low | high  (high always goes to review)
        unspsc: ["43230000"] # optional crosswalk
        include: ["subscription", "license seat"]
        exclude: ["hardware"]
```
Target ~10 L1 and ~40 L2. Every L2 code is `<L1>.<SHORT>`, upper case, unique.

## Rules
- L2 codes are the LLM's output enum. Anything not in the enum fails validation
  (`shared.guardrails.taxonomy_validator`) and goes to the review queue.
- Always include `UNCLASSIFIED.REVIEW` as an escape hatch; it is `risk: high`.
- `risk: high` for categories where a wrong label has real consequences: professional services,
  legal, contractors (possible worker classification issues), capex-like items, charitable or
  political payments, travel cash advances.
- `include` / `exclude` hints feed the prompt; keep them short and concrete.
- Never reuse a retired code for a different meaning; mark it `retired: true` instead.

## When changing it
1. Edit with a human override, bump `version`.
2. Re-run `make eval` and paste the before/after table into the PR.
3. Update the crosswalk and any approved labels whose code moved.
