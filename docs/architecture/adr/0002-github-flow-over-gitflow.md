# ADR 0002: GitHub Flow over Git Flow

## Status
Accepted

## Context
This is a solo-developer project with a single deployable environment (no separate staging), built over roughly a week. Git Flow's `develop` + `release/*` + `hotfix/*` branch structure exists to coordinate multiple contributors and multiple simultaneously-supported environments — neither applies here.

## Decision
Trunk-based development (GitHub Flow): `main` is the only long-lived branch, protected and always deployable. Every change lands via a short-lived `feat/*`/`fix/*`/`chore/*` branch and a pull request, merged with a merge commit (not squashed) so the branch's incremental commit history stays visible in `main`'s history.

## Consequences
- Every PR gets its own Vercel preview deployment — a `develop`-gated workflow would not produce this for free.
- The commit graph is a genuine record of iterative development (a graded deliverable) rather than a flat sequence of squashed features.
- No `develop` branch means no risk of `main` and `develop` drifting out of sync, which would have been pure overhead for one person.
