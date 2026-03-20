# R72 Overlay / Publication Optimisation

## Objective
Reduce cached complete-statbook publication overhead after R71 moved subset execution cost out of the way.

## Source basis
- Baseline calculator: `tower_stat_calc_r54_routed_repairs`
- Current guarded incremental line through R71
- No stat-engine overrides allowed

## Changes
1. Optimised `IncrementalOverlayPublisher.publish(...)` to use structural sharing for unchanged rows instead of deep-copying the full reference statbook.
2. Preserved diagnostics isolation by copying the diagnostics dict before writing overlay metadata.
3. Fixed two regressions in the working line discovered while taking this tranche:
   - restored `IncrementalPlan.to_dict()` and `runtime_consumer_ids` emission in `engine/incremental_recalc_runtime.py`
   - restored selective contributor serialization for `canonical_stat::free_upgrade_multiplier` in `engine/incremental_subset_executor.py`, because downstream free-upgrade formulas read `support_row.contributors` directly

## Safety contract
- Cached reference statbooks must be treated as immutable by callers.
- Unchanged rows are structurally shared with the cached reference in cached publish mode.
- Candidate rows remain freshly computed rows.
- Diagnostics are copied and the reference diagnostics are not mutated.

## Verification
- `pytest -q tests/test_incremental_subset_executor.py tests/test_incremental_overlay_publisher.py tests/test_progression_recalc_bridge.py tests/test_no_canonical_stat_engine_overrides.py`
- 28 passed
- Benchmark rerun completed with fresh JSON/CSV outputs under `out/benchmarks/`

## Outcome
Cached complete-statbook publication is now materially faster and close to probe-mode speed on the benchmarked closed subset.
