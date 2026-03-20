# R77 Progression Engine Repair on R76

## Purpose
Repair and complete the progression engine on top of the merged `r76` stat-engine-refactor/runtime base.

## What changed

### 1. Restored progression-truth skip policy
- File: `engine/wave_progression_policy.py`
- Removed effective warmup behavior from attack/health skip application.
- `warmup_waves` remains only as a compatibility field and is ignored.
- Attack/health wave progression now uses exact current-wave deterministic skip carry.

### 2. Restored sparse enemy-table interpolation
- File: `engine/boss_wave_engine.py`
- Enemy damage/health lookup now interpolates between sparse table rows.
- Out-of-range lookups clamp to the nearest available bound.

### 3. Restored BHD-conditional Range handling for free upgrades
- Files:
  - `engine/free_upgrade_generation_policy.py`
  - `engine/boss_wave_engine.py`
- `Range` is no longer globally excluded.
- It is excluded only when `capability::capability.uw.black_hole.disable_ranged` is active.

### 4. Recovered grouped progression execution
- File: `engine/boss_wave_engine.py`
- Added `run_many(...)`.
- Configs are grouped by progression-affecting signature.
- Shared progression snapshots are built once per compatible group.

### 5. Recovered streamed perk application in progression path
- File: `engine/boss_wave_engine.py`
- Progression snapshot builder now streams perk events by wave rather than recomputing counts from scratch each loop.

### 6. Recovered progression snapshot ownership
- File: `engine/boss_wave_engine.py`
- Progression mutation loop is now separated from row evaluation.
- Boss-wave output rows are evaluated from progression snapshots, which keeps progression semantics explicit and reusable.

## Tests added/updated
- `tests/test_wave_progression_policy.py`
- `tests/test_free_upgrade_generation_policy.py`
- `tests/test_progression_accuracy_merge.py`

## Verification
Progression-focused verification pack passed:
- `tests/test_wave_progression_policy.py`
- `tests/test_free_upgrade_generation_policy.py`
- `tests/test_progression_accuracy_merge.py`
- `tests/test_progression_state.py`
- `tests/test_workshop_progression_policy.py`
- `tests/test_perk_timeline_state.py`
- `tests/test_progression_recalc_bridge.py`
- `tests/test_no_canonical_stat_engine_overrides.py`
- `tests/test_boss_wave_engine_scaffold.py`

Result:
- 36 passed

## Scope boundary
This artifact restores and completes the progression engine on the current merged base.
It does not claim final combat/runtime truth closure outside the progression boundary.
