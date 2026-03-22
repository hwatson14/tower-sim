# ACTIVE_TRANCHE

## Tranche ID
`PH1-TRANCHE-B_CANONICAL_PLAN_AND_TERMINOLOGY_UNIFICATION`

## Phase
`Phase 1 — Canonical planning truth and archive closure`

## Objective
Finalize canonical planning vocabulary across the major repo docs and make `AI_EXECUTION_PLAN.md` the sole long-lived planning authority without losing still-useful product-planning truth.

## Scope in
- `AI_EXECUTION_PLAN.md` as the canonical whole-program plan
- compressed absorption of any still-useful roadmap-only planning truth into `AI_EXECUTION_PLAN.md`
- terminology alignment in `README.md`, `ARCHITECTURE.md`, and other control-surface docs if needed
- roadmap deletion decision and any minimal control-file wording needed to reflect the result

## Scope out
- runtime mechanic changes
- Query Engine code changes
- objective-state promotion work
- evaluator implementation
- optimiser or advisor implementation
- Phase 1C or later tranche execution

## Required outputs
- one canonical execution-plan file
- aligned terminology in major docs
- explicit roadmap deletion or retention decision

## Required verification
- no major doc contradicts canonical layer or phase language
- roadmap content is either absorbed into `AI_EXECUTION_PLAN.md` or explicitly rejected
- no stale reference treats `AI_MIGRATION_EXECUTION_PLAN.md` or the deleted roadmap as canonical

## Acceptance criteria
- `AI_EXECUTION_PLAN.md` contains the remaining useful product-planning truth that was unique to the roadmap, or explicitly rejects it
- no major doc depends on a parallel roadmap authority
- the roadmap is either safely deleted or explicitly retained with a clear reason
- terminology is more uniform than before

## Blockers
- none

## Stop conditions
Stop once Phase 1B canonical-planning truth is self-contained and later Phase 1 work can proceed without needing the old roadmap to answer product-shaping questions.

## Non-goals
- do not edit runtime mechanics
- do not begin Query Engine seam work
- do not promote later-phase implementation work early
- do not perform broad repo cleanup unrelated to canonical planning truth
