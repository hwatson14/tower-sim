# Codex Current Brief

## Objective
Implement the **runtime overlay foundation** on top of the existing static staged architecture.

This is **not** full runtime simulation.
This is **not** combat resolution.
This is **not** evaluator work.

## Required architecture constraints
Preserve the explicit separation between:
- `baseline_account`
- `baseline_gem_respec`
- `baseline_loadout`
- `runtime_overlay`

Do not collapse runtime overlays into static stage outputs.

## Inspect first
Before editing, inspect:
- `docs/v2/TOWERSIM_V2_MASTER_SPEC.md`
- `tables/meta/registry/v2/stages.yaml`
- `tower_sim/registry/static_v2_contract.py`
- `tower_sim/engines/static_pipeline_v2.py`
- existing perk / battle condition / workshop progression / free-upgrade / EALS/EHLS surfaces
- `tests/test_static_pipeline_v2.py`
- tests related to perks, battle conditions, workshop progression, free upgrades, or skips

## In scope
Implement the minimum runtime overlay materialization layer for:
- perks
- battle_conditions
- cash_workshop_purchases / workshop runtime progression
- free_upgrades
- eals_realized_effect
- ehls_realized_effect

## Required tasks
1. Add the minimum runtime overlay materialization layer after static staged outputs.
2. Keep runtime overlays explicitly separate from static stages.
3. Reuse existing repo-native structures where possible.
4. Add tests proving:
   - static stages remain deterministic and unchanged before overlays
   - overlay families are materialized separately
   - overlay application order is explicit and validated
   - missing/incompatible overlay data fails closed

## Out of scope
- combat engine implementation
- boss-state execution
- evaluator rewrites
- broad registry redesign
- KB import work
- deleting large legacy areas
- unrelated refactors

## Files likely allowed to change
- `tables/meta/registry/v2/stages.yaml`
- `tower_sim/registry/static_v2_contract.py`
- `tower_sim/engines/static_pipeline_v2.py`
- relevant existing runtime/progression support files if strictly necessary
- relevant tests only

## Files not to change unless absolutely required
- evaluator code
- combat engine code
- broad KB contents
- unrelated loader/compiler logic
- top-level governance docs unrelated to this phase

## Output required from Codex
Return only:
1. exact files changed
2. how runtime overlays are exposed/materialized
3. exact tests run and results
4. remaining gaps before combat/runtime-state implementation

## Stop conditions
Stop and report instead of improvising if:
- runtime overlay families cannot be routed cleanly through existing repo-native structures
- implementing this would require evaluator rewrites
- implementing this would require a parallel staged pipeline
- stage/overlay naming becomes ambiguous or conflicts with active contracts
