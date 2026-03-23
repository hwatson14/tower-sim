# ACTIVE_TRANCHE

## Tranche ID
`PH3-TRANCHE-F_OBJECTIVE_SURFACE_VALIDATION_AND_PARITY_CLOSEOUT`

## Phase
`Phase 3 — Objective-state promotion`

## Objective
Validate and close out the promoted Query Engine-owned derived objective surfaces for eHP, eDamage, eEcon, and persistent income publication after integrating the reviewed Phase 3 merge-candidate bundle.

## Change classification
- **Routing correction**: optimizer now consumes governed derived objective surfaces instead of re-deriving local objective formulas.
- **Output correction**: Phase 3 query-owned derived surfaces and persistent-income publications are now emitted into the resolved statbook flow.
- **Test correction**: targeted Phase 3 regression coverage now validates the publication/consumption contract that survived review.

## Scope in
- validation of the integrated `derived::ehp`, `derived::edamage`, and `derived::eecon` publication path
- validation of persistent income publication boundaries under `derived::economy.income.*`
- confirmation that optimizer consumption is fail-closed and query-owned
- documentation of the remaining Phase 3 gaps after bundle review

## Scope out
- simulator or evaluator implementation
- workbook-wide parity certification beyond targeted tranche evidence
- new guessed mechanics or unsupported income models

## Required outputs
- reviewed Phase 3 publication/consumption code path
- updated query contracts and ownership ledgers for derived objective surfaces
- bounded manual-income input lane for externalized persistent resources
- explicit note that Phase 3 is not yet complete until broader validation/parity closes

## Required verification
- targeted publication/contract/optimizer tests pass
- `python run_stats.py` succeeds with the Phase 3 publication hook enabled
- full `pytest` is re-run to check for regressions caused by the integration

## Acceptance criteria
- optimizer no longer owns canonical eHP/eDamage/eEcon formulas
- derived objective and income surfaces are declared once in the governed query contracts
- remaining open Phase 3 work is stated explicitly rather than implied complete

## Current status
- Reviewed merge-candidate code was integrated selectively: publication modules, derived contracts, income contracts, optimizer consumption, and targeted tests landed.
- Runtime validation now confirms `run_stats.py` emits the governed derived objective surfaces and the deterministic coin-income proxy surface.
- Phase 3 is **not complete yet**. Remaining work is broader parity / accepted-model evidence closure for the promoted surfaces plus any remaining full-suite regression cleanup needed outside this tranche.
