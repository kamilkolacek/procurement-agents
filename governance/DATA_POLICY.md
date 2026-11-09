# Data policy

## Current rule: synthetic data only
No real company data is processed until this file records an approval (who, when, scope,
retention). Until then `agents/*/data/real/` stays empty.

## Classes
| Class | Where | Committed? | Claude may read? |
|---|---|---|---|
| Synthetic | `data/synthetic/` | Yes | Yes |
| Human labels / aliases | `data/labels/` | Yes (synthetic-derived only) | Yes |
| Real | `data/real/` | Never (gitignored) | **No** (hook-blocked) |
| Run artifacts | `runs/`, `outputs/` | Synthetic samples only | Yes |
| Secrets | `.env`, credentials | Never | **No** (hook-blocked) |

## Handling rules
- PII and bank-detail fields (bank account, IBAN, routing, SWIFT, tax ID, personal names on
  P-card lines) are dropped at ingest and never sent to an LLM.
- Data credentials, when introduced, are read-only.
- No outbound channels: agents write files only.
- Pre-commit and CI run `scripts/scan_secrets.py` (secrets + PII patterns).

## Approvals for real data
| Date | Approver | Scope | Retention | Reference |
|---|---|---|---|---|
| — | — | — | — | — |
