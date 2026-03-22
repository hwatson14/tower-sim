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

## Blockers
- none

## Stop conditions
Stop once every manifest row has current evidence status, delegated-family benchmark scope is recorded, and the bounded Phase 2 proof surface is ready for phase-gate review.

## Non-goals
- do not widen covered-family scope
- do not treat fallback-owned rows as delegated proof
- do not rewrite formulas while collecting parity/benchmark evidence
