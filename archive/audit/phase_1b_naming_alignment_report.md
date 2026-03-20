# Phase 1B Naming Alignment Report

## Scope
- Analysis-only audit of naming alignment between Tier-1 ledger contract and repository identifiers in `tower_sim/engines`, `tower_sim/loaders`, `tower_sim/audit`, `tower_sim/run`.
- No runtime/compiler code or naming changes performed.

## Canonical extraction from Tier-1 ledger
- Ledger rows: 479
- Canonical `target_stat` count: 293
- Canonical `contributor_id` count: 479
- Contributor families (14): battle_condition, bot, card, enhancement, guardian, lab, module_main, module_sub, module_unique, perk, relic, uw, uw_plus, workshop
- Semantic types (22): angle_degrees, base, bonus, chance, chance_bonus, cooldown_seconds, cooldown_seconds_reduction, count, count_bonus, duration_seconds, duration_seconds_bonus, enabled, interval_seconds, interval_seconds_reduction, multiplier, pct, pct_bonus, range_m, range_m_bonus, ratio, rotation_rate, scalar_bonus
- Operations (25): add, add_chance, add_count, add_duration_seconds, add_pct, add_range_m, add_scalar, apply_ratio, enable, multiply, reduce_cooldown_seconds, reduce_interval_seconds, review_required, set_angle_degrees, set_base, set_chance, set_cooldown_seconds, set_count, set_duration_seconds, set_enabled, set_interval_seconds, set_multiplier, set_pct, set_range_m, set_rotation_rate

## Repository identifier scan
- Python files scanned: 80
- Candidate underscore tokens in string literals: 871
- Exact `target_stat` matches in repo strings: 22
- Exact `contributor_id` matches in repo strings: 0

## Mapping table (sampled high-signal mismatches and alignments)
| repo_name | ledger_name | semantic_match_confidence | required_action |
|---|---|---|---|
| `wall_regen` | `wall_regen` | high | keep (already aligned) |
| `attack_speed` | `attack_speed` | high | keep (already aligned) |
| `health_regen` | `health_regen` | high | keep (already aligned) |
| `super_crit_chance` | `super_crit_chance` | high | keep (already aligned) |
| `defense_absolute` | `defense_absolute` | high | keep (already aligned) |
| `wall_health` | `wall_health` | high | keep (already aligned) |
| `defense_pct` | `defense_pct` | high | keep (already aligned) |
| `damage_per_meter` | `damage_per_meter` | high | keep (already aligned) |
| `orb_speed` | `orb_speed` | high | keep (already aligned) |
| `critical_chance` | `critical_chance` | high | keep (already aligned) |
| `chain_lightning_chance` | `chain_lightning_chance` | high | keep (already aligned) |
| `chain_lightning_quantity` | `chain_lightning_quantity` | high | keep (already aligned) |
| `inner_land_mines_quantity` | `inner_land_mines_quantity` | high | keep (already aligned) |
| `smart_missiles_quantity` | `smart_missiles_quantity` | high | keep (already aligned) |
| `super_crit_multiplier` | `super_crit_multiplier` | high | keep (already aligned) |
| `bounce_shot_chance` | `bounce_shot_chance` | high | keep (already aligned) |
| `bounce_shot_targets` | `bounce_shot_targets` | high | keep (already aligned) |
| `coins_per_kill_bonus` | `coins_per_kill_bonus` | high | keep (already aligned) |
| `multishot_chance` | `multishot_chance` | high | keep (already aligned) |
| `multishot_targets` | `multishot_targets` | high | keep (already aligned) |
| `super_crit_mult` | `super_crit_multiplier` | high | evaluate alias normalization in future rename phase |
| `wall_hp` | `—` | low | classify: engine-internal vs missing ledger concept before any rename |
| `tower_regen` | `—` | low | classify: engine-internal vs missing ledger concept before any rename |
| `tower_damage` | `—` | low | classify: engine-internal vs missing ledger concept before any rename |
| `damage_reduction` | `—` | low | classify: engine-internal vs missing ledger concept before any rename |
| `percent_points` | `—` | low | classify: engine-internal vs missing ledger concept before any rename |
| `thorns_damage_mult` | `—` | low | classify: engine-internal vs missing ledger concept before any rename |
| `damage_multiplier` | `—` | low | classify: engine-internal vs missing ledger concept before any rename |
| `tower_attack_speed` | `—` | low | classify: engine-internal vs missing ledger concept before any rename |
| `tower_crit_chance` | `—` | low | classify: engine-internal vs missing ledger concept before any rename |
| `workshop_coins_per_kill_bonus` | `—` | low | classify: engine-internal vs missing ledger concept before any rename |
| `enhancement_multiplier` | `—` | low | classify: engine-internal vs missing ledger concept before any rename |
| `uw_name` | `—` | low | classify: engine-internal vs missing ledger concept before any rename |
| `boss_survivability` | `—` | low | classify: engine-internal vs missing ledger concept before any rename |
| `bot_bonus_multiplier` | `—` | low | classify: engine-internal vs missing ledger concept before any rename |
| `bot_range` | `—` | low | classify: engine-internal vs missing ledger concept before any rename |
| `labs_values_v1` | `—` | low | classify: engine-internal vs missing ledger concept before any rename |
| `plasma_cannon_damage_mult` | `—` | low | classify: engine-internal vs missing ledger concept before any rename |
| `duration_s` | `—` | low | classify: engine-internal vs missing ledger concept before any rename |
| `tower_crit_multiplier` | `—` | low | classify: engine-internal vs missing ledger concept before any rename |
| `workshop_wall_health` | `—` | low | classify: engine-internal vs missing ledger concept before any rename |
| `workshop_wall_regen` | `—` | low | classify: engine-internal vs missing ledger concept before any rename |
| `bot_cooldown_multiplier` | `—` | low | classify: engine-internal vs missing ledger concept before any rename |
| `bot_duration_multiplier` | `—` | low | classify: engine-internal vs missing ledger concept before any rename |
| `card_presets` | `—` | low | classify: engine-internal vs missing ledger concept before any rename |
| `coin_multiplier` | `—` | low | classify: engine-internal vs missing ledger concept before any rename |
| `cooldown_s` | `—` | low | classify: engine-internal vs missing ledger concept before any rename |
| `pc_boss_mult` | `—` | low | classify: engine-internal vs missing ledger concept before any rename |
| `super_crit_mult` | `—` | low | classify: engine-internal vs missing ledger concept before any rename |
| `thorns_frac` | `—` | low | classify: engine-internal vs missing ledger concept before any rename |
| `uw_purchase_costs_v1` | `—` | low | classify: engine-internal vs missing ledger concept before any rename |

## Alias collisions / merged-semantics candidates
- `thorns_pct` vs `thorns_percent`: present repo token vs not-in-ledger ledger token (percent suffix normalization).
- `def_abs_pct` vs `defense_absolute_percent`: not-seen repo token vs not-in-ledger ledger token (abbrev + suffix expansion).
- `orb_speed` vs `orb_speed_mps`: present repo token vs not-in-ledger ledger token (unit suffix mismatch).
- `regen` vs `health_regen`: not-seen repo token vs present ledger token (ambiguous base stat label).
- `wall_rebuild` vs `wall_rebuild_time_seconds`: present repo token vs not-in-ledger ledger token (time semantic expansion).

## Stats defined multiple times (string literal presence across files)
| target_stat | file_count | sample_files |
|---|---:|---|
| `attack_speed` | 6 | `tower_sim/engines/edamage_formulas.py`, `tower_sim/engines/edamage_pipeline.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/loaders/ep_export_loader.py` |
| `wall_regen` | 6 | `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/engines/combat/boss_survivability.py`, `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/loaders/ep_export_loader.py` |
| `health_regen` | 5 | `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/loaders/ep_export_loader.py` |
| `super_crit_chance` | 4 | `tower_sim/engines/edamage_pipeline.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/loaders/ep_export_loader.py` |
| `wall_health` | 4 | `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/loaders/ep_export_loader.py` |
| `critical_chance` | 3 | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/engines/survivability_pipeline.py` |
| `damage_per_meter` | 3 | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/loaders/ep_export_loader.py` |
| `defense_absolute` | 3 | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/loaders/ep_export_loader.py` |
| `defense_pct` | 3 | `tower_sim/engines/combat/boss_engine.py`, `tower_sim/engines/combat/boss_survivability.py`, `tower_sim/engines/survivability_pipeline.py` |
| `chain_lightning_chance` | 2 | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` |
| `chain_lightning_quantity` | 2 | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` |
| `inner_land_mines_quantity` | 2 | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` |
| `orb_speed` | 2 | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` |
| `smart_missiles_quantity` | 2 | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` |

## Repo names not found in ledger (focused subset)
`wall_hp`, `tower_regen`, `tower_damage`, `damage_reduction`, `percent_points`, `thorns_damage_mult`, `damage_multiplier`, `tower_attack_speed`, `tower_crit_chance`, `workshop_coins_per_kill_bonus`, `enhancement_multiplier`, `uw_name`, `boss_survivability`, `bot_bonus_multiplier`, `bot_range`, `labs_values_v1`, `plasma_cannon_damage_mult`, `duration_s`, `tower_crit_multiplier`, `workshop_wall_health`, `workshop_wall_regen`, `bot_cooldown_multiplier`, `bot_duration_multiplier`, `card_presets`, `coin_multiplier`, `cooldown_s`, `pc_boss_mult`, `super_crit_mult`, `thorns_frac`, `uw_purchase_costs_v1`, `workshop_free_defense_upgrade`, `workshop_package_chance`, `bot_upgrades`, `card_masteries_v1`, `death_ray_damage_mult`, `defense_percent`, `enemy_attack_wave`, `enemy_health_wave`, `free_defense_upgrade`, `knockback_mult`, `max_wave`, `module_presets`, `module_unique_unmapped`, `more_bosses`, `orb_damage_mult`, `orb_resistance`, `required_max_wave_gap_count`, `required_max_wave_stat_input_ids`, `thorns_resistance`, `uw_plus_ladders_v1`, `uw_track_ladders_v1`, `value_percent_points`, `wave_damage_tier`, `workshop_bounce_shot_chance`, `workshop_multishot_targets`, `workshop_range_meters`, `chain_lightning_damage`, `crit_chance`, `death_wave_damage`, `flame_bot_damage_reduction_multiplier`, `inner_land_mines_damage`, `modules_inventory`, `modules_library`, `percent_string`, `poison_swamp_damage`, `ramp_waves`, `recovery_package_chance`, `skip_ramp`, `smart_missiles_damage`, `wall_rebuild`, `wave_attack_index`, `wave_health_index`, `workshop_land_mine_chance`, `card_id`, `cards_inventory`, `coin_level`, `crit_factor`, `defense_abs`, `electrons_damage_frac`, `extra_defense`

## High-risk rename areas
1. `tower_sim/engines/stat_input_compiler.py` — central static assembly; high blast radius for key names.
2. `tower_sim/engines/stat_pipeline.py` and `tower_sim/engines/combat_stat_derivation.py` — wiring/join points where alias drift can re-enter.
3. `tower_sim/loaders/ids.py` and loader table adapters — upstream field names may be abbreviated and not ledger-normalized.
4. `tower_sim/audit/*` diagnostics surfaces — often mirror historical aliases and can mask unresolved naming drift.

## Smallest-safe migration strategy (no changes in this phase)
1. Freeze canonical naming dictionary derived from `target_stat` + `contributor_id` + contract semantic rules.
2. Build read-only alias map in audit docs only (old_name -> canonical_name) with confidence tags.
3. Prioritize high-confidence exact substitutions in non-runtime audit/report surfaces first.
4. Then apply runtime renames in one pipeline boundary at a time (`stat_input_compiler` -> `stat_pipeline`), with fail-closed checks.
5. Keep contributor IDs immutable unless contract update explicitly authorizes changes.
