# R65 Runtime Output Publication for Skip Paths

## Purpose
Promote the two already-closed skip-driven runtime consumers from diagnostic-only invalidation to guarded runtime-output publication.

## Scope
In scope:
- `runtime_consumer::wave_progression.attack_wave`
- `runtime_consumer::wave_progression.health_wave`
- guarded publication only when `runtime_target_display_wave` is explicitly provided on the bridge request
- exact comparison against the full-safe reference statbook-derived runtime outputs

Out of scope:
- broader runtime publication
- removal of full-safe reference precompute
- performance claims
- any runtime consumer not already explicitly registered

## Package evidence
This tranche relies on existing package evidence already closed in prior tranches:
- `docs/10_workshop_dependency_ledger.md`
- `engine/wave_progression_policy.py`
- `engine/boss_wave_engine.py`
- `engine/runtime_consumer_registry.py`

## Implementation
Added:
- `engine/runtime_consumer_executor.py`

Modified:
- `engine/progression_recalc_bridge.py`
- `tests/test_progression_recalc_bridge.py`
- added `tests/test_runtime_consumer_executor.py`

## Behavior
If `runtime_target_display_wave` is omitted:
- no runtime outputs are published

If `runtime_target_display_wave` is supplied and the plan has impacted runtime consumers:
- `full_safe` publishes runtime outputs from the full-safe reference
- `incremental_parity_guarded` publishes runtime outputs from the full-safe reference
- `incremental_publish_guarded` publishes runtime outputs only after candidate-overlay parity passes, and records both published and reference outputs in diagnostics

## Safety rule
Runtime publication remains fail-closed:
- only registered runtime consumers are eligible
- only skip-driven wave outputs are supported
- publication occurs only from a complete statbook path
- `incremental_publish_guarded` records `runtime_publication.status = pass|mismatch`

## Verification
Targeted tests:
- `tests/test_runtime_consumer_executor.py`
- `tests/test_progression_recalc_bridge.py`
- retained DAG/bridge regression suite

Expected result on this tranche:
- runtime outputs present for skip-driven guarded publication when `runtime_target_display_wave` is provided
- no runtime outputs for non-runtime health path
