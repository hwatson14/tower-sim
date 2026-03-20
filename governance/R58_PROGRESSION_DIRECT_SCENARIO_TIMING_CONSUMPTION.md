# R58 — Progression direct consumption of scenario and timing engines

## Objective
Make progression consume the split engine owners directly, rather than relying on stat-row fallbacks that bypass the new ownership boundary.

## What changed
- `engine/boss_wave_engine.py` now builds a per-recompute runtime context using:
  - `engine.scenario_engine.config_from_statbook(...)`
  - `engine.scenario_engine.compute_scenario_surfaces(...)`
  - `engine.timing_engine.compute_timing_surfaces(...)`
- Boss hit interval fallback now comes from `scenario_engine` before external runtime-input fallbacks.
- Damage-intake fallback now uses `timing_engine` over the resolved encounter interval to derive average Chrono Field damage reduction when no governed combat DR surface or explicit override is present.

## Ownership after this patch
- `scenario_engine`
  - world/scenario surfaces
  - boss cadence / hit interval
  - BC and environment effects
- `timing_engine`
  - temporal mechanic surfaces
  - interval-active evaluation
  - encounter-average timed damage reduction
- `boss_wave_engine`
  - progression-state evolution and encounter simulation
  - consumes scenario/timing outputs instead of recreating them

## Scope limits
- Orb/electron cadence and boss contact timing remain external/governed runtime surfaces or explicit overrides.
- Flame Bot DR timing is still excluded from encounter DR because activation/persistence timing is not yet contract-defined in the timing engine.
- Progression still does not own phase scheduling; timing defaults remain zero-phase unless/ until scenario/runtime contracts add phase inputs.

## Verification
Targeted tests passed:
- `tests/test_timing_engine.py`
- `tests/test_boss_wave_engine_scaffold.py`
- `tests/test_scenario_timing_split.py`
- `tests/test_scenario_runtime_inputs.py`
- `tests/test_wave_progression_policy.py`
- `tests/test_progression_recalc_bridge.py`
- `tests/test_workshop_progression_policy.py`
