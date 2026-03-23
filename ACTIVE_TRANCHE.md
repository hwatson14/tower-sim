# ACTIVE_TRANCHE

## Tranche ID
`PH4-TRANCHE-A_SURFACE_VERIFICATION_REGISTRY`

## Phase
`Phase 4 — Verification and evaluator foundation`

## Objective
Promote Phase 4 by making `PH4-TRANCHE-A_SURFACE_VERIFICATION_REGISTRY` the current executable tranche and align the control stack around the next governed verification owner surface.

## Why this tranche exists
Phase 3 bounded verification is now evidenced and Phase 3 closeout is complete. The next executable work is to establish the governed surface-verification registry that Phase 4 needs before broader evaluator or comparison work can proceed. This control-stack promotion PR only updates repo truth to reflect that sequencing; it does not implement Phase 4 work.

## Change classification
- **Cleanup only**: control-stack truth promotion from completed Phase 3 closeout to active Phase 4 entry.
- **Control-stack reconciliation**: make the active phase and tranche unambiguous across the control files.
- **Plan alignment**: remove stale wording that still describes Query Engine-owned objective surfaces as optimizer-local or Phase 3 as still open.

## Scope in
- promote the active phase from PH3 to PH4
- set `PH4-TRANCHE-A_SURFACE_VERIFICATION_REGISTRY` as the current executable tranche
- align `ACTIVE_TRANCHE.md`, `BURNDOWN.yaml`, and `AI_EXECUTION_PLAN.md` to the same control-stack truth
- keep Phase 3 recorded as complete and Phase 4 as active

## Scope out
- implementation of the Phase 4 surface-verification registry
- evaluator contract or evaluator runtime work
- new code paths, registries, or verification helpers
- full `pytest` or unrelated test cleanup
- opportunistic doc cleanup outside the major control files

## Required outputs
- updated `ACTIVE_TRANCHE.md` for the Phase 4A active tranche
- updated `BURNDOWN.yaml` with `active_phase_id: PH4` and `active_tranche_id: PH4-TRANCHE-A_SURFACE_VERIFICATION_REGISTRY`
- updated `AI_EXECUTION_PLAN.md` wording so no major control file claims stale Phase 3 state

## Acceptance criteria
- Phase 3 remains recorded as complete in the control stack
- Phase 4 is the active phase
- `PH4-TRANCHE-A_SURFACE_VERIFICATION_REGISTRY` is the current executable tranche
- no major control file still says `derived::ehp`, `derived::edamage`, or `derived::eecon` are optimizer-local
- no major control file still implies that Phase 3 closeout is open

## Current status
- Phase 3 bounded verification was evidenced on 2026-03-23 and its closeout remains complete in repo truth.
- Phase 4 is now the active phase in the control stack.
- Phase 4A is selected as the current executable tranche, but no Phase 4 implementation work is part of this PR.
