# Agent #1 — Invoice Exception Agent

Lives in its own repository: <https://github.com/kamilkolacek/invoice-exception-agent>.

It is not part of this monorepo yet. ADR 0001 records why: moving it would rewrite its public
history and CI, so it stays standalone until a migration is planned. The shared governance code
here (`shared/audit`, `shared/guardrails`, `shared/evals`) is written so Agent #1 can adopt it later.
