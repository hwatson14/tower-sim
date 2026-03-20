# R75 Merge Integration and Acceptance Plan

## Purpose
This pack is the recommended next step after R74 consolidation.

The guarded incremental runtime line is now at a good architectural stop point. The next task is not more DAG breadth. The next task is to merge the verified line safely into the active calculator branch and prove that:

1. existing calculator outputs are not regressed
2. the guarded modes still pass their own tests
3. the benchmark-backed speed wins still hold on the merged tree
4. no one reintroduces stat-engine override logic

## Recommended merge order
Apply patches in this order:

1. R59 rebased guarded runtime baseline
2. R60 no-override stat-engine correction
3. R61 canonical subset expansion: defense, thorns, orb speed
4. R62 canonical subset verification: free upgrades and skips
5. R63 runtime-consumer registry for skip paths
6. R64 runtime-consumer guarded diagnostics
7. R65 guarded runtime-output publication for skip paths
8. R66 targeted probe mode
9. R67 cached complete-statbook mode
10. R68 strong cache fingerprint guard
11. R69 benchmark tranche
12. R70 cost-attribution instrumentation
13. R71 subset-executor optimisation
14. R72 overlay/publication optimisation
15. R73 free-attack path verification and benchmark extension
16. R74 consolidation and stop point

Do not merge pre-R59 artifacts as the live base. R59 is the correct rebase point onto the current bug-fixed source package.

## Merge guardrails
- Treat `tower_stat_calc_r54_routed_repairs.zip` as the active source baseline.
- Do not add new stat-engine override logic.
- Do not broaden publishable coverage unless a path is already contract-closed and test-backed.
- Do not weaken cache fingerprint requirements to improve speed.
- Do not claim global speed improvement from the local benchmarked subset.
- If any merge conflict forces a choice between old docs and current calculator behavior, prefer current package behavior.

## Acceptance gates
The merge is only acceptable if all of the following pass.

### Gate 1: core guarded line tests
Run:

```bash
pytest -q \
  tests/test_incremental_subset_executor.py \
  tests/test_incremental_overlay_publisher.py \
  tests/test_incremental_cache_validator.py \
  tests/test_incremental_cache_fingerprint.py \
  tests/test_runtime_consumer_executor.py \
  tests/test_runtime_consumer_registry.py \
  tests/test_progression_recalc_bridge.py \
  tests/test_no_canonical_stat_engine_overrides.py
```

Expected result: pass.

### Gate 2: no-override rule
Verify there is no dependency on post-resolution override logic in the stat engine core for the guarded subset paths.

Practical check:
- `tests/test_no_canonical_stat_engine_overrides.py` passes
- no new override branch is introduced during merge conflict resolution

### Gate 3: benchmark rerun
Run:

```bash
python benchmarks/incremental_closed_subset_benchmark.py
```

Expected interpretation:
- `incremental_targeted_probe_guarded` faster than `full_safe` on the benchmarked subset
- `incremental_cached_publish_guarded` faster than `full_safe` on the benchmarked subset

Do not require exact timing equality with prior numbers. Require directional preservation.

### Gate 4: existing calculator sanity
Run the existing calculator/statbook path used by the repo on the merged tree and confirm no obvious regression in baseline output generation.

At minimum:
- statbook still emits successfully
- guarded modes still emit diagnostics
- cached mode still fails closed when cache identity is missing or mismatched

## Recommended stop point after merge
Stop after the guarded line is merged and accepted unless one of these is true:

1. a specific downstream consumer needs another closed surface
2. the merged benchmark regresses materially and needs repair
3. a production integration requires stronger cache/state identity than the current fingerprint

If none of those are true, broadening the DAG line further is likely lower value than other simulator work.

## What not to do next
- do not start a new 10+ tranche expansion run by default
- do not try to make every runtime surface incremental
- do not treat unbenchmarked coverage growth as progress
- do not replace the stat engine with a generic graph evaluator

## Recommended next workstreams after merge
1. integrate the guarded modes into the progression/search consumers that can actually exploit them
2. add one thin caller-level convenience wrapper for probe vs cached guarded modes
3. only then consider promoting one more surface family if a real caller needs it

## Merge AI notes
- prefer mechanical merge over reinterpretation
- preserve test additions and benchmark artifacts
- if benchmark artifacts conflict, regenerate them from the merged tree rather than hand-editing
- preserve the consolidation doc because it defines the current verified scope and stop point
