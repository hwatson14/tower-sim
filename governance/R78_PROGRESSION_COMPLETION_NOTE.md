# R78 Progression Engine Completion Note

## Purpose
This artifact repairs and completes the progression engine on top of the merged `r76` refactored branch.

It is intended to be the new progression-engine merge candidate.

## Scope boundary
This tranche completes the progression engine within the accepted progression scope:
- exact attack/health wave progression
- interpolated enemy table lookup
- deterministic same-wave free-upgrade generation with BHD-gated `Range`
- grouped multi-config progression execution
- dirty-state progression recompute
- streamed perk application
- scenario-owned progression inputs consumed by progression:
  - boss cadence interval
  - enemy level skip reduction

It does **not** claim full combat/runtime truth closure beyond the existing scaffold/runtime boundary.

## Key fixes beyond r77
1. Restored progression-affecting grouping semantics instead of grouping by raw query bounds.
2. Restored dirty-state recompute so progression no longer forces full recompute every wave when nothing changed.
3. Restored scenario-owned progression inputs into the progression path:
   - `boss_wave_interval`
   - `enemy_level_skip_reduction_pp`
4. Restored grouped fanout to max end-wave within each progression-equivalent group.
5. Added regression tests for:
   - grouping split when skip reduction differs
   - scenario-owned boss cadence
   - dirty-state recompute when progression state is unchanged

## Files changed
- `engine/boss_wave_engine.py`
- `engine/scenario_runtime_inputs.py`
- `tests/test_progression_accuracy_merge.py`

## Verification
Progression-focused regression pack:
- `tests/test_wave_progression_policy.py`
- `tests/test_free_upgrade_generation_policy.py`
- `tests/test_progression_accuracy_merge.py`
- `tests/test_progression_state.py`
- `tests/test_workshop_progression_policy.py`
- `tests/test_perk_timeline_state.py`
- `tests/test_progression_recalc_bridge.py`
- `tests/test_no_canonical_stat_engine_overrides.py`
- `tests/test_boss_wave_engine_scaffold.py`

Status:
- 39 progression-focused tests passed in local verification

Manual spot checks:
- scenario-owned boss cadence override produces `[10, 15, 20]` for 10..20 with interval 5
- grouped multi-tier `run_many(...)` shares a single progression group for equivalent Tier 12 / Tier 13 farming configs

## Merge intent
Use this artifact as the progression-engine merge candidate on top of the current refactored branch lineage.

Next workstream after merge should be named:
**combat/runtime truth closure**
