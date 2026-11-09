# Autonomy levels

Every agent starts at **L0**. Moving up a level needs eval evidence that meets the bar below
and a recorded approval (an ADR in `governance/decisions/` signed by the approver).

| Level | What the agent may do | Promotion bar |
|---|---|---|
| **L0 — Propose only** | Everything is a draft. Every label, vendor merge and opportunity waits for a human. | — (starting level) |
| **L1 — Auto-accept low risk** | Auto-accept high-confidence labels in low-risk categories. 5% sampled QA continues. High-risk / high-dollar items still go to review. | Two consecutive shadow runs meeting all targets in `shared/evals/targets.toml`; high-confidence precision >= 98% on QA sample |
| **L2 — Auto-publish drafts** | Brief is published as Draft automatically; a human still moves it to Reviewed/Published. | Three months at L1 with no reportable misstatement; untraceable figures = 0 |

At no level can an agent write to an ERP, send messages, or move money.

## Current levels
| Agent | Level | Since | Approval |
|---|---|---|---|
| spend-classification | L0 | 2026-11-08 | n/a (default) |

## Demotion
Any of these drops the agent back to L0 until reviewed: an eval regression below target, an
untraceable figure reaching a published brief, a failed injection test, or a data-policy breach.
