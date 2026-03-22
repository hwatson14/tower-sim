# ACTIVE_TRANCHE

## Tranche ID
`PH1-TRANCHE-A_CONTROL_STACK_CLOSEOUT`

## Phase
`Phase 1 — Canonical planning truth and archive closure`

## Objective
Close or explicitly supersede the current bootstrap control tranche and promote the repo onto the new phase-gated execution system so future Codex runs operate from:
- durable rules in `AGENTS.md`
- canonical whole-program truth in `AI_EXECUTION_PLAN.md`
- one active tranche file
- machine-readable phase/tranche delivery and verification state in `BURNDOWN.yaml`

## Scope in
- `AI_EXECUTION_PLAN.md`
- `ACTIVE_TRANCHE.md`
- `BURNDOWN.yaml`
- major doc pointers that still reference `AI_MIGRATION_EXECUTION_PLAN.md`

## Scope out
- runtime mechanic changes
- Query Engine code changes
- `stat_input_compiler.py` seam code changes
- objective-state promotion work
- evaluator, optimiser, or advisor implementation
- archive content implementation

## Required outputs
- control-stack closeout note
- explicit bootstrap status: completed, superseded, or blocked
- first promoted tranche ID under the phase-gated system
- updated `ACTIVE_TRANCHE.md`
- updated `BURNDOWN.yaml`
- updated major doc pointers to `AI_EXECUTION_PLAN.md`

## Required verification
- current bootstrap acceptance criteria checked against repo truth
- control-file naming and references reviewed
- stale IDs identified or removed
- active tranche, burndown, and canonical plan use the same phase and tranche vocabulary

## Acceptance criteria
- the old bootstrap tranche is explicitly closed or superseded
- `ACTIVE_TRANCHE.md` points at the phase-gated system
- `BURNDOWN.yaml` uses phase-gated tranche IDs and plan references
- no major control file still points to `AI_MIGRATION_EXECUTION_PLAN.md`
- the next executable Phase 1 tranche is unambiguous

## Blockers
- none

## Stop conditions
Stop once the acceptance criteria above are satisfied and the burndown reflects the promoted control-stack state.

## Non-goals
- do not start Phase 1B or later implementation work here
- do not change runtime code
- do not rewrite archive content
- do not add new architecture layers
