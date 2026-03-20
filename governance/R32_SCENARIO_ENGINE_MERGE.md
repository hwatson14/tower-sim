# R32 Scenario-Invariant Engine Merge

## What was merged
- `engine/scenario_invariant_engine.py` — 46-surface scenario-adjusted effects engine
- `tests/test_scenario_invariant.py` — 59 tests, all passing

## Purpose
Sits between the stat engine (permanent stats) and the progression engine (wave-by-wave simulation).
Computes all fixed-for-run scenario-adjusted surfaces: BC penalties with lab reduction,
boss cadence/resistances, UW/bot uptimes after BC duration penalties and perks,
CF damage reduction, and environment overlays.

## Fixes applied during merge (3)

### Fix 1: Stale bridge test (test_bridge_from_actual_statbook)
- Old assertions expected R27 values: `tower_orb_count=6`, `cf_damage_reduction_pct=30.0`
- R32 stat engine emits: `tower_orb_count=8` (perk Orbs+1 fix), `cf_damage_reduction_pct=20.0`
- Updated test to R32 baseline values

### Fix 2: CF damage reduction auto-read from stat engine
- R32 semantics closure (R32_GT_BONUS_AND_CF_REDUCTION_SEMANTICS.md) resolved
  `mechanic_param::uw.chrono_field.damage_reduction_pct` as a stat engine surface
- `config_from_statbook()` now auto-reads this surface when the caller does not
  provide an explicit `cf_damage_reduction_pct` override
- Parameter changed from `float = 0.0` to `Optional[float] = None` to distinguish
  "no override" from "explicitly set to zero"
- `compute_cf_damage_reduction_pct()` helper retained for validation and fallback

### Fix 3: KB loader caching
- Added `@lru_cache(maxsize=1)` to `_load_tier_battle_conditions()`,
  `_load_tournament_bc_magnitudes()`, and `_load_boss_enemy_class_resistances()`
- Matches the caching pattern used throughout `compilers/stat_input_compiler.py`

## R27_REQUIRED_UPDATES status under R32

| Item | Status |
|------|--------|
| A1: tower_orb_count perk silently dropped | **Resolved in R32** — perk branch present in orb_count resolver |
| A2: count_add SPB creates fractional counts | **Resolved in R32** — `integrality_policy` column in perk-effect-registry.csv, code checks it |
| A3: tower_bounce_shot_targets fractional | **Resolved in R32** — `integer_count_stat` resolver rounds at line 883 |
| B1: CF damage reduction not emitted | **Resolved in R32** — `mechanic_param::uw.chrono_field.damage_reduction_pct = 20.0` |
| B2: BC reduction lab levels not emitted | **Open** — Stream 2 route-now work, scenario engine workaround is correct |
| C1: perk-entity-registry missing columns | **Resolved in R32** — columns present in `perk-effect-registry.csv` |
| C2: No bc-group-membership.csv | **Open** — nice-to-have, engine hardcodes group membership correctly |

## Test results
- 59/59 scenario engine tests passing
- 11/11 key smoke tests passing
- 2/2 R32 semantics tests passing
- Full pipeline rebuild: clean
