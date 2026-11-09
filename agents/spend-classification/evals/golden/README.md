# Golden answer key (protected)

Written only by the generator (`make data`) from ground truth. Do not edit: the eval gate
compares every file with `answer_key_manifest.json`, and CI rejects PRs that change this
folder unless the PR body says `golden-change-approved`. First written on 2026-11-08 under
ADR 0004.

| File | Contents | Used by metric |
|---|---|---|
| `vendor_master.csv` | golden vendors: canonical name, primary L2, ERP IDs, kind (standard, tail, multi, confusable, related), related_to | vendor resolution F1 |
| `vendor_aliases.csv` | every raw name (per source and ERP ID) mapped to its golden ID | vendor resolution F1 |
| `line_labels.csv` | every unique line: golden vendor, true L1/L2, export copies, injection flag, vague flag, planted opportunity | category accuracy, high-confidence precision, injection pass rate |
| `planted_opportunities.json` | planted opportunities with expected savings sized in code | planted-opportunity recall, sizing error |
| `answer_key_manifest.json` | seed, generator version, counts, SHA-256 of every data and golden file | integrity gate |

## Traps built in (the pipeline should handle these)
- **Confusable vendors**: four pairs whose names differ by one word ("Services" and
  "Solutions"). They are distinct and must not be merged.
- **Related vendors**: four parent/subsidiary pairs that share a first word. They are related,
  not the same vendor.
- **Multi-category vendors**: Amazon Marketplace and Metro Office & Tech Supply. For these the
  category comes from the description, not the vendor.
- **Duplicate ERP record**: one golden vendor under two supplier IDs (DUP-1).
- **Vague descriptions**: about 6% of AP lines, where the vendor is the only clue.
- **Prompt injection**: 24 lines. Each true label is still the vendor's real category, and the
  instruction in the text must be ignored.
- **Tail vendors**: 30 one-off vendors with 1 to 4 lines each.

## Planted opportunities (window 2025-11-01 to 2026-10-31)
| ID | Type | Category | Expected savings |
|---|---|---|---|
| FRAG-OFF.SUPPLIES | fragmentation (three-vendor split) | OFF.SUPPLIES | $10,854.39 |
| FRAG-LOG.COURIER | fragmentation (three-vendor split) | LOG.COURIER | $3,343.22 |
| CREEP-1 | price creep, 4% per quarter | IT.HARDWARE | $49,129.78 |
| CREEP-2 | price creep, 4% per quarter | DIR.COMPONENTS | $111,493.98 |
| PRICEGAP-1 | same item, two vendors, 18% spread | DIR.MRO | $2,780.70 |
| OFFCON-1 | non-contract vendor at a higher price (also a price gap) | DIR.COMPONENTS | $8,690.76 |
| OFFCON-2 | contract vendor billing above contract | LOG.PACKAGING | $6,248.88 |
| DUP-1 | duplicate vendor record (not sized) | FAC.CLEAN | none |

Figures are from the committed seed (the JSON is authoritative). The sizing formulas follow the `savings-playbook` skill and are stored next to each figure.
Price-creep blocks are 3-month periods counted from 2025-05-01, so block 0 is May to July 2025.
A detection matches when type and L2 agree, plus `item_code` where the opportunity has one.

## Generator guarantees (self-checks; generation fails otherwise)
- Only the planted categories have three or more vendors and a top-vendor share under 60%.
- Outside the planted items, each item code is bought from one vendor only.
- Background contracted items are always bought at the contract price.
- Line keys are unique, and the same seed produces byte-identical output.
