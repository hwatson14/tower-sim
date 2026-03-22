# ACTIVE_TRANCHE

## Tranche ID
`PH2-TRANCHE-D_RESOLVE_STATS_DELEGATION_TO_QUERY_KERNEL`

## Phase
`Phase 2 — Query Engine ownership completion`

## Objective
Route only the manifest-approved covered `resolve_stats()` families through the query kernel while preserving the public compatibility entrypoint and an explicit fallback path for undelegated or non-covered families.

## Scope in
- internal `resolve_stats()` delegation routing
- delegation only for declared manifest-approved covered families
- explicit fallback preservation for undelegated families and non-covered outputs
- public compatibility entrypoint preservation
- no-false-implication review of partial delegation coverage

## Scope out
- new family coverage beyond the Phase 2C manifest
- formula rewrites
- benchmark closure work beyond routing-proof checks
- simulator or optimiser changes

## Required outputs
- explicit query-kernel delegation path for approved families
- explicit fallback path for undelegated families
- preserved public compatibility entrypoint
- verification that routing does not imply full delegation

## Required verification
- declared covered families delegate only when the compatibility entrypoint can identify them without guessing
- undelegated families still resolve through the explicit fallback owner
- public `engine.stat_engine.resolve_stats` entrypoint remains intact
- no doc or diagnostic language implies repo-wide full delegation

## Acceptance criteria
- internal routing delegates only governed, manifest-approved families
- undelegated and ambiguous requests remain on the explicit compatibility fallback path
- public entrypoint signature and import surface remain preserved
- tests prove both delegated routing and undelegated fallback behavior

## Blockers
- none

## Stop conditions
Stop once the compatibility entrypoint delegates only the governed, detectable family subset, preserves explicit fallback behavior for everything else, and targeted verification covers the bounded routing truth.

## Non-goals
- do not expand the covered-family manifest
- do not treat ambiguous family identification as delegated proof
- do not claim Phase 2E parity or benchmark completion
