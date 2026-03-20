# R60 Remove stat-engine override dependence and enforce explicit dependency order

Decision:
- Removed the incremental subset executor's dependence on stat-engine phase-3 postprocessing.
- Moved derived/helper surface composition out of the stat engine core into `engine/derived_surface_composer.py`.
- Converted the following stat surfaces to direct resolver formulas inside `_resolve_bucket(...)`:
  - `canonical_stat::free_attack_upgrade_chance_pct`
  - `canonical_stat::free_defense_upgrade_chance_pct`
  - `canonical_stat::free_utility_upgrade_chance_pct`
  - `canonical_stat::max_rend_mult`
  - `canonical_stat::wall_regen`
  - `canonical_stat::package_chance_pct`
- Replaced implicit bucket iteration order with explicit dependency-aware ordering for cross-stat resolver dependencies:
  - `tower_hp -> wall_hp`
  - `tower_regen -> wall_regen`
  - `free_upgrade_multiplier -> free_*_upgrade_chance_pct`

Reason:
- No override or postprocessing dependence is allowed in the stat engine core.
- The previous design required phase-3 mutation after bucket resolution to get correct values for free upgrades, wall regen, package chance, and max rend.
- That was structurally wrong for incremental execution because subset resolution could not be correct without replaying opaque postprocessing.

What remains outside the stat engine core:
- `canonical_stat::coin_kill_multiplier` transition mirror
- `canonical_stat::all_coin_bonus_multiplier` derived display surface

These are now composed in `engine/derived_surface_composer.py` from already-resolved rows and no longer mutate canonical bucket outputs inside the stat engine resolver.

Verification:
- `tests/test_perk_scaling.py::test_free_upgrades_card_is_split_into_canonical_free_upgrade_stats_and_values_match_ep_baseline`
- `tests/test_perk_scaling.py::test_max_rend_mult_exact_formula_uses_enhancement_base_cap_lab_and_module_substat`
- `tests/test_perk_scaling.py::test_all_coin_bonus_multiplier_uses_farming_tier_and_numeric_pack_multipliers`
- `tests/test_progression_recalc_bridge.py`
- `tests/test_incremental_subset_executor.py`

Result:
- 9 passed
