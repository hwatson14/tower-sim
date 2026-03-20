# R69 Incremental Benchmark Results

## Environment-local result
Benchmarked on the current container against the guarded closed subset only.

## Scenarios
- `health_canonical`: workshop mutation on `Health`
- `eals_runtime`: workshop mutation on `Enemy Attack Level Skip` with `runtime_target_display_wave=1000`

## Modes
- `full_safe`
- `incremental_targeted_probe_guarded`
- `incremental_cached_publish_guarded`

## Mean timings
| Scenario | full_safe ms | targeted_probe ms | cached_publish ms |
|---|---:|---:|---:|
| health_canonical | 92.144 | 87.273 | 99.931 |
| eals_runtime | 87.725 | 83.369 | 100.472 |

## Interpretation
- `incremental_targeted_probe_guarded` is only modestly faster than `full_safe` here: about 1.05x on both scenarios.
- `incremental_cached_publish_guarded` is slower than `full_safe` here.
- Therefore, the current cached complete-statbook path is **architecturally valid but not yet performance-justified** on this environment.

## Decision implication
The next speed tranche should not widen cached publication coverage. It should instead target the actual remaining overhead sources:
1. repeated `compile_stat_inputs(...)`
2. cache validation and overlay overhead
3. runtime/diagnostic object churn

## Guardrail
These numbers are directional and environment-local. They justify prioritising optimisation work, not claiming production speedups yet.
