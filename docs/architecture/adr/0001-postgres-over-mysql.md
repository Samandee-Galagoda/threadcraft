# ADR 0001: PostgreSQL over MySQL

## Status
Accepted

## Context
The proposal specifies MySQL (matching the original XAMPP-based local prototype). Free-tier cloud database hosting was evaluated for the deployed demo:

- **Neon (Postgres)**: free plan does not expire, autosuspends after ~5 min idle with sub-second wake, 0.5 GB storage.
- **Render Postgres (MySQL-adjacent free option)**: expires 30 days after creation regardless of activity, then a 14-day grace period before hard deletion. Unsuitable for a project that needs a stable demo URL across a multi-week grading period.
- **Supabase (Postgres)**: pauses after 7 days of no database activity, restorable for up to a year.
- Comparable free-tier MySQL hosting is scarcer and more time-limited than the Postgres options above.

## Decision
Use PostgreSQL in production (Neon free tier), SQLite for local development and CI (zero setup, no service container needed). SQLAlchemy's engine abstraction means the application code is unaffected by this choice — only `DATABASE_URL` changes between environments.

## Consequences
- JSON snapshot columns (`app/models/order.py`) use plain `sqlalchemy.JSON` rather than a Postgres-specific `JSONB`, and status fields are plain strings rather than a native enum, so the same model definitions work identically on SQLite (tests/CI) and Postgres (production) without a Postgres-only test service container.
- This is a deliberate deviation from the original proposal, documented here for the dissertation rather than silently substituted.
