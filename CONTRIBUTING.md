# Contributing to ThreadCraft

Solo-developer academic project. This document exists mainly to fix the conventions in place, since the commit/PR history is itself a graded deliverable.

## Branching

Trunk-based (GitHub Flow): `main` is always deployable. Every change lands via a short-lived branch + pull request, never a direct push to `main`.

Branch naming: `<type>/<kebab-slug>`, where `type` is one of `feat`, `fix`, `refactor`, `chore`, `docs`, `test`, `ci`.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/), scoped:

```
feat(pricing): derive fabric metres from fit multiplier
fix(orders): persist guest orders (user_id now nullable)
test(pricing): add 20 verified design combinations
docs(erd): add entity relationship diagram
```

Commit at genuine checkpoints (schema → service → router → tests → docs), not as one dump per branch.

## Pull requests

Every PR body follows: **What / Why / How to test**, and links the issue it closes (`Closes #N`). Merge with a merge commit (not squash) so the branch's incremental history is preserved — that history is graded evidence of iterative development, not just the final diff.

## Code style

- Backend: `ruff check` + `ruff format`, enforced in CI.
- Frontend: `eslint`, enforced in CI. Plain JSX, no TypeScript (see `docs/architecture/adr/0004-plain-jsx-over-typescript.md`).

## Tests

New backend logic in `services/` needs a corresponding `pytest` file. The pricing engine in particular must stay at 100% line coverage — it's an explicitly graded artefact.
