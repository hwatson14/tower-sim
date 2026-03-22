# ACTIVE_TRANCHE

## Tranche ID
`PH1-TRANCHE-B_CANONICAL_PLAN_AND_TERMINOLOGY_UNIFICATION`

## Phase
`Phase 1 — Canonical planning truth and archive closure`

## Objective
Finalize the canonical planning vocabulary across the major repo documents now that the bootstrap control tranche is closed and the phase-gated execution system is live.

## Scope in
- `AI_EXECUTION_PLAN.md`
- `README.md`
- `ARCHITECTURE.md`
- `AGENTS.md`
- explicit retirement or supersession note for parallel planning language
- terminology alignment needed so major docs describe the same canonical layers, phases, and control files

## Scope out
- runtime mechanic changes
- Query Engine code changes
- archive ledger implementation beyond naming and terminology alignment
- objective-state promotion work
- evaluator, optimiser, or advisor implementation

## Required outputs
- one canonical execution-plan file
- aligned terminology in major docs
- explicit roadmap retirement or supersession note
- tranche closeout note if any major document still carries stale planning terminology

## Required verification
- major docs reviewed for canonical layer and phase wording
- no major doc contradicts the canonical execution plan
- roadmap content is either absorbed into `AI_EXECUTION_PLAN.md` or explicitly marked non-canonical
- control files and major docs use the same plan filename and tranche vocabulary where referenced

## Acceptance criteria
- one canonical execution-plan file exists and is current
- no major doc contradicts layer or phase language from `AI_EXECUTION_PLAN.md`
- any surviving roadmap language is explicitly retired, superseded, or scoped as historical only
- the tranche leaves Phase 1 terminology more uniform than it found it

## Blockers
- none

## Stop conditions
Stop once the canonical terminology is aligned across the major docs in scope and any residual parallel-planning language is explicitly retired or superseded.

## Non-goals
- do not start Phase 1C or later implementation work here
- do not change runtime code
- do not rewrite archive content beyond necessary terminology/pointer updates
- do not add new architecture layers
