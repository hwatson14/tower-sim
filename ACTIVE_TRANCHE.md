# ACTIVE_TRANCHE

## Tranche ID
`PH2-TRANCHE-E_COVERED_FAMILY_PARITY_AND_BENCHMARK_EVIDENCE`

## Phase
`Phase 2 — Query Engine ownership completion`

## Objective
Prove the bounded delegated path with family-scoped parity and benchmark evidence without implying repo-wide Query Engine ownership beyond the governed Phase 2C/2D family boundary.

## Scope in
- parity evidence for declared covered families
- benchmark evidence for delegated workloads
- explicit pass, fail, or open status by family and surface
- visibility of remaining open failures or blocked evidence

## Scope out
- new family coverage beyond the manifest
- new routing semantics beyond the landed Phase 2D delegation path
- formula rewrites
- simulator or optimiser changes

## Required outputs
- parity matrix by family and surface
- benchmark evidence for delegated workloads
- explicit pass, fail, blocked, or open status records

## Required verification
- every manifest family keeps a visible evidence status
- delegated families have bounded parity/benchmark evidence attached to the approved surface set
- open failures remain visible and bounded
- no evidence artifact implies full `resolve_stats()` delegation outside the governed family set

## Acceptance criteria
- declared delegated families have parity and benchmark evidence records
- undelegated rows remain visibly outside delegated-proof claims
- any remaining mismatch or missing proof is explicit, bounded, and assigned status
- Phase 2 exit evidence can be read directly from governed repo surfaces
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
Stop once every manifest row has current evidence status, delegated-family benchmark scope is recorded, and the bounded Phase 2 proof surface is ready for phase-gate review.

## Non-goals
- do not widen covered-family scope
- do not treat fallback-owned rows as delegated proof
- do not rewrite formulas while collecting parity/benchmark evidence
Stop once the compatibility entrypoint delegates only the governed, detectable family subset, preserves explicit fallback behavior for everything else, and targeted verification covers the bounded routing truth.

## Non-goals
- do not expand the covered-family manifest
- do not treat ambiguous family identification as delegated proof
- do not claim Phase 2E parity or benchmark completion
