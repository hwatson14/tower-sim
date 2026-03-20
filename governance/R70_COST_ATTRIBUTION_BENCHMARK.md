# R70 Cost Attribution Benchmark

## Objective
Measure where time is actually spent in the current guarded recompute modes, using bridge-level phase timings rather than only outer wall-clock timings.

## Source baseline
- Authoritative calculator baseline: `tower_stat_calc_r54_routed_repairs`
- DAG/incremental line: R59-R69 merged into working tree before this tranche
- No stat-engine overrides allowed

## What this tranche adds
- Bridge phase timing instrumentation in `engine/progression_recalc_bridge.py`
- Phase-aware benchmark output in `benchmarks/incremental_closed_subset_benchmark.py`
- CSV/JSON benchmark artifacts under `out/benchmarks/`

## Measured phases
The bridge now records `incremental_diagnostics.phase_timing_ms` with the following possible keys:
- `apply_workshop_overrides`
- `apply_perk_counts_override`
- `compile_stat_inputs`
- `plan_from_workshop_overrides`
- `build_cache_fingerprint`
- `execute_candidate_subset`
- `validate_cached_reference`
- `publish_overlay`
- `resolve_stats`
- `compare_parity`
- `execute_runtime_publication`
- `total_measured_ms`

## Benchmark scope
Scenarios:
- `health_canonical`
- `eals_runtime`

Modes:
- `full_safe`
- `incremental_targeted_probe_guarded`
- `incremental_cached_publish_guarded`

## Result summary
### Outer wall-clock result
- `incremental_targeted_probe_guarded` is only modestly faster than `full_safe`
- `incremental_cached_publish_guarded` is slower than `full_safe`

### Cost attribution result
The largest remaining cost on both incremental modes is not cache validation or fingerprinting.
It is `execute_candidate_subset` itself.

Observed pattern from benchmark output:
- `resolve_stats` in `full_safe`: roughly 71-73 ms
- `execute_candidate_subset` in incremental modes: roughly 62-66 ms
- `publish_overlay` in cached mode: roughly 18-20 ms extra
- `compile_stat_inputs` and `build_cache_fingerprint`: small but non-trivial, usually ~4-6 ms each
- `validate_cached_reference`: negligible

## Conclusion
The current bottleneck is the subset executor, not cache validation.
That means the next optimisation tranche should inspect why `IncrementalSubsetExecutor` is still so expensive relative to `resolve_stats`.

## Immediate recommendation
Do not expand coverage yet.
Instead:
1. profile `IncrementalSubsetExecutor`
2. identify repeated work inside subset execution
3. remove per-call loading / grouping / sorting costs where possible
4. rerun the same benchmark before making further architecture changes
