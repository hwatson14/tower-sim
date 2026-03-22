# ACTIVE_TRANCHE

## Tranche ID
`PH2-TRANCHE-C_COVERED_FAMILY_DELEGATION_MANIFEST`

## Phase
`Phase 2 — Query Engine ownership completion`

## Objective
Finalize the governed covered-family delegation manifest using the completed Phase 2A ownership ledger and the bounded Query Engine family contracts as the governing boundary.

## Scope in
- finalized covered-family list for Phase 2C
- explicit delegated scope per declared family
- explicit fallback ownership for every undelegated family or non-covered remainder
- visible parity and benchmark status per manifest row
- no-false-implication review against KB contracts and the public compatibility entrypoint

## Scope out
- code-path routing changes for `resolve_stats()`
- formula rewrites
- undeclared family expansion beyond the governed Query Engine contracts
- simulator or optimiser changes
- benchmark execution beyond status declaration

## Required outputs
- covered-family delegation manifest
- explicit delegated-scope notes for each declared family
- explicit fallback-owner declaration for undelegated areas
- visible parity and benchmark status for every manifest row

## Required verification
- covered-family scope is explicit and bounded
- fallback owner is named for every undelegated family or non-covered remainder
- manifest language does not imply full delegation
- parity and benchmark status are visible for Phase 2E handoff
- docs and tranche state reflect the new manifest truth

## Acceptance criteria
- the Phase 2C family list is finalized from governed Query Engine declarations
- delegated scope is explicit for each delegated row
- undelegated areas are visible, bounded, and name their fallback owner
- parity and benchmark status exist for every manifest row
- no major doc implies full `resolve_stats()` delegation

## Blockers
- none

## Stop conditions
Stop once the covered-family manifest is finalized, undelegated fallback ownership is explicit, and status visibility is landed for Phase 2E handoff.

## Non-goals
- do not rewrite formulas
- do not implement `resolve_stats()` delegation routing in this tranche
- do not add undeclared families to the manifest
- do not claim parity or benchmark completion without evidence
