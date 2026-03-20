# R70 Cost Attribution Results

## Mean outer timings (ms)
| Scenario | full_safe | targeted_probe | cached_publish |
|---|---:|---:|---:|
| health_canonical | 85.355 | 84.610 | 101.262 |
| eals_runtime | 88.959 | 78.642 | 100.375 |

## Relative result
| Scenario | Mode | Speedup vs full_safe | Mean ms saved |
|---|---|---:|---:|
| health_canonical | incremental_targeted_probe_guarded | 1.009x | 0.745 |
| health_canonical | incremental_cached_publish_guarded | 0.843x | -15.907 |
| eals_runtime | incremental_targeted_probe_guarded | 1.131x | 10.317 |
| eals_runtime | incremental_cached_publish_guarded | 0.886x | -11.416 |

## Dominant phase costs
### health_canonical
- `full_safe.resolve_stats`: 70.950 ms
- `targeted_probe.execute_candidate_subset`: 65.930 ms
- `cached_publish.execute_candidate_subset`: 64.635 ms
- `cached_publish.publish_overlay`: 19.912 ms

### eals_runtime
- `full_safe.resolve_stats`: 72.562 ms
- `targeted_probe.execute_candidate_subset`: 62.067 ms
- `cached_publish.execute_candidate_subset`: 64.600 ms
- `cached_publish.publish_overlay`: 18.561 ms

## Interpretation
1. The subset executor is still expensive enough that skipping `resolve_stats` only gives a modest gain.
2. Cached complete-statbook mode currently loses because overlay cost adds materially on top of subset execution.
3. Cache validation and fingerprinting are not the main problem.
4. The optimisation target should shift from cache mechanics to subset executor mechanics.

## Recommended next tranche
Profile and optimise `IncrementalSubsetExecutor` internals before expanding any more surface area.
