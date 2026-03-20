# Phase 1B.1 Stat Surface Inventory

## Files inspected
- `tower_sim/engines`
- `tower_sim/loaders`
- `tower_sim/audit`
- `tower_sim/run`
- `/workspace/tower-sim/tower_sim/models`
- `tower_sim/registry`
- `tables/meta/registry`
- `audit/reference/tower_sim_3_handover/towersim_static_ledger_latest.csv`
- `audit/reference/tower_sim_3_handover/towersim_static_ledger_naming_contract_v1_10.md`
- `audit/reference/tower_sim_3_handover/towersim_v1_handover_pack.md`
- `legacy/governance_handoff/CODEX_HANDOFF_V1_FULL.md`, `legacy/governance_handoff/STATUS_V1.yaml`, `CONTRACT.md`

## 1. Summary counts
- Total unique stat-like identifiers: **633**
- By category:
  - `alias`: 41
  - `derived`: 17
  - `report-only`: 20
  - `runtime`: 69
  - `target_stat`: 23
  - `unknown`: 463
- By stage:
  - `mixed`: 137
  - `report`: 21
  - `runtime`: 112
  - `static`: 363
- Ledger match status:
  - `no`: 610
  - `target_stat`: 23

## 2. Inventory table
| repo_name | category | semantic_role | source_surface (sample) | owner_function(s) | stage | ledger_match | confidence | action |
|---|---|---|---|---|---|---|---:|---|
| `absolute_chance_subtract` | unknown | consumed_identifier | `tower_sim/engines/tier_rule_apply.py` | — | mixed | no | 4 | investigate |
| `assist_mult` | alias | declared_identifier | `tower_sim/engines/econ_current.py` | `EPG_MODULE_BONUS` | mixed | no | 7 | split |
| `assist_multiplier` | unknown | declared_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_armor_module_multiplier` | static | no | 4 | investigate |
| `at_wave` | runtime | declared_identifier | `tower_sim/engines/survivability_pipeline.py`, `tower_sim/registry/stat_registry.py` | `build_survivability_report` | static | no | 7 | classify |
| `at_wave_inputs` | runtime | declared_identifier | `tower_sim/engines/stat_snapshots.py` | `build_at_wave_snapshot` | mixed | no | 7 | classify |
| `at_wave_missing` | runtime | declared_identifier | `tower_sim/engines/stat_pipeline.py` | `build_canonical_stat_pipeline_for_problem_spec` | mixed | no | 7 | classify |
| `at_wave_snapshot` | runtime | declared_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/engines/survivability_pipeline.py` | `build_canonical_stat_pipeline_for_problem_spec`, `build_survivability_report`, `derive_canonical_combat_snapshot` | runtime | no | 7 | classify |
| `at_wave_stage` | runtime | declared_identifier | `tower_sim/engines/stat_pipeline.py` | `build_canonical_stat_pipeline_for_problem_spec` | mixed | no | 7 | classify |
| `at_wave_stage_missing` | runtime | consumed_identifier | `tower_sim/engines/stat_pipeline.py` | `build_canonical_stat_pipeline_for_problem_spec` | mixed | no | 7 | classify |
| `at_wave_stage_skipped` | runtime | emitted_key | `tower_sim/engines/stat_pipeline.py` | `build_canonical_stat_pipeline_for_problem_spec` | mixed | no | 7 | classify |
| `at_wave_stats` | runtime | declared_identifier | `tower_sim/engines/stat_snapshots.py` | `build_at_wave_snapshot` | mixed | no | 7 | classify |
| `attack` | unknown | declared_identifier | `tower_sim/engines/combat/boss_survivability.py`, `tower_sim/engines/combat/combat_engine.py`, `tower_sim/engines/free_upgrades.py`, … | `_free_upgrade_chances`, `_parse_boss_stats`, `_workshop_category` | mixed | no | 4 | investigate |
| `attack_interval` | unknown | declared_identifier | `tower_sim/engines/combat/boss_survivability.py`, `tower_sim/run/problem_spec.py`, `tower_sim/run/spec_loader.py` | `_parse_boss_stats` | runtime | no | 4 | investigate |
| `attack_speed` | target_stat | declared_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/engines/edamage_formulas.py`, … | `_apply_card_effects`, `_compile_relic_stat_inputs`, `build_edamage_stat_inputs` | static | target_stat | 10 | aligned |
| `base_cooldown` | unknown | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `base_cooldown_s` | unknown | consumed_identifier | `tower_sim/engines/uptime.py` | `build_gcomp_activation_intervals` | runtime | no | 4 | investigate |
| `base_duration` | unknown | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `bc_mult` | alias | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | — | static | no | 7 | alias-map |
| `bh_coin_bonus_lvl` | unknown | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `bonus_multiplier` | unknown | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `boss_attack` | unknown | declared_and_emitted | `tower_sim/engines/combat/boss_survivability.py`, `tower_sim/engines/combat_stat_derivation.py` | `resolve_boss_fight`, `validate_boss_survivability_spec` | runtime | no | 4 | investigate |
| `boss_attack_interval` | unknown | emitted_key | `tower_sim/engines/combat_stat_derivation.py` | `validate_boss_survivability_spec` | runtime | no | 4 | investigate |
| `boss_attack_mult` | alias | consumed_identifier | `tower_sim/engines/combat/boss_params_loader.py` | `load_bc_params` | runtime | no | 7 | alias-map |
| `boss_engine` | report-only | consumed_identifier | `tower_sim/audit/status.py`, `tower_sim/engines/combat/__init__.py` | `_components` | runtime | no | 7 | classify |
| `boss_enrage_mult` | alias | emitted_key | `tower_sim/engines/combat_stat_derivation.py` | `validate_boss_survivability_spec` | runtime | no | 7 | alias-map |
| `boss_hit_interval` | unknown | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 4 | investigate |
| `boss_hit_interval_v1` | unknown | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 4 | investigate |
| `boss_hp` | unknown | emitted_key | `tower_sim/engines/combat_stat_derivation.py` | `validate_boss_survivability_spec` | runtime | no | 4 | investigate |
| `boss_hp_frac_damage` | unknown | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | `evaluate` | runtime | no | 4 | investigate |
| `boss_hp_frac_damage_per_hit` | unknown | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | — | runtime | no | 4 | investigate |
| `boss_hp_mult` | alias | consumed_identifier | `tower_sim/engines/combat/boss_params_loader.py` | `load_bc_params` | runtime | no | 7 | alias-map |
| `boss_hp_remaining_mult` | alias | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | `evaluate` | runtime | no | 7 | alias-map |
| `boss_hp_remaining_mult_per_hit` | unknown | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | — | runtime | no | 4 | investigate |
| `boss_interval_waves` | runtime | consumed_identifier | `tower_sim/engines/tier_rule_apply.py` | — | mixed | no | 7 | classify |
| `boss_kills_tower` | unknown | consumed_identifier | `tower_sim/engines/combat/boss_survivability.py` | `resolve_boss_fight` | runtime | no | 4 | investigate |
| `boss_params_loader` | unknown | consumed_identifier | `tower_sim/engines/combat/__init__.py` | — | runtime | no | 4 | investigate |
| `boss_survivability` | report-only | declared_identifier | `tower_sim/audit/status.py`, `tower_sim/engines/combat/__init__.py`, `tower_sim/engines/combat_stat_derivation.py`, … | `_components`, `_parse_boss_survivability`, `_parse_scenario` | runtime | no | 7 | classify |
| `boss_survivability_invalid` | unknown | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | `validate_boss_survivability_spec` | runtime | no | 4 | investigate |
| `boss_wall_thorns_frac_v1` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | — | static | no | 4 | investigate |
| `bot_amplify_bonus` | unknown | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry`, `resolve_runtime_bot_effects` | mixed | no | 4 | investigate |
| `bot_amplify_cooldown` | unknown | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry`, `resolve_runtime_bot_effects` | mixed | no | 4 | investigate |
| `bot_amplify_duration` | unknown | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry`, `resolve_runtime_bot_effects` | mixed | no | 4 | investigate |
| `bot_amplify_range` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `bot_attribute_unmapped` | unknown | consumed_identifier | `tower_sim/registry/naming_contract.py` | `validate_account_snapshot_naming` | static | no | 4 | investigate |
| `bot_attributes` | unknown | consumed_identifier | `tower_sim/registry/naming_contract.py` | `_build_named_entity_maps`, `validate_account_snapshot_naming`, `validate_repo_naming_contract` | static | no | 4 | investigate |
| `bot_bonus_multiplier` | unknown | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | `resolve_runtime_bot_effects` | runtime | no | 4 | investigate |
| `bot_cooldown_multiplier` | unknown | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | `_read_profile_from_snapshot`, `resolve_runtime_bot_effects` | runtime | no | 4 | investigate |
| `bot_duration_multiplier` | unknown | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | `_read_profile_from_snapshot`, `resolve_runtime_bot_effects` | runtime | no | 4 | investigate |
| `bot_flame_cooldown` | unknown | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry`, `resolve_runtime_bot_effects` | mixed | no | 4 | investigate |
| `bot_flame_damage` | unknown | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry`, `resolve_runtime_bot_effects` | mixed | no | 4 | investigate |
| `bot_flame_damage_reduction` | unknown | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry`, `resolve_runtime_bot_effects` | mixed | no | 4 | investigate |
| `bot_flame_range` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `bot_golden_bonus` | unknown | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry`, `resolve_runtime_bot_effects` | mixed | no | 4 | investigate |
| `bot_golden_cooldown` | unknown | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry`, `resolve_runtime_bot_effects` | mixed | no | 4 | investigate |
| `bot_golden_duration` | unknown | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry`, `resolve_runtime_bot_effects` | mixed | no | 4 | investigate |
| `bot_golden_range` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `bot_level_invalid` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_bot_stat_inputs` | static | no | 4 | investigate |
| `bot_level_missing` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_bot_stat_inputs` | static | no | 4 | investigate |
| `bot_levels` | unknown | declared_identifier | `tower_sim/engines/combat_stat_derivation.py` | `resolve_runtime_bot_effects` | runtime | no | 4 | investigate |
| `bot_range` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/registry/stat_registry.py` | `_apply_unique_effects`, `_compile_relic_stat_inputs`, `default_registry` | static | no | 4 | investigate |
| `bot_range_bonus_m` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_unique_effects` | static | no | 4 | investigate |
| `bot_table` | unknown | declared_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/naming_contract.py` | `_build_named_entity_maps`, `_compile_bot_stat_inputs` | static | no | 4 | investigate |
| `bot_thunder_cooldown` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `bot_thunder_duration` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `bot_thunder_linger` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `bot_thunder_range` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `bot_tracks` | unknown | declared_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_bot_stat_inputs` | static | no | 4 | investigate |
| `bot_unmapped` | unknown | consumed_identifier | `tower_sim/registry/naming_contract.py` | `validate_account_snapshot_naming` | static | no | 4 | investigate |
| `bot_upgrades` | unknown | declared_identifier | `tower_sim/loaders/account_snapshot_compiler.py`, `tower_sim/loaders/account_snapshot_loader.py`, `tower_sim/loaders/table_paths.py` | `_load_snapshot`, `_parse_bot_upgrades`, `_parse_bots` | static | no | 4 | investigate |
| `bot_upgrades_v1` | unknown | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 4 | investigate |
| `bot_values` | unknown | declared_identifier | `tower_sim/loaders/account_snapshot_compiler.py` | `_parse_bots` | static | no | 4 | investigate |
| `bounce_shot_chance` | target_stat | consumed_identifier | `tower_sim/loaders/ep_export_loader.py` | — | static | target_stat | 10 | aligned |
| `build_canonical_wave_row` | runtime | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | — | runtime | no | 7 | classify |
| `build_canonical_wave_snapshot` | runtime | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | — | runtime | no | 7 | classify |
| `build_edamage_stat_inputs` | unknown | consumed_identifier | `tower_sim/engines/edamage_pipeline.py` | — | mixed | no | 4 | investigate |
| `canonical_stat_inputs_for_wave` | runtime | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | — | runtime | no | 7 | classify |
| `card_canonical` | unknown | declared_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_card_effects` | static | no | 4 | investigate |
| `card_id` | unknown | consumed_identifier | `tower_sim/run/optimizer_patch.py` | `_validate_card_actions` | mixed | no | 4 | investigate |
| `card_level` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/engines/edamage_formulas.py` | `epd_aspd`, `epd_crit_chance` | static | no | 4 | investigate |
| `card_masteries` | unknown | declared_identifier | `tower_sim/loaders/table_paths.py`, `tower_sim/run/optimizer_engine.py` | `_load_card_masteries`, `_stone_actions` | static | no | 4 | investigate |
| `card_masteries_v1` | unknown | consumed_identifier | `tower_sim/engines/edamage_pipeline.py`, `tower_sim/loaders/table_paths.py`, `tower_sim/run/optimizer_engine.py` | `_load_card_masteries`, `_mastery_action`, `resolve_card_mastery_value` | static | no | 4 | investigate |
| `card_mastery` | unknown | consumed_identifier | `tower_sim/run/optimizer_engine.py` | `_load_card_masteries` | mixed | no | 4 | investigate |
| `card_name` | unknown | declared_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/loaders/account_snapshot_compiler.py` | `_compile_survivability_loadout_inputs_resilient`, `_level_from_provenance`, `_parse_cards` | mixed | no | 4 | investigate |
| `card_pct` | alias | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | — | static | no | 7 | alias-map |
| `card_presets` | unknown | declared_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/loaders/account_snapshot_loader.py` | `_load_snapshot`, `_parse_card_presets`, `_resolve_loadout_inputs` | mixed | no | 4 | investigate |
| `card_unmapped` | unknown | consumed_identifier | `tower_sim/registry/naming_contract.py` | `validate_account_snapshot_naming` | static | no | 4 | investigate |
| `card_val` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `cards_common` | unknown | consumed_identifier | `tower_sim/loaders/wiki/cards.py` | `_load_cards_df` | static | no | 4 | investigate |
| `cards_epic` | unknown | consumed_identifier | `tower_sim/loaders/wiki/cards.py` | `_load_cards_df` | static | no | 4 | investigate |
| `cards_inventory` | unknown | consumed_identifier | `tower_sim/loaders/account_snapshot_loader.py` | `_load_snapshot`, `_parse_cards` | static | no | 4 | investigate |
| `cards_lib` | report-only | consumed_identifier | `tower_sim/audit/repo_audit.py` | `_check_modules` | report | no | 7 | classify |
| `cards_rare` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tower_sim/engines/combat/boss_engine.py`, `tower_sim/loaders/wiki/cards.py` | `_load_cards_df` | mixed | no | 4 | investigate |
| `cash_bonus` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/registry/stat_registry.py` | `_compile_relic_stat_inputs`, `default_registry` | static | no | 4 | investigate |
| `chain_lightning_chance` | target_stat | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | target_stat | 10 | aligned |
| `chain_lightning_damage` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_slot_main_effect` | static | no | 4 | investigate |
| `chain_lightning_quantity` | target_stat | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | target_stat | 10 | aligned |
| `chrono_field_cooldown` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | no | 4 | investigate |
| `chrono_field_duration` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | no | 4 | investigate |
| `chrono_field_speed_reduction` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | no | 4 | investigate |
| `cl_chance` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `cl_damage` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `coin_actions_not_implemented` | unknown | consumed_identifier | `tower_sim/run/optimizer_engine.py` | `run_resource_optimizer` | mixed | no | 4 | investigate |
| `coin_level` | unknown | declared_identifier | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/loaders/account_snapshot_compiler.py`, … | `_apply_snapshot_patch`, `_parse_workshop`, `_serialize_workshop_entry` | static | no | 4 | investigate |
| `coin_mult` | alias | declared_identifier | `tower_sim/engines/uptime.py` | `aggregate_uptime` | runtime | no | 7 | alias-map |
| `coin_multiplier` | unknown | declared_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/econ_current.py`, `tower_sim/engines/uptime.py` | `_read_profile_from_snapshot`, `build_bot_effects`, `resolve_runtime_bot_effects` | runtime | no | 4 | investigate |
| `coin_sum` | unknown | declared_identifier | `tower_sim/engines/uptime.py` | `aggregate_uptime` | runtime | no | 4 | investigate |
| `coins_bonus` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `_compile_relic_stat_inputs`, `default_registry` | static | no | 4 | investigate |
| `coins_card` | unknown | declared_identifier | `tower_sim/engines/econ_current.py` | `econ_current` | mixed | no | 4 | investigate |
| `coins_mastery_lvl` | unknown | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `coins_per_kill_bonus` | target_stat | consumed_identifier | `tower_sim/loaders/ep_export_loader.py` | — | static | target_stat | 10 | aligned |
| `coins_per_kill_bonus_lvl` | unknown | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `coins_per_kill_mult` | alias | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 7 | split |
| `compile_workshop_values_at_wave` | runtime | consumed_identifier | `tower_sim/engines/stat_input_compiler.py` | — | static | no | 7 | classify |
| `compute_edamage_outputs` | unknown | consumed_identifier | `tower_sim/engines/edamage_pipeline.py` | — | mixed | no | 4 | investigate |
| `cooldown_s` | unknown | declared_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/uptime.py` | `_read_profile_from_snapshot`, `build_bot_effects`, `build_periodic_activation_intervals` | runtime | no | 4 | investigate |
| `crit_chance` | unknown | declared_identifier | `tower_sim/engines/edamage_pipeline.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/loaders/ep_export_loader.py` | `_compile_relic_stat_inputs`, `build_edamage_stat_inputs`, `compute_edamage_outputs` | static | no | 4 | investigate |
| `crit_factor` | unknown | declared_identifier | `tower_sim/engines/edamage_pipeline.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/loaders/ep_export_loader.py` | `_compile_relic_stat_inputs`, `compute_edamage_outputs` | static | no | 4 | investigate |
| `crit_multiplier` | unknown | declared_identifier | `tower_sim/engines/edamage_pipeline.py` | `build_edamage_stat_inputs`, `compute_edamage_outputs` | mixed | no | 4 | investigate |
| `critical_chance` | target_stat | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_card_effects` | static | target_stat | 10 | aligned |
| `current_bot` | unknown | declared_identifier | `tower_sim/loaders/account_snapshot_compiler.py` | `_parse_bots` | static | no | 4 | investigate |
| `current_wave` | runtime | declared_identifier | `tower_sim/engines/perk_timeline_generator.py`, `tower_sim/loaders/perk_timeline_loader.py` | `apply_perk_timeline_to_inputs`, `generate_timeline` | static | no | 7 | classify |
| `damage` | target_stat | declared_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tower_sim/audit/status.py`, `tower_sim/engines/combat/boss_engine.py`, … | `_apply_card_effects`, `_compile_relic_stat_inputs`, `_components` | mixed | target_stat | 10 | split |
| `damage_mult` | alias | declared_identifier | `tower_sim/engines/uptime.py` | `aggregate_uptime` | runtime | no | 7 | alias-map |
| `damage_mult_sum` | unknown | declared_identifier | `tower_sim/engines/uptime.py` | `aggregate_uptime` | runtime | no | 4 | investigate |
| `damage_multiplier` | unknown | declared_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/tier_rule_apply.py`, `tower_sim/engines/uptime.py` | `_read_profile_from_snapshot`, `build_bot_effects`, `resolve_runtime_bot_effects` | runtime | no | 4 | investigate |
| `damage_per_meter` | target_stat | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/loaders/ep_export_loader.py`, … | `_compile_relic_stat_inputs`, `default_registry` | static | target_stat | 10 | aligned |
| `damage_reduction` | unknown | declared_identifier | `tower_sim/engines/combat/boss_engine.py`, `tower_sim/engines/combat/boss_survivability.py`, `tower_sim/engines/combat_stat_derivation.py`, … | `_read_profile_from_snapshot`, `build_bot_effects`, `evaluate` | runtime | no | 4 | investigate |
| `damage_remaining` | unknown | declared_identifier | `tower_sim/engines/combat/boss_survivability.py` | `_time_to_death` | runtime | no | 4 | investigate |
| `damage_taken` | unknown | declared_identifier | `tower_sim/engines/uptime.py` | `aggregate_uptime` | runtime | no | 4 | investigate |
| `death_ray_damage_mult` | alias | emitted_key | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/engines/tier_rule_apply.py`, … | `_apply_condition`, `_build_reaches_stat_input`, `_compile_base_stat_inputs` | static | no | 7 | alias-map |
| `death_wave_cooldown` | runtime | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | no | 7 | classify |
| `death_wave_damage` | runtime | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_slot_main_effect` | static | no | 7 | classify |
| `death_wave_quantity` | runtime | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | no | 7 | classify |
| `def_pct` | report-only | declared_and_emitted | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/engines/combat_stat_derivation.py`, … | `_apply_card_effects`, `_build_reaches_stat_input`, `_compile_base_stat_inputs` | mixed | no | 7 | classify |
| `default_wave_damage_tier` | runtime | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | — | runtime | no | 7 | classify |
| `defense` | unknown | declared_identifier | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/engines/free_upgrades.py`, `tower_sim/engines/stat_input_compiler.py`, … | `_free_upgrade_chances`, `_parse_tower_defense`, `_workshop_category` | static | no | 4 | investigate |
| `defense_abs` | alias | declared_identifier | `tower_sim/engines/combat/boss_survivability.py` | `resolve_boss_fight` | runtime | no | 7 | alias-map |
| `defense_absolute` | target_stat | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/loaders/ep_export_loader.py`, … | `_apply_card_effects`, `_compile_relic_stat_inputs`, `default_registry` | static | target_stat | 10 | aligned |
| `defense_pct` | target_stat | declared_identifier | `tower_sim/engines/combat/boss_engine.py`, `tower_sim/engines/combat/boss_survivability.py`, `tower_sim/engines/survivability_pipeline.py` | `_missing_inputs`, `_resolve_survivability_verdict`, `evaluate` | runtime | target_stat | 10 | aligned |
| `defense_percent` | report-only | consumed_identifier | `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/loaders/ep_export_loader.py` | `_compile_relic_stat_inputs` | static | no | 7 | classify |
| `delta_mult` | alias | consumed_identifier | `tower_sim/registry/stat_registry.py` | — | static | no | 7 | alias-map |
| `duration_s` | unknown | declared_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/uptime.py` | `_read_profile_from_snapshot`, `build_bot_effects`, `build_gcomp_activation_intervals` | runtime | no | 4 | investigate |
| `dw_coin_bonus_lvl` | unknown | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `dwdamage` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `dwdamageamp` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `eals_pct` | alias | declared_and_emitted | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/engines/tier_rule_apply.py`, … | `_apply_skip_reduction`, `_build_reaches_stat_input`, `_build_wave_state` | static | no | 7 | alias-map |
| `eals_ramp` | unknown | declared_identifier | `tower_sim/run/problem_spec.py`, `tower_sim/run/spec_loader.py` | `_parse_scenario` | mixed | no | 4 | investigate |
| `edamage` | unknown | consumed_identifier | `tower_sim/engines/edamage_pipeline.py` | `inputs_from_canonical_values` | mixed | no | 4 | investigate |
| `effective_damage` | derived | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | `evaluate` | runtime | no | 4 | investigate |
| `effective_damage_per_sec` | derived | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | — | runtime | no | 4 | investigate |
| `effective_regen` | derived | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | `evaluate` | runtime | no | 4 | investigate |
| `effective_regen_per_sec` | derived | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | — | runtime | no | 4 | investigate |
| `ehls_pct` | alias | declared_and_emitted | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/engines/tier_rule_apply.py`, … | `_apply_skip_reduction`, `_build_reaches_stat_input`, `_build_wave_state` | static | no | 7 | alias-map |
| `ehls_ramp` | unknown | declared_identifier | `tower_sim/run/problem_spec.py`, `tower_sim/run/spec_loader.py` | `_parse_scenario` | mixed | no | 4 | investigate |
| `electrons_damage_frac` | unknown | declared_identifier | `tower_sim/engines/combat/boss_survivability.py` | `resolve_boss_fight` | runtime | no | 4 | investigate |
| `enemy_attack` | unknown | declared_identifier | `tower_sim/engines/combat/combat_engine.py` | `resolve_combat` | runtime | no | 4 | investigate |
| `enemy_attack_mult` | alias | consumed_identifier | `tower_sim/engines/combat/combat_engine.py` | `resolve_combat` | runtime | no | 7 | alias-map |
| `enemy_attack_wave` | runtime | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_pipeline.py` | `build_canonical_wave_row`, `resolve_wave_snapshot_for_problem_spec`, `wave_state_from_row` | runtime | no | 7 | classify |
| `enemy_damage_table` | unknown | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 4 | investigate |
| `enemy_health_table` | unknown | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 4 | investigate |
| `enemy_health_wave` | runtime | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_pipeline.py` | `build_canonical_wave_row`, `resolve_wave_snapshot_for_problem_spec`, `wave_state_from_row` | runtime | no | 7 | classify |
| `enemy_hp` | unknown | declared_identifier | `tower_sim/engines/combat/combat_engine.py` | — | runtime | no | 4 | investigate |
| `enemy_level_skip_reduction` | unknown | consumed_identifier | `tower_sim/engines/tier_rule_apply.py` | `_apply_condition` | mixed | no | 4 | investigate |
| `enhancement_multiplier` | report-only | declared_identifier | `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_engine.py`, … | `_build_row`, `_compile_workshop_stat_inputs`, `_extract_value` | mixed | no | 7 | classify |
| `enrage_mult` | alias | declared_identifier | `tower_sim/engines/combat/boss_survivability.py`, `tower_sim/run/problem_spec.py`, `tower_sim/run/spec_loader.py` | `_parse_boss_stats` | runtime | no | 7 | alias-map |
| `ep_edamage_cr5` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml`, `tower_sim/loaders/ep_export_loader.py` | — | static | no | 4 | investigate |
| `ep_edamage_cs5` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_ct5` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_cu5` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_cv5` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_cw5` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_cx5` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_cz5` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_da5` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_db5` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_dc5` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml`, `tower_sim/loaders/ep_export_loader.py` | — | static | no | 4 | investigate |
| `ep_edamage_dd5` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_de5` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_df5` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_dg5` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_dh5` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_di5` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_dj5` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_dk5` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_dl5` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml`, `tower_sim/loaders/ep_export_loader.py` | — | static | no | 4 | investigate |
| `ep_edamage_dm5` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml`, `tower_sim/loaders/ep_export_loader.py` | — | static | no | 4 | investigate |
| `ep_edamage_dp5` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml`, `tower_sim/loaders/ep_export_loader.py` | — | static | no | 4 | investigate |
| `ep_edamage_ds5` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_dt5` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_du5` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_dv5` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_dw5` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_dy5` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_eb5` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_ef5` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml`, `tower_sim/loaders/ep_export_loader.py` | — | static | no | 4 | investigate |
| `ep_lambda_ep_uw_sl_coverage` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_ep_uw_total_damage` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_epd_crit_chance` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_epd_critical` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_epd_multishot` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_epd_range` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_epd_rangedpm` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_epd_supertower_cooldown` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_epd_uwcritical` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_eph_def_pct` | alias | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | alias-map |
| `ep_lambda_eph_health` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_eph_regen` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_eph_wall_health` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_eph_wall_regen` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_stat_uw_cl_final_ch` | derived | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_stat_uw_cl_final_dmg` | derived | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_stat_uw_cl_final_qty` | derived | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_stat_uw_dw_final_cd` | derived | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_stat_uw_dw_final_dmg` | derived | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_stat_uw_dw_final_qty` | derived | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_stat_uw_sl_final_angle` | derived | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_stat_uw_sl_final_dmg` | derived | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_stat_uw_sl_final_lr` | derived | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_stat_uw_sm_final_cd` | derived | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_stat_uw_sm_final_cf` | derived | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_stat_uw_sm_final_dmg` | derived | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_stat_uw_sm_final_qty` | derived | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `epd_crit_chance` | unknown | consumed_identifier | `tower_sim/engines/edamage_formulas.py` | — | mixed | no | 4 | investigate |
| `epd_critical` | unknown | consumed_identifier | `tower_sim/engines/edamage_formulas.py` | — | mixed | no | 4 | investigate |
| `equipped_cards` | unknown | declared_identifier | `tower_sim/run/api.py` | `_serialize_loadout` | mixed | no | 4 | investigate |
| `expected_coin_multiplier` | unknown | declared_identifier | `tower_sim/engines/uptime.py` | — | runtime | no | 4 | investigate |
| `expected_damage_multiplier` | unknown | declared_identifier | `tower_sim/engines/uptime.py` | — | runtime | no | 4 | investigate |
| `expected_damage_taken` | unknown | declared_identifier | `tower_sim/engines/uptime.py` | — | runtime | no | 4 | investigate |
| `expected_skipped_waves` | runtime | consumed_identifier | `tower_sim/audit/status.py` | `_components` | report | no | 7 | classify |
| `extra_defense` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_card_effects` | static | no | 4 | investigate |
| `extra_orb_mastery_lvl` | unknown | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `extract_max_wave_targets` | runtime | consumed_identifier | `tower_sim/loaders/ep_export_loader.py` | — | static | no | 7 | classify |
| `final_wave` | runtime | consumed_identifier | `tower_sim/engines/perk_timeline_generator.py` | `generate_timeline` | mixed | no | 7 | classify |
| `flame_bot_damage_reduction_multiplier` | unknown | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | `resolve_runtime_bot_effects` | runtime | no | 4 | investigate |
| `free_attack_upgrade` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/loaders/ep_export_loader.py`, … | `_compile_relic_stat_inputs`, `default_registry` | static | no | 4 | investigate |
| `free_attack_upgrade_rate` | unknown | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `free_defense_upgrade` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/loaders/ep_export_loader.py`, … | `_compile_relic_stat_inputs`, `default_registry` | static | no | 4 | investigate |
| `from_wave` | runtime | declared_identifier | `tower_sim/engines/combat_stat_derivation.py` | `derive_canonical_combat_snapshot` | runtime | no | 7 | classify |
| `generator_module` | unknown | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `gold_bot_cooldown_lvl` | unknown | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `gold_bot_duration_lvl` | unknown | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `golden_tower_cooldown` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | no | 4 | investigate |
| `golden_tower_duration` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | no | 4 | investigate |
| `golden_tower_multiplier` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | no | 4 | investigate |
| `gt_duration_lvl` | unknown | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `has_card` | unknown | declared_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/engines/econ_current.py`, … | `epd_aspd`, `epd_crit_chance` | static | no | 4 | investigate |
| `has_coins_perk` | unknown | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `has_module` | unknown | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `has_more_bosses` | unknown | declared_identifier | `tower_sim/loaders/tournament_bc_selection.py` | `load_league_rules` | static | no | 4 | investigate |
| `health` | target_stat | consumed_identifier | `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/audit/wiring_health_check.py`, `tower_sim/engines/combat/combat_engine.py`, … | `_apply_card_effects`, `_compile_relic_stat_inputs`, `_parse_args` | mixed | target_stat | 10 | split |
| `health_regen` | target_stat | consumed_identifier | `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, … | `_apply_card_effects`, `_compile_relic_stat_inputs` | static | target_stat | 10 | aligned |
| `heat_mult` | alias | declared_identifier | `tower_sim/engines/combat/boss_survivability.py` | `_time_to_death` | runtime | no | 7 | alias-map |
| `hpregen` | unknown | consumed_identifier | `tower_sim/registry/naming_contract.py` | — | static | no | 4 | investigate |
| `incoming_damage` | unknown | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | `evaluate` | runtime | no | 4 | investigate |
| `inner_land_mines_cooldown` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | no | 4 | investigate |
| `inner_land_mines_damage` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_slot_main_effect` | static | no | 4 | investigate |
| `inner_land_mines_quantity` | target_stat | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | target_stat | 10 | aligned |
| `is_boss` | unknown | declared_identifier | `tower_sim/engines/combat/combat_engine.py` | — | runtime | no | 4 | investigate |
| `key_modules` | report-only | declared_identifier | `tower_sim/audit/repo_audit.py` | `_check_modules` | report | no | 7 | classify |
| `kill_at_range` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `knockback_mult` | alias | emitted_key | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/engines/tier_rule_apply.py`, … | `_apply_condition`, `_build_reaches_stat_input`, `_compile_base_stat_inputs` | static | no | 7 | alias-map |
| `knockback_multiplier` | unknown | consumed_identifier | `tower_sim/engines/tier_rule_apply.py` | — | mixed | no | 4 | investigate |
| `lab_enemy_attack_level_skip` | unknown | consumed_identifier | `tower_sim/loaders/wiki/labs_eals_ehls.py` | `get_eals_lab_pp` | static | no | 4 | investigate |
| `lab_enemy_health_level_skip` | unknown | consumed_identifier | `tower_sim/loaders/wiki/labs_eals_ehls.py` | `get_ehls_lab_pp` | static | no | 4 | investigate |
| `lab_health` | unknown | consumed_identifier | `tower_sim/loaders/wiki/labs.py` | — | static | no | 4 | investigate |
| `lab_health_regen` | unknown | consumed_identifier | `tower_sim/loaders/wiki/labs.py` | — | static | no | 4 | investigate |
| `lab_multiplier` | unknown | declared_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_workshop_stat_inputs` | static | no | 4 | investigate |
| `lab_pct` | alias | declared_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_armor_module_multiplier` | static | no | 7 | alias-map |
| `lab_recovery_package_chance` | unknown | consumed_identifier | `tower_sim/loaders/wiki/labs.py` | — | static | no | 4 | investigate |
| `lab_speed` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `_compile_relic_stat_inputs`, `default_registry` | static | no | 4 | investigate |
| `lineage_required_max_wave_gap_count` | runtime | consumed_identifier | `tower_sim/audit/wiring_health_check.py` | `run_wiring_health_check` | report | no | 7 | classify |
| `load_card_masteries` | unknown | consumed_identifier | `tower_sim/loaders/card_masteries.py` | — | static | no | 4 | investigate |
| `locked_uws` | unknown | declared_identifier | `tower_sim/run/optimizer_engine.py` | `_parse_uw_rows`, `_stone_actions` | mixed | no | 4 | investigate |
| `make_wave_state` | runtime | consumed_identifier | `tower_sim/audit/status.py` | `_components` | report | no | 7 | classify |
| `mastery_mult` | alias | declared_identifier | `tower_sim/engines/econ_current.py` | `EPC_CARD_COINS` | mixed | no | 7 | split |
| `max_recovery_vault_mult` | alias | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | alias-map |
| `max_recovery_wse_mult` | alias | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | alias-map |
| `max_rend_mult` | alias | consumed_identifier | `tower_sim/loaders/ep_export_loader.py` | — | static | no | 7 | alias-map |
| `max_wave` | runtime | declared_identifier | `tower_sim/audit/status.py`, `tower_sim/loaders/bc_heat_loader.py`, `tower_sim/loaders/ep_export_loader.py`, … | `_components`, `_parse_problem_spec`, `extract_max_wave_targets` | static | no | 7 | classify |
| `max_wave_ids` | runtime | declared_identifier | `tower_sim/engines/statbook_builder.py` | `_target_stat_ids` | mixed | no | 7 | classify |
| `max_wave_latest` | runtime | consumed_identifier | `tower_sim/run/runner.py` | — | mixed | no | 7 | classify |
| `max_wave_report` | runtime | consumed_identifier | `tower_sim/audit/status.py` | `_components` | report | no | 7 | classify |
| `max_wave_runner` | runtime | consumed_identifier | `tower_sim/run/runner.py` | — | mixed | no | 7 | classify |
| `min_wave` | runtime | declared_identifier | `tower_sim/loaders/bc_heat_loader.py` | `value_at` | static | no | 7 | classify |
| `missing_at_wave` | runtime | emitted_key | `tower_sim/engines/stat_pipeline.py` | `build_canonical_stat_pipeline_for_problem_spec` | mixed | no | 7 | classify |
| `missing_cards` | unknown | declared_identifier | `tower_sim/loaders/account_snapshot_compiler.py` | `_parse_cards` | static | no | 4 | investigate |
| `missing_required_at_wave_stats` | runtime | emitted_key | `tower_sim/engines/stat_pipeline.py` | `build_canonical_stat_pipeline_for_problem_spec` | mixed | no | 7 | classify |
| `missing_wave` | runtime | declared_identifier | `tower_sim/engines/stat_pipeline.py` | `build_canonical_stat_pipeline_for_problem_spec` | mixed | no | 7 | classify |
| `missing_wave_state` | runtime | emitted_key | `tower_sim/engines/stat_pipeline.py` | `build_canonical_stat_pipeline_for_problem_spec` | mixed | no | 7 | classify |
| `module_` | unknown | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | `_canonical_unmapped_by_source`, `_families_from_stat_input` | runtime | no | 4 | investigate |
| `module_blocks` | unknown | declared_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_build_inventory_summary`, `compile_baseline_loadout_stat_inputs` | static | no | 4 | investigate |
| `module_context` | unknown | declared_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_pipeline.py` | `_compile_survivability_loadout_inputs_resilient`, `_resolve_loadout_inputs` | runtime | no | 4 | investigate |
| `module_contribution_ledger` | unknown | declared_and_emitted | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, … | `_compile_survivability_loadout_inputs_resilient`, `build_canonical_stat_inputs`, `build_canonical_stat_pipeline_for_problem_spec` | mixed | no | 4 | investigate |
| `module_id` | unknown | consumed_identifier | `tower_sim/run/optimizer_patch.py` | `_validate_module_actions` | mixed | no | 4 | investigate |
| `module_layer_gaps` | unknown | emitted_key | `tower_sim/engines/survivability_pipeline.py` | `build_survivability_report` | mixed | no | 4 | investigate |
| `module_main_effect_bands` | unknown | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 4 | investigate |
| `module_main_effect_bands_v1` | unknown | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 4 | investigate |
| `module_main_effect_bases` | unknown | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 4 | investigate |
| `module_main_effect_bases_v1` | unknown | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 4 | investigate |
| `module_name` | report-only | declared_identifier | `tower_sim/audit/repo_audit.py`, `tower_sim/engines/survivability_pipeline.py` | `_check_modules`, `_parse_module_block` | report | no | 7 | classify |
| `module_preset_unmapped` | unknown | consumed_identifier | `tower_sim/registry/naming_contract.py` | `validate_account_snapshot_naming` | static | no | 4 | investigate |
| `module_presets` | unknown | declared_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/loaders/account_snapshot_compiler.py`, `tower_sim/loaders/account_snapshot_loader.py` | `_load_snapshot`, `_parse_module_presets`, `_parse_modules` | mixed | no | 4 | investigate |
| `module_primary_effect` | unknown | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_slot_main_effect`, `_module_unmapped_by_layer` | mixed | no | 4 | investigate |
| `module_rules` | unknown | consumed_identifier | `tower_sim/engines/modules.py` | — | mixed | no | 4 | investigate |
| `module_substat_unmapped` | unknown | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, … | `_apply_module_substats`, `_module_unmapped_by_layer`, `validate_account_snapshot_naming` | mixed | no | 4 | investigate |
| `module_substats` | unknown | consumed_identifier | `tower_sim/loaders/table_paths.py`, `tower_sim/registry/naming_contract.py` | `_build_named_entity_maps`, `validate_account_snapshot_naming`, `validate_repo_naming_contract` | static | no | 4 | investigate |
| `module_substats_v1` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/loaders/table_paths.py` | — | static | no | 4 | investigate |
| `module_summary` | unknown | declared_identifier | `tower_sim/engines/survivability_pipeline.py` | `_build_inventory_summary` | mixed | no | 4 | investigate |
| `module_system_state` | unknown | declared_identifier | `tower_sim/loaders/account_snapshot_compiler.py`, `tower_sim/loaders/account_snapshot_loader.py` | `_load_snapshot`, `_parse_module_system_state`, `_parse_modules` | static | no | 4 | investigate |
| `module_unique_unmapped` | unknown | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_module_effects`, `_module_unmapped_by_layer` | mixed | no | 4 | investigate |
| `module_unmapped` | unknown | consumed_identifier | `tower_sim/registry/naming_contract.py` | `validate_account_snapshot_naming` | static | no | 4 | investigate |
| `module_unmapped_by_layer` | unknown | declared_and_emitted | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_pipeline.py` | `build_canonical_stat_inputs`, `build_canonical_stat_pipeline_for_problem_spec` | runtime | no | 4 | investigate |
| `modules_inventory` | unknown | declared_identifier | `tower_sim/loaders/account_snapshot_compiler.py`, `tower_sim/loaders/account_snapshot_loader.py` | `_load_snapshot`, `_parse_modules` | static | no | 4 | investigate |
| `modules_lib` | report-only | consumed_identifier | `tower_sim/audit/repo_audit.py` | `_check_modules` | report | no | 7 | classify |
| `modules_library` | report-only | consumed_identifier | `tower_sim/audit/repo_audit.py`, `tower_sim/engines/modules.py` | `_check_modules`, `_iter_reference_files` | report | no | 7 | classify |
| `more_bosses` | unknown | declared_identifier | `tower_sim/engines/tier_rule_apply.py`, `tower_sim/loaders/bc_heat_loader.py`, `tower_sim/loaders/tournament_bc_selection.py` | `_apply_condition`, `enumerate_tournament_bc_sets`, `load_tournament_heat_table` | static | no | 4 | investigate |
| `multi_rapid_bounce` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `multiplier_cap` | unknown | declared_identifier | `tower_sim/loaders/account_snapshot_compiler.py`, `tower_sim/loaders/account_snapshot_loader.py` | `_parse_module_system_state` | static | no | 4 | investigate |
| `multiplier_efficiency` | unknown | declared_identifier | `tower_sim/engines/modules.py` | `apply_multiplier_efficiency` | mixed | no | 4 | investigate |
| `multiplier_level` | unknown | declared_identifier | `tower_sim/run/optimizer_engine.py` | `_stone_actions` | mixed | no | 4 | investigate |
| `multishot_chance` | target_stat | consumed_identifier | `tower_sim/loaders/ep_export_loader.py` | — | static | target_stat | 10 | aligned |
| `multishot_targets` | target_stat | consumed_identifier | `tower_sim/loaders/ep_export_loader.py` | — | static | target_stat | 10 | aligned |
| `net_damage` | unknown | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | `evaluate` | runtime | no | 4 | investigate |
| `net_damage_per_sec` | unknown | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | — | runtime | no | 4 | investigate |
| `next_percent` | unknown | declared_identifier | `tower_sim/run/optimizer_engine.py` | `_apply_unlock` | mixed | no | 4 | investigate |
| `next_uw_plus_unlock_cost` | unknown | declared_identifier | `tower_sim/run/optimizer_engine.py` | `_stone_actions` | mixed | no | 4 | investigate |
| `next_uw_unlock_cost` | unknown | declared_identifier | `tower_sim/run/optimizer_engine.py` | `_stone_actions` | mixed | no | 4 | investigate |
| `next_wave` | runtime | declared_identifier | `tower_sim/engines/perk_timeline_generator.py` | `generate_timeline` | mixed | no | 7 | classify |
| `no_authoritative_bot_mapping_for_stat` | unknown | consumed_identifier | `tower_sim/registry/combat_stat_contract.py` | `_excluded_reason`, `stat_lineage_status_lists` | static | no | 4 | investigate |
| `no_authoritative_card_mapping_for_stat` | unknown | consumed_identifier | `tower_sim/registry/combat_stat_contract.py` | `_excluded_reason`, `stat_lineage_status_lists` | static | no | 4 | investigate |
| `no_authoritative_module_mapping_for_stat` | unknown | consumed_identifier | `tower_sim/registry/combat_stat_contract.py` | `_excluded_reason`, `stat_lineage_status_lists` | static | no | 4 | investigate |
| `no_authoritative_uw_mapping_for_stat` | unknown | consumed_identifier | `tower_sim/registry/combat_stat_contract.py` | `_excluded_reason`, `stat_lineage_status_lists` | static | no | 4 | investigate |
| `op_chain` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `orb_damage_frac` | unknown | declared_identifier | `tower_sim/engines/combat/boss_survivability.py` | `resolve_boss_fight` | runtime | no | 4 | investigate |
| `orb_damage_mult` | alias | emitted_key | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/engines/tier_rule_apply.py`, … | `_apply_condition`, `_build_reaches_stat_input`, `_compile_base_stat_inputs` | static | no | 7 | alias-map |
| `orb_resistance` | unknown | consumed_identifier | `tower_sim/engines/survivability_pipeline.py`, `tower_sim/engines/tier_rule_apply.py`, `tower_sim/loaders/tournament_bc_enrichment.py` | `_apply_condition`, `_tier_rules_applied` | static | no | 4 | investigate |
| `orb_speed` | target_stat | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/registry/stat_registry.py` | `_compile_relic_stat_inputs`, `default_registry` | static | target_stat | 10 | aligned |
| `out_of_range` | unknown | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | `validate_boss_survivability_spec` | runtime | no | 4 | investigate |
| `package_chance` | target_stat | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | `evaluate` | runtime | target_stat | 10 | aligned |
| `package_heal` | unknown | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | `evaluate` | runtime | no | 4 | investigate |
| `package_regen` | unknown | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | `evaluate` | runtime | no | 4 | investigate |
| `pc_boss_mult` | alias | declared_identifier | `tower_sim/engines/combat/boss_engine.py`, `tower_sim/engines/combat/boss_survivability.py`, `tower_sim/engines/combat/combat_engine.py` | `evaluate`, `resolve_boss_fight`, `resolve_combat` | runtime | no | 7 | alias-map |
| `per_hit_boss_frac` | unknown | declared_identifier | `tower_sim/engines/combat/boss_survivability.py` | `resolve_boss_fight` | runtime | no | 4 | investigate |
| `percent_points` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/loaders/wiki/promote_labs_tables.py`, … | `_compile_wall_survivability_aliases`, `_parse_value`, `_resolve_lab_delta` | static | no | 4 | investigate |
| `percent_string` | unknown | consumed_identifier | `tower_sim/loaders/wiki/cache_audit.py` | `_detect_unit_hint`, `_strip_unit` | static | no | 4 | investigate |
| `perk_multiplier` | unknown | declared_identifier | `tower_sim/engines/edamage_pipeline.py` | `resolve_damage_perk_multiplier` | mixed | no | 4 | investigate |
| `plasma_cannon_card_frac_v1` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | — | static | no | 4 | investigate |
| `plasma_cannon_damage_mult` | alias | emitted_key | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/engines/tier_rule_apply.py`, … | `_apply_card_effects`, `_apply_condition`, `_build_reaches_stat_input` | static | no | 7 | alias-map |
| `poison_swamp_cooldown` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | no | 4 | investigate |
| `poison_swamp_damage` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_slot_main_effect` | static | no | 4 | investigate |
| `poison_swamp_duration` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | no | 4 | investigate |
| `preset_cards` | unknown | declared_identifier | `tower_sim/engines/wave_time.py` | `wa_reduction_from_snapshot` | runtime | no | 4 | investigate |
| `ramp_waves` | runtime | declared_identifier | `tower_sim/engines/wave_engine.py`, `tower_sim/run/problem_spec.py`, `tower_sim/run/spec_loader.py` | `_parse_skip_ramp` | runtime | no | 7 | classify |
| `range_dpm` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | — | static | no | 4 | investigate |
| `range_multiplier` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | — | static | no | 4 | investigate |
| `rapid_fire_chance` | target_stat | consumed_identifier | `tower_sim/loaders/ep_export_loader.py` | — | static | target_stat | 10 | aligned |
| `rapid_fire_duration` | unknown | consumed_identifier | `tower_sim/loaders/ep_export_loader.py` | — | static | no | 4 | investigate |
| `raw_damage` | unknown | declared_identifier | `tower_sim/engines/combat/boss_survivability.py` | `_time_to_death` | runtime | no | 4 | investigate |
| `raw_multiplier` | unknown | declared_identifier | `tower_sim/engines/stat_input_compiler.py` | `_parse_workshop_enhancement_multipliers` | static | no | 4 | investigate |
| `recovery_package_chance` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/engines/survivability_pipeline.py`, … | `_apply_card_effects` | static | no | 4 | investigate |
| `recovery_package_max` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `reduced_damage` | unknown | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | `evaluate` | runtime | no | 4 | investigate |
| `regen` | report-only | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/audit/status.py`, `tower_sim/engines/stat_input_compiler.py`, … | `_components`, `_workshop_value`, `default_registry` | static | no | 7 | classify |
| `regen_per_hit` | unknown | declared_identifier | `tower_sim/engines/combat/boss_survivability.py` | `_time_to_death` | runtime | no | 4 | investigate |
| `regen_per_sec` | unknown | declared_identifier | `tower_sim/engines/combat/boss_survivability.py`, `tower_sim/run/problem_spec.py`, `tower_sim/run/spec_loader.py` | `_parse_tower_defense` | runtime | no | 4 | investigate |
| `relic_pct` | alias | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | alias-map |
| `remaining_enemy_hp` | unknown | consumed_identifier | `tower_sim/engines/combat/combat_engine.py` | `resolve_combat` | runtime | no | 4 | investigate |
| `rend_mult` | alias | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | — | static | no | 7 | alias-map |
| `required_max_wave` | runtime | consumed_identifier | `tower_sim/audit/stat_lineage_report.py` | `_build_full_table` | report | no | 7 | classify |
| `required_max_wave_gap_count` | runtime | consumed_identifier | `tower_sim/audit/stat_lineage_report.py`, `tower_sim/audit/wiring_health_check.py` | `_parse_args`, `render_report`, `run_wiring_health_check` | report | no | 7 | classify |
| `required_max_wave_gaps` | runtime | declared_identifier | `tower_sim/audit/stat_lineage_report.py` | `render_report`, `summarize_manifest` | report | no | 7 | classify |
| `required_max_wave_other` | runtime | declared_identifier | `tower_sim/registry/combat_stat_contract.py` | `ordered_stat_lineage_sections` | static | no | 7 | classify |
| `required_max_wave_other_stat_inputs` | runtime | consumed_identifier | `tower_sim/registry/combat_stat_contract.py` | `ordered_stat_lineage_sections` | static | no | 7 | classify |
| `required_max_wave_stat_input_ids` | runtime | consumed_identifier | `tower_sim/audit/stat_lineage_report.py`, `tower_sim/registry/combat_stat_contract.py` | `load_manifest`, `summarize_manifest` | static | no | 7 | classify |
| `resolve_canonical_wave_damage` | runtime | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | — | runtime | no | 7 | classify |
| `resolve_canonical_wave_damage_for_attack_wave` | runtime | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | — | runtime | no | 7 | classify |
| `resolve_card_mastery_value` | unknown | consumed_identifier | `tower_sim/engines/edamage_pipeline.py` | — | mixed | no | 4 | investigate |
| `resolve_damage_perk_multiplier` | unknown | consumed_identifier | `tower_sim/engines/edamage_pipeline.py` | — | mixed | no | 4 | investigate |
| `resolve_wave_state_for_wave` | runtime | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | — | runtime | no | 7 | classify |
| `selected_cards` | unknown | declared_and_emitted | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_pipeline.py` | `_compile_survivability_loadout_inputs_resilient`, `_resolve_loadout_inputs` | runtime | no | 4 | investigate |
| `skip_ramp` | unknown | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_pipeline.py` | `_build_wave_state`, `resolve_wave_state_for_wave` | runtime | no | 4 | investigate |
| `skipped_missing_targets` | report-only | consumed_identifier | `tower_sim/audit/max_wave_ep_parity.py` | `validate_runner_against_ep_export` | runtime | no | 7 | classify |
| `sl_damage` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `sl_lightrange` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `sm_cooldown` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `sm_damage` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `smart_missiles_cooldown` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | no | 4 | investigate |
| `smart_missiles_damage` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_slot_main_effect` | static | no | 4 | investigate |
| `smart_missiles_quantity` | target_stat | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | target_stat | 10 | aligned |
| `spotlight_coin_bonus_lvl` | unknown | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `spotlight_multiplier` | unknown | consumed_identifier | `tower_sim/engines/econ_current.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | no | 4 | investigate |
| `st_uw_mastery` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `standard_perks_bonus_mult` | alias | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | alias-map |
| `stone_pct` | alias | declared_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_armor_module_multiplier`, `_resolve_assist_efficiencies` | static | no | 7 | alias-map |
| `super_crit_chance` | target_stat | declared_identifier | `tower_sim/engines/edamage_pipeline.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, … | `_compile_relic_stat_inputs`, `default_registry`, `inputs_from_canonical_values` | static | target_stat | 10 | aligned |
| `super_crit_mult` | alias | declared_identifier | `tower_sim/engines/edamage_pipeline.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, … | `_compile_relic_stat_inputs`, `default_registry`, `inputs_from_canonical_values` | static | no | 7 | alias-map |
| `super_crit_multiplier` | target_stat | consumed_identifier | `tower_sim/loaders/ep_export_loader.py` | — | static | target_stat | 10 | aligned |
| `survivability_loadout_unknown_card` | unknown | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | `_compile_survivability_loadout_inputs_resilient` | runtime | no | 4 | investigate |
| `survivability_loadout_unsupported_card` | unknown | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | `_compile_survivability_loadout_inputs_resilient` | runtime | no | 4 | investigate |
| `target_wall_hp_base` | unknown | declared_identifier | `tower_sim/engines/combat_stat_derivation.py` | `_rebase_wall_stats_from_tower` | runtime | no | 4 | investigate |
| `target_wall_regen_base` | unknown | declared_identifier | `tower_sim/engines/combat_stat_derivation.py` | `_rebase_wall_stats_from_tower` | runtime | no | 4 | investigate |
| `target_wave` | runtime | declared_identifier | `tower_sim/engines/perk_timeline_generator.py`, `tower_sim/engines/stat_pipeline.py` | `build_canonical_stat_pipeline_for_problem_spec`, `load_policy` | mixed | no | 7 | classify |
| `test_boss_engine` | report-only | consumed_identifier | `tower_sim/audit/status.py` | `_components` | report | no | 7 | classify |
| `test_boss_survivability` | report-only | consumed_identifier | `tower_sim/audit/status.py` | `_components` | report | no | 7 | classify |
| `test_max_wave_observability` | runtime | consumed_identifier | `tower_sim/audit/status.py` | `_components` | report | no | 7 | classify |
| `test_max_wave_v1_contract` | runtime | consumed_identifier | `tower_sim/audit/status.py` | `_components` | report | no | 7 | classify |
| `test_wave_damage_strict` | runtime | consumed_identifier | `tower_sim/audit/status.py` | `_components` | report | no | 7 | classify |
| `test_wave_engine` | runtime | consumed_identifier | `tower_sim/audit/status.py` | `_components` | report | no | 7 | classify |
| `thorns_damage_mult` | alias | emitted_key | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, … | `_apply_condition`, `_build_reaches_stat_input`, `_compile_base_stat_inputs` | mixed | no | 7 | split |
| `thorns_frac` | unknown | declared_identifier | `tower_sim/engines/combat/boss_engine.py`, `tower_sim/engines/combat/boss_survivability.py`, `tower_sim/engines/combat/combat_engine.py`, … | `_resolve_survivability_verdict`, `evaluate`, `resolve_boss_fight` | runtime | no | 4 | investigate |
| `thorns_mult` | alias | consumed_identifier | `tower_sim/engines/survivability_pipeline.py` | `_resolve_thorns_inputs` | mixed | no | 7 | split |
| `thorns_pct` | alias | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | `_missing_inputs`, `evaluate` | runtime | no | 7 | alias-map |
| `thorns_resistance` | unknown | consumed_identifier | `tower_sim/engines/survivability_pipeline.py`, `tower_sim/engines/tier_rule_apply.py`, `tower_sim/loaders/tournament_bc_enrichment.py` | `_apply_condition`, `_tier_rules_applied` | static | no | 4 | investigate |
| `tier_multiplier` | report-only | declared_identifier | `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_snapshots.py` | `_extract_value`, `_resolve_stat_input_value`, `_resolved_stat_input_value` | runtime | no | 7 | classify |
| `tier_rule_multiplier` | unknown | declared_identifier | `tower_sim/engines/stat_engine.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/run/api.py`, … | `_merge_stat_input_for_run_stats`, `_parse_stat_input`, `_resolved_stat_input_value` | static | no | 4 | investigate |
| `tier_wave_damage` | runtime | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 7 | classify |
| `tier_wave_damage_legacy` | runtime | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 7 | classify |
| `time_multiplier_mode` | unknown | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `total_damage` | unknown | declared_identifier | `tower_sim/engines/combat/combat_engine.py` | `resolve_combat` | runtime | no | 4 | investigate |
| `tournament_more_bosses_static` | unknown | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 4 | investigate |
| `tournament_wave_damage` | runtime | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 7 | classify |
| `tournament_wave_damage_legacy` | runtime | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 7 | classify |
| `tower_attack_speed` | unknown | declared_and_emitted | `tower_sim/engines/edamage_pipeline.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, … | `_apply_card_effects`, `_build_reaches_stat_input`, `_compile_relic_stat_inputs` | static | no | 4 | investigate |
| `tower_crit_chance` | unknown | declared_and_emitted | `tower_sim/engines/edamage_pipeline.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, … | `_apply_card_effects`, `_build_reaches_stat_input`, `_compile_relic_stat_inputs` | static | no | 4 | investigate |
| `tower_crit_factor` | unknown | declared_identifier | `tower_sim/engines/edamage_pipeline.py` | — | mixed | no | 4 | investigate |
| `tower_crit_multiplier` | unknown | emitted_key | `tower_sim/engines/edamage_pipeline.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, … | `_build_reaches_stat_input`, `_compile_relic_stat_inputs`, `build_edamage_stat_inputs` | static | no | 4 | investigate |
| `tower_damage` | unknown | declared_and_emitted | `tower_sim/engines/combat/combat_engine.py`, `tower_sim/engines/edamage_pipeline.py`, `tower_sim/engines/stat_input_compiler.py`, … | `_apply_card_effects`, `_apply_slot_main_effect`, `_build_reaches_stat_input` | mixed | no | 4 | investigate |
| `tower_damage_taken` | unknown | consumed_identifier | `tower_sim/engines/combat/combat_engine.py` | `resolve_combat` | runtime | no | 4 | investigate |
| `tower_kills_boss` | unknown | consumed_identifier | `tower_sim/engines/combat/boss_survivability.py` | `resolve_boss_fight` | runtime | no | 4 | investigate |
| `tower_regen` | report-only | declared_and_emitted | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/engines/combat/boss_engine.py`, … | `_apply_card_effects`, `_build_reaches_stat_input`, `_compile_base_stat_inputs` | mixed | no | 7 | classify |
| `tower_regen_per_sec` | unknown | emitted_key | `tower_sim/engines/combat_stat_derivation.py` | `validate_boss_survivability_spec` | runtime | no | 4 | investigate |
| `transfer_multiplier` | unknown | declared_identifier | `tower_sim/engines/combat_stat_derivation.py` | `_replace_base` | runtime | no | 4 | investigate |
| `ultimate_crit` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_card_effects` | static | no | 4 | investigate |
| `ultimate_damage` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `_compile_relic_stat_inputs`, `default_registry` | static | no | 4 | investigate |
| `unknown_card` | unknown | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | `_canonical_unmapped_by_source` | runtime | no | 4 | investigate |
| `unsupported_card` | unknown | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | `_canonical_unmapped_by_source` | runtime | no | 4 | investigate |
| `upgrade_mult` | alias | declared_identifier | `tower_sim/engines/stat_input_compiler.py` | `_free_upgrade_chances` | static | no | 7 | alias-map |
| `uw_` | unknown | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/statbook_builder.py`, … | `_canonical_unmapped_by_source`, `_ordered_target_stat_ids`, `_uw_canonical_aliases` | mixed | no | 4 | investigate |
| `uw_alias` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_uw_stat_inputs` | static | no | 4 | investigate |
| `uw_alias_pairs` | unknown | declared_identifier | `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_behavior` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_unique_effects` | static | no | 4 | investigate |
| `uw_black_hole_consume` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_black_hole_cooldown` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_black_hole_duration` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_black_hole_size` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_canonical` | unknown | declared_identifier | `tower_sim/registry/naming_contract.py` | `_build_named_entity_maps` | static | no | 4 | investigate |
| `uw_chain_lightning_chance` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_chain_lightning_damage` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_chain_lightning_quantity` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_chain_lightning_smite` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_chrono_field_chrono_loop` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_chrono_field_cooldown` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_chrono_field_duration` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_chrono_field_speed_reduction` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_cost_stats` | unknown | declared_identifier | `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_costs` | unknown | declared_identifier | `tower_sim/run/optimizer_engine.py` | `_load_uw_purchase_costs` | mixed | no | 4 | investigate |
| `uw_crit_card` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `uw_damage_boost` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `uw_death_wave_cooldown` | runtime | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 7 | classify |
| `uw_death_wave_damage` | runtime | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 7 | classify |
| `uw_death_wave_kill_wall` | runtime | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 7 | classify |
| `uw_death_wave_quantity` | runtime | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 7 | classify |
| `uw_golden_tower_cooldown` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_golden_tower_duration` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_golden_tower_golden_combo` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_golden_tower_multiplier` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_ids` | unknown | declared_identifier | `tower_sim/engines/statbook_builder.py` | `_target_stat_ids` | mixed | no | 4 | investigate |
| `uw_inner_land_mines_charged_mines` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_inner_land_mines_cooldown` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_inner_land_mines_damage` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_inner_land_mines_quantity` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_level_missing` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py` | `_parse_uw_tracks` | static | no | 4 | investigate |
| `uw_lib` | report-only | consumed_identifier | `tower_sim/audit/repo_audit.py` | `_check_modules` | report | no | 7 | classify |
| `uw_locked` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_uw_stat_inputs` | static | no | 4 | investigate |
| `uw_mapping` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_uw_stat_inputs` | static | no | 4 | investigate |
| `uw_name` | unknown | declared_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/run/optimizer_engine.py` | `_load_uw_plus_ladders`, `_load_uw_track_ladders`, `_load_uw_track_values` | static | no | 4 | investigate |
| `uw_plus` | unknown | emitted_key | `tower_sim/run/optimizer_engine.py` | `_load_uw_purchase_costs`, `_stone_actions` | mixed | no | 4 | investigate |
| `uw_plus_costs` | unknown | declared_identifier | `tower_sim/run/optimizer_engine.py` | `_load_uw_purchase_costs`, `_stone_actions` | mixed | no | 4 | investigate |
| `uw_plus_ladders` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/loaders/table_paths.py`, `tower_sim/run/optimizer_engine.py` | `_load_uw_plus_ladders`, `_load_uw_track_values` | static | no | 4 | investigate |
| `uw_plus_ladders_v1` | unknown | consumed_identifier | `tower_sim/loaders/table_paths.py`, `tower_sim/run/optimizer_engine.py` | `_load_uw_plus_ladders`, `_uw_plus_track_upgrade_action` | static | no | 4 | investigate |
| `uw_plus_locked` | unknown | declared_identifier | `tower_sim/run/optimizer_engine.py` | `_parse_uw_rows`, `_stone_actions` | mixed | no | 4 | investigate |
| `uw_plus_track_upgrade` | unknown | consumed_identifier | `tower_sim/run/optimizer_engine.py` | `_uw_plus_track_upgrade_action` | mixed | no | 4 | investigate |
| `uw_plus_tracks` | unknown | declared_identifier | `tower_sim/run/optimizer_engine.py` | `_parse_uw_rows`, `_stone_actions` | mixed | no | 4 | investigate |
| `uw_plus_unlock` | unknown | consumed_identifier | `tower_sim/run/optimizer_engine.py` | `_uw_plus_unlock_action` | mixed | no | 4 | investigate |
| `uw_plus_unlock_cost` | unknown | consumed_identifier | `tower_sim/run/optimizer_engine.py` | `_load_uw_purchase_costs` | mixed | no | 4 | investigate |
| `uw_plus_unlock_count` | unknown | consumed_identifier | `tower_sim/run/optimizer_engine.py` | `_load_uw_purchase_costs` | mixed | no | 4 | investigate |
| `uw_plus_unlocked_count` | unknown | declared_identifier | `tower_sim/run/optimizer_engine.py` | `_parse_uw_rows`, `_stone_actions` | mixed | no | 4 | investigate |
| `uw_poison_swamp_cooldown` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_poison_swamp_damage` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_poison_swamp_death_creep` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_poison_swamp_duration` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_purchase_costs` | unknown | declared_identifier | `tower_sim/loaders/table_paths.py`, `tower_sim/run/optimizer_engine.py` | `_load_uw_purchase_costs`, `_stone_actions` | static | no | 4 | investigate |
| `uw_purchase_costs_v1` | unknown | consumed_identifier | `tower_sim/loaders/table_paths.py`, `tower_sim/run/optimizer_engine.py` | `_load_uw_purchase_costs`, `_uw_plus_unlock_action`, `_uw_unlock_action` | static | no | 4 | investigate |
| `uw_scalar` | unknown | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `uw_section` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py` | `_level_from_provenance`, `_uw_provenance` | static | no | 4 | investigate |
| `uw_smart_missiles_cooldown` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_smart_missiles_cover_fire` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_smart_missiles_damage` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_smart_missiles_quantity` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_spotlight_angle` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_spotlight_light_range` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_spotlight_multiplier` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_spotlight_quantity` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_state` | unknown | declared_identifier | `tower_sim/run/optimizer_engine.py` | `_stone_actions` | mixed | no | 4 | investigate |
| `uw_table_level` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py` | `_load_uw_track_values` | static | no | 4 | investigate |
| `uw_table_value` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py` | `_load_uw_track_values` | static | no | 4 | investigate |
| `uw_tables_v2_1_2` | unknown | consumed_identifier | `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_track_costs` | unknown | declared_identifier | `tower_sim/run/optimizer_engine.py` | `_stone_actions` | mixed | no | 4 | investigate |
| `uw_track_ladders` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/loaders/table_paths.py`, `tower_sim/run/optimizer_engine.py` | `_load_uw_track_ladders`, `_load_uw_track_values` | static | no | 4 | investigate |
| `uw_track_ladders_v1` | unknown | consumed_identifier | `tower_sim/loaders/table_paths.py`, `tower_sim/run/optimizer_engine.py` | `_load_uw_track_ladders`, `_uw_track_upgrade_action` | static | no | 4 | investigate |
| `uw_track_upgrade` | unknown | consumed_identifier | `tower_sim/run/optimizer_engine.py` | `_uw_track_upgrade_action` | mixed | no | 4 | investigate |
| `uw_tracks` | unknown | declared_identifier | `tower_sim/registry/naming_contract.py`, `tower_sim/run/optimizer_engine.py` | `_build_named_entity_maps`, `_parse_uw_rows`, `_stone_actions` | static | no | 4 | investigate |
| `uw_unlock` | unknown | consumed_identifier | `tower_sim/run/optimizer_engine.py` | `_uw_unlock_action` | mixed | no | 4 | investigate |
| `uw_unlock_cost` | unknown | consumed_identifier | `tower_sim/run/optimizer_engine.py` | `_load_uw_purchase_costs` | mixed | no | 4 | investigate |
| `uw_unlock_count` | unknown | consumed_identifier | `tower_sim/run/optimizer_engine.py` | `_load_uw_purchase_costs` | mixed | no | 4 | investigate |
| `uw_unlocked_count` | unknown | declared_identifier | `tower_sim/run/optimizer_engine.py` | `_parse_uw_rows`, `_stone_actions` | mixed | no | 4 | investigate |
| `uw_unmapped` | unknown | consumed_identifier | `tower_sim/registry/naming_contract.py` | `validate_account_snapshot_naming` | static | no | 4 | investigate |
| `validate_boss_survivability_spec` | unknown | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | — | runtime | no | 4 | investigate |
| `value_percent_points` | unknown | consumed_identifier | `tower_sim/loaders/wiki/labs_eals_ehls.py`, `tower_sim/loaders/wiki/promote_labs_tables.py` | `_discover_lab_sources`, `_parse_value`, `get_eals_lab_pp` | static | no | 4 | investigate |
| `vault_pct` | alias | declared_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/engines/econ_current.py` | — | static | no | 7 | alias-map |
| `wa_card` | unknown | declared_identifier | `tower_sim/engines/wave_time.py` | `wa_reduction_from_snapshot` | runtime | no | 4 | investigate |
| `wall_current` | unknown | declared_identifier | `tower_sim/engines/combat/boss_survivability.py` | `_time_to_death` | runtime | no | 4 | investigate |
| `wall_fort_overheal_ratio` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `wall_fortification` | unknown | consumed_identifier | `tower_sim/loaders/ep_export_loader.py` | — | static | no | 4 | investigate |
| `wall_health` | target_stat | consumed_identifier | `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, … | `_apply_unique_effects`, `_compile_relic_stat_inputs` | static | target_stat | 10 | aligned |
| `wall_health_data` | unknown | declared_identifier | `tower_sim/engines/stat_input_compiler.py` | `compile_workshop_values_at_wave` | static | no | 4 | investigate |
| `wall_health_input` | unknown | declared_identifier | `tower_sim/engines/combat_stat_derivation.py` | `_wall_ratio_from_ids` | runtime | no | 4 | investigate |
| `wall_health_lab` | unknown | declared_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_wall_survivability_aliases`, `compile_workshop_values_at_wave` | static | no | 4 | investigate |
| `wall_health_ratio` | unknown | declared_identifier | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py` | `_compile_wall_survivability_aliases`, `_wall_ratio_from_ids`, `compile_workshop_values_at_wave` | mixed | no | 4 | investigate |
| `wall_health_ratio_input` | unknown | declared_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_wall_survivability_aliases` | static | no | 4 | investigate |
| `wall_health_regen_mult_x` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_unique_effects` | static | no | 4 | investigate |
| `wall_hp` | report-only | declared_and_emitted | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/engines/combat/boss_survivability.py`, … | `_apply_unique_effects`, `_build_reaches_stat_input`, `_compile_base_stat_inputs` | mixed | no | 7 | classify |
| `wall_lab_` | unknown | consumed_identifier | `tower_sim/loaders/wiki/promote_labs_tables.py` | `_discover_lab_sources` | static | no | 4 | investigate |
| `wall_lab_wall_health` | unknown | consumed_identifier | `tower_sim/loaders/wiki/labs.py` | — | static | no | 4 | investigate |
| `wall_lab_wall_regen` | unknown | consumed_identifier | `tower_sim/loaders/wiki/labs.py` | — | static | no | 4 | investigate |
| `wall_max` | unknown | declared_identifier | `tower_sim/engines/combat/boss_survivability.py` | `_time_to_death` | runtime | no | 4 | investigate |
| `wall_ratio` | unknown | declared_identifier | `tower_sim/engines/survivability_pipeline.py` | `_compile_base_stat_inputs` | mixed | no | 4 | investigate |
| `wall_rebuild` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/registry/stat_registry.py` | `_compile_relic_stat_inputs`, `default_registry` | static | no | 4 | investigate |
| `wall_regen` | target_stat | declared_and_emitted | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/engines/combat/boss_survivability.py`, … | `_apply_unique_effects`, `_build_reaches_stat_input`, `_compile_base_stat_inputs` | mixed | target_stat | 10 | split |
| `wall_regen_blocked` | unknown | declared_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_wall_survivability_aliases`, `compile_workshop_values_at_wave` | static | no | 4 | investigate |
| `wall_regen_data` | unknown | declared_identifier | `tower_sim/engines/stat_input_compiler.py` | `compile_workshop_values_at_wave` | static | no | 4 | investigate |
| `wall_regen_entry` | unknown | declared_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_wall_survivability_aliases`, `compile_workshop_values_at_wave` | static | no | 4 | investigate |
| `wall_regen_input` | unknown | declared_identifier | `tower_sim/engines/combat_stat_derivation.py` | `_wall_ratio_from_ids` | runtime | no | 4 | investigate |
| `wall_regen_lab` | unknown | declared_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_wall_survivability_aliases`, `compile_workshop_values_at_wave` | static | no | 4 | investigate |
| `wall_regen_per_hit` | unknown | declared_identifier | `tower_sim/engines/combat/boss_survivability.py` | `_time_to_death` | runtime | no | 4 | investigate |
| `wall_regen_ratio` | unknown | declared_identifier | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, … | `_compile_base_stat_inputs`, `_compile_wall_survivability_aliases`, `_wall_ratio_from_ids` | mixed | no | 4 | investigate |
| `wall_regen_ratio_input` | unknown | declared_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_wall_survivability_aliases` | static | no | 4 | investigate |
| `wall_thorns_entry` | unknown | declared_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_wall_survivability_aliases`, `compile_workshop_values_at_wave` | static | no | 4 | investigate |
| `wall_thorns_lvl` | unknown | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | — | static | no | 4 | investigate |
| `wall_thorns_mult` | alias | emitted_key | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `_compile_wall_survivability_aliases`, `compile_workshop_values_at_wave`, `default_registry` | static | no | 7 | alias-map |
| `wave_accel_mastery_lvl` | unknown | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `wave_actual` | unknown | declared_identifier | `tower_sim/loaders/bc_heat_loader.py` | `_load_tournament_heat_values`, `value_at` | static | no | 4 | investigate |
| `wave_attack_index` | runtime | emitted_key | `tower_sim/engines/stat_engine.py`, `tower_sim/engines/stat_snapshots.py`, `tower_sim/registry/combat_stat_contract.py`, … | `_append_wave_state_inputs`, `_build_reaches_stat_input`, `_resolve_at_wave_value` | static | no | 7 | classify |
| `wave_damage` | unknown | declared_and_emitted | `tower_sim/engines/combat/boss_engine.py`, `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/survivability_pipeline.py` | `_missing_inputs`, `_resolve_survivability_verdict`, `resolve_canonical_wave_damage` | runtime | no | 4 | investigate |
| `wave_damage_error` | unknown | emitted_key | `tower_sim/engines/combat_stat_derivation.py` | `resolve_canonical_wave_damage` | runtime | no | 4 | investigate |
| `wave_damage_strict` | report-only | consumed_identifier | `tower_sim/audit/status.py` | `_components` | report | no | 7 | classify |
| `wave_damage_table` | unknown | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | `resolve_canonical_wave_damage`, `resolve_canonical_wave_damage_for_attack_wave` | runtime | no | 4 | investigate |
| `wave_damage_tier` | unknown | declared_and_emitted | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/run/problem_spec.py`, `tower_sim/run/spec_loader.py` | `_parse_scenario`, `resolve_canonical_wave_damage`, `resolve_canonical_wave_damage_for_attack_wave` | runtime | no | 4 | investigate |
| `wave_damage_wave` | runtime | emitted_key | `tower_sim/engines/combat_stat_derivation.py` | `resolve_canonical_wave_damage` | runtime | no | 7 | classify |
| `wave_engine` | report-only | consumed_identifier | `tower_sim/audit/status.py`, `tower_sim/engines/stat_engine.py` | `_append_wave_state_inputs`, `_components` | report | no | 7 | classify |
| `wave_health_index` | runtime | emitted_key | `tower_sim/engines/stat_engine.py`, `tower_sim/engines/stat_snapshots.py`, `tower_sim/registry/combat_stat_contract.py`, … | `_append_wave_state_inputs`, `_build_reaches_stat_input`, `_resolve_at_wave_value` | static | no | 7 | classify |
| `wave_inputs` | unknown | declared_identifier | `tower_sim/engines/stat_pipeline.py` | `build_canonical_stat_pipeline_for_problem_spec` | mixed | no | 4 | investigate |
| `wave_limit` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py` | `compile_workshop_values_at_wave` | static | no | 4 | investigate |
| `wave_max` | unknown | declared_identifier | `tower_sim/loaders/ep_export_loader.py`, `tower_sim/run/problem_spec.py`, `tower_sim/run/spec_loader.py` | `_parse_scenario`, `extract_max_wave_targets` | static | no | 4 | investigate |
| `wave_probe` | unknown | declared_identifier | `tower_sim/run/problem_spec.py`, `tower_sim/run/spec_loader.py` | `_parse_scenario` | mixed | no | 4 | investigate |
| `wave_raw` | unknown | declared_identifier | `tower_sim/loaders/perk_timeline_loader.py` | `_parse_row` | static | no | 4 | investigate |
| `wave_row` | unknown | declared_identifier | `tower_sim/engines/stat_pipeline.py` | `resolve_wave_snapshot_for_problem_spec` | mixed | no | 4 | investigate |
| `wave_rows` | unknown | consumed_identifier | `tower_sim/engines/stat_pipeline.py` | `resolve_wave_snapshot_for_problem_spec` | mixed | no | 4 | investigate |
| `wave_skip_mastery_lvl` | unknown | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `wave_snapshot` | unknown | consumed_identifier | `tower_sim/engines/stat_pipeline.py` | `resolve_wave_snapshot_for_problem_spec` | mixed | no | 4 | investigate |
| `wave_snapshot_error` | unknown | emitted_key | `tower_sim/engines/stat_pipeline.py` | `resolve_wave_snapshot_for_problem_spec` | mixed | no | 4 | investigate |
| `wave_snapshot_inputs` | unknown | consumed_identifier | `tower_sim/engines/stat_pipeline.py` | `resolve_wave_snapshot_for_problem_spec` | mixed | no | 4 | investigate |
| `wave_state` | unknown | declared_and_emitted | `tower_sim/engines/stat_pipeline.py`, `tower_sim/engines/stat_snapshots.py`, `tower_sim/engines/survivability_pipeline.py` | `build_at_wave_snapshot`, `build_canonical_stat_pipeline_for_problem_spec`, `build_survivability_report` | mixed | no | 4 | investigate |
| `wave_state_from_row` | unknown | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | — | runtime | no | 4 | investigate |
| `wave_tier` | unknown | declared_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/survivability_pipeline.py` | `_resolve_wave_damage`, `resolve_canonical_wave_damage`, `resolve_canonical_wave_damage_for_attack_wave` | runtime | no | 4 | investigate |
| `wave_time` | runtime | declared_identifier | `tower_sim/engines/econ_current.py` | `econ_current` | mixed | no | 7 | classify |
| `wave_time_boost` | runtime | consumed_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 7 | classify |
| `waves_required_lab` | unknown | declared_identifier | `tower_sim/engines/perk_timeline_generator.py` | `load_policy` | mixed | no | 4 | investigate |
| `waves_skipped` | unknown | consumed_identifier | `tower_sim/engines/free_upgrades.py` | `expected_upgrades_per_wave` | mixed | no | 4 | investigate |
| `waves_skipped_per_wave` | runtime | consumed_identifier | `tower_sim/engines/workshop_progression.py` | `simulate_workshop_progression` | mixed | no | 7 | classify |
| `waves_to_end` | unknown | declared_identifier | `tower_sim/engines/workshop_progression.py` | `simulate_workshop_progression` | mixed | no | 4 | investigate |
| `weight_percent` | unknown | declared_identifier | `tower_sim/loaders/perk_tables.py` | `load_perk_pool_weights` | static | no | 4 | investigate |
| `wmax_wave_relative` | runtime | consumed_identifier | `tower_sim/audit/max_wave_ep_parity.py` | `_resolve_wmax_tolerance` | runtime | no | 7 | classify |
| `workshop_attack_speed` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_bounce_shot_chance` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/engines/survivability_pipeline.py`, … | `default_registry` | static | no | 4 | investigate |
| `workshop_bounce_shot_range` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_cash_bonus` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/registry/stat_registry.py` | `_apply_card_effects`, `default_registry` | static | no | 4 | investigate |
| `workshop_cash_per_wave` | runtime | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 7 | classify |
| `workshop_coins_per_kill_bonus` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/engines/survivability_pipeline.py`, … | `_apply_card_effects`, `default_registry` | static | no | 4 | investigate |
| `workshop_coins_per_wave` | runtime | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 7 | classify |
| `workshop_critical_chance` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/loaders/ep_export_loader.py`, … | `default_registry` | static | no | 4 | investigate |
| `workshop_critical_factor` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_damage` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/loaders/ep_export_loader.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_damage_per_meter` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/loaders/ep_export_loader.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_defense_absolute` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/loaders/ep_export_loader.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_defense_percent` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_enemy_attack_level_skip` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `_parse_workshop_enhancement_multipliers`, `default_registry` | static | no | 4 | investigate |
| `workshop_enemy_health_level_skip` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `_parse_workshop_enhancement_multipliers`, `default_registry` | static | no | 4 | investigate |
| `workshop_enemy_level_skip` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_free_attack_upgrade` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/loaders/ep_export_loader.py`, … | `_free_upgrade_chances`, `default_registry` | static | no | 4 | investigate |
| `workshop_free_defense_upgrade` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/loaders/ep_export_loader.py`, … | `_free_upgrade_chances`, `default_registry` | static | no | 4 | investigate |
| `workshop_health` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_health_regen` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_knockback_chance` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_land_mine` | unknown | consumed_identifier | `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_land_mine_chance` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/engines/survivability_pipeline.py`, … | `default_registry` | static | no | 4 | investigate |
| `workshop_land_mine_damage` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_land_mine_radius` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_level_to_chance` | unknown | consumed_identifier | `tower_sim/loaders/wiki/enemy_level_skip.py` | — | static | no | 4 | investigate |
| `workshop_multishot_chance` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/loaders/ep_export_loader.py`, … | `default_registry` | static | no | 4 | investigate |
| `workshop_multishot_targets` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/engines/survivability_pipeline.py`, … | `default_registry` | static | no | 4 | investigate |
| `workshop_orb_size` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_orb_speed` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_orbs` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_package_chance` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/engines/survivability_pipeline.py`, … | `_apply_card_effects`, `default_registry` | static | no | 4 | investigate |
| `workshop_range_meters` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/engines/survivability_pipeline.py`, … | `_apply_card_effects`, `default_registry` | static | no | 4 | investigate |
| `workshop_rapid_fire_chance` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/loaders/ep_export_loader.py`, … | `default_registry` | static | no | 4 | investigate |
| `workshop_rapid_fire_duration` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/loaders/ep_export_loader.py`, … | `default_registry` | static | no | 4 | investigate |
| `workshop_recovery_packages` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/loaders/ep_export_loader.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_rend_armor_chance` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_rend_armor_mult` | alias | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/loaders/ep_export_loader.py`, … | `default_registry` | static | no | 7 | alias-map |
| `workshop_shockwave` | unknown | consumed_identifier | `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_shockwave_frequency` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_shockwave_size` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_super_crit_chance` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_super_crit_mult` | alias | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 7 | alias-map |
| `workshop_super_crit_mult_alt` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_thorn_damage` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_thorns` | unknown | declared_identifier | `tower_sim/engines/survivability_pipeline.py` | `_resolve_thorns_inputs` | mixed | no | 4 | investigate |
| `workshop_wall_fortification` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_wall_health` | unknown | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, … | `_compile_wall_survivability_aliases`, `_wall_ratio_from_ids`, `compile_workshop_values_at_wave` | mixed | no | 4 | investigate |
| `workshop_wall_rebuild` | unknown | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_wall_regen` | unknown | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `_compile_wall_survivability_aliases`, `_wall_ratio_from_ids`, `compile_workshop_values_at_wave` | mixed | no | 4 | investigate |

## 3. Collision report
### 3.1 One repo_name used across multiple semantics/stages
- `absolute_chance_subtract` appears across mixed surfaces/stages; paths include `tower_sim/engines/tier_rule_apply.py`.
- `assist_mult` appears across mixed surfaces/stages; paths include `tower_sim/engines/econ_current.py`.
- `at_wave_inputs` appears across mixed surfaces/stages; paths include `tower_sim/engines/stat_snapshots.py`.
- `at_wave_missing` appears across mixed surfaces/stages; paths include `tower_sim/engines/stat_pipeline.py`.
- `at_wave_stage` appears across mixed surfaces/stages; paths include `tower_sim/engines/stat_pipeline.py`.
- `at_wave_stage_missing` appears across mixed surfaces/stages; paths include `tower_sim/engines/stat_pipeline.py`.
- `at_wave_stage_skipped` appears across mixed surfaces/stages; paths include `tower_sim/engines/stat_pipeline.py`.
- `at_wave_stats` appears across mixed surfaces/stages; paths include `tower_sim/engines/stat_snapshots.py`.
- `attack` appears across mixed surfaces/stages; paths include `tower_sim/engines/combat/boss_survivability.py`, `tower_sim/engines/combat/combat_engine.py`, `tower_sim/engines/free_upgrades.py`, `tower_sim/engines/stat_input_compiler.py`.
- `base_cooldown` appears across mixed surfaces/stages; paths include `tower_sim/engines/econ_current.py`.
- `base_duration` appears across mixed surfaces/stages; paths include `tower_sim/engines/econ_current.py`.
- `bh_coin_bonus_lvl` appears across mixed surfaces/stages; paths include `tower_sim/engines/econ_current.py`.
- `bonus_multiplier` appears across mixed surfaces/stages; paths include `tower_sim/engines/econ_current.py`.
- `boss_interval_waves` appears across mixed surfaces/stages; paths include `tower_sim/engines/tier_rule_apply.py`.
- `bot_amplify_bonus` appears across mixed surfaces/stages; paths include `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py`.
- `bot_amplify_cooldown` appears across mixed surfaces/stages; paths include `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py`.
- `bot_amplify_duration` appears across mixed surfaces/stages; paths include `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py`.
- `bot_flame_cooldown` appears across mixed surfaces/stages; paths include `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py`.
- `bot_flame_damage` appears across mixed surfaces/stages; paths include `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py`.
- `bot_flame_damage_reduction` appears across mixed surfaces/stages; paths include `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py`.
- `bot_golden_bonus` appears across mixed surfaces/stages; paths include `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py`.
- `bot_golden_cooldown` appears across mixed surfaces/stages; paths include `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py`.
- `bot_golden_duration` appears across mixed surfaces/stages; paths include `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py`.
- `build_edamage_stat_inputs` appears across mixed surfaces/stages; paths include `tower_sim/engines/edamage_pipeline.py`.
- `card_id` appears across mixed surfaces/stages; paths include `tower_sim/run/optimizer_patch.py`.
- `card_mastery` appears across mixed surfaces/stages; paths include `tower_sim/run/optimizer_engine.py`.
- `card_name` appears across mixed surfaces/stages; paths include `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/loaders/account_snapshot_compiler.py`.
- `card_presets` appears across mixed surfaces/stages; paths include `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/loaders/account_snapshot_loader.py`.
- `cards_rare` appears across mixed surfaces/stages; paths include `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tower_sim/engines/combat/boss_engine.py`, `tower_sim/loaders/wiki/cards.py`.
- `coin_actions_not_implemented` appears across mixed surfaces/stages; paths include `tower_sim/run/optimizer_engine.py`.
- `coins_card` appears across mixed surfaces/stages; paths include `tower_sim/engines/econ_current.py`.
- `coins_mastery_lvl` appears across mixed surfaces/stages; paths include `tower_sim/engines/econ_current.py`.
- `coins_per_kill_bonus_lvl` appears across mixed surfaces/stages; paths include `tower_sim/engines/econ_current.py`.
- `coins_per_kill_mult` appears across mixed surfaces/stages; paths include `tower_sim/engines/econ_current.py`.
- `compute_edamage_outputs` appears across mixed surfaces/stages; paths include `tower_sim/engines/edamage_pipeline.py`.
- `crit_multiplier` appears across mixed surfaces/stages; paths include `tower_sim/engines/edamage_pipeline.py`.
- `damage` appears across mixed surfaces/stages; paths include `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tower_sim/audit/status.py`, `tower_sim/engines/combat/boss_engine.py`, `tower_sim/engines/combat/boss_survivability.py`.
- `def_pct` appears across mixed surfaces/stages; paths include `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`.
- `dw_coin_bonus_lvl` appears across mixed surfaces/stages; paths include `tower_sim/engines/econ_current.py`.
- `eals_ramp` appears across mixed surfaces/stages; paths include `tower_sim/run/problem_spec.py`, `tower_sim/run/spec_loader.py`.
- `edamage` appears across mixed surfaces/stages; paths include `tower_sim/engines/edamage_pipeline.py`.
- `ehls_ramp` appears across mixed surfaces/stages; paths include `tower_sim/run/problem_spec.py`, `tower_sim/run/spec_loader.py`.
- `enemy_level_skip_reduction` appears across mixed surfaces/stages; paths include `tower_sim/engines/tier_rule_apply.py`.
- `enhancement_multiplier` appears across mixed surfaces/stages; paths include `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_engine.py`, `tower_sim/engines/stat_input_compiler.py`.
- `epd_crit_chance` appears across mixed surfaces/stages; paths include `tower_sim/engines/edamage_formulas.py`.
- `epd_critical` appears across mixed surfaces/stages; paths include `tower_sim/engines/edamage_formulas.py`.
- `equipped_cards` appears across mixed surfaces/stages; paths include `tower_sim/run/api.py`.
- `extra_orb_mastery_lvl` appears across mixed surfaces/stages; paths include `tower_sim/engines/econ_current.py`.
- `final_wave` appears across mixed surfaces/stages; paths include `tower_sim/engines/perk_timeline_generator.py`.
- `free_attack_upgrade_rate` appears across mixed surfaces/stages; paths include `tower_sim/engines/econ_current.py`.
- `generator_module` appears across mixed surfaces/stages; paths include `tower_sim/engines/econ_current.py`.
- `gold_bot_cooldown_lvl` appears across mixed surfaces/stages; paths include `tower_sim/engines/econ_current.py`.
- `gold_bot_duration_lvl` appears across mixed surfaces/stages; paths include `tower_sim/engines/econ_current.py`.
- `gt_duration_lvl` appears across mixed surfaces/stages; paths include `tower_sim/engines/econ_current.py`.
- `has_coins_perk` appears across mixed surfaces/stages; paths include `tower_sim/engines/econ_current.py`.
- `has_module` appears across mixed surfaces/stages; paths include `tower_sim/engines/econ_current.py`.
- `health` appears across mixed surfaces/stages; paths include `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/audit/wiring_health_check.py`, `tower_sim/engines/combat/combat_engine.py`, `tower_sim/engines/modules.py`.
- `knockback_multiplier` appears across mixed surfaces/stages; paths include `tower_sim/engines/tier_rule_apply.py`.
- `locked_uws` appears across mixed surfaces/stages; paths include `tower_sim/run/optimizer_engine.py`.
- `mastery_mult` appears across mixed surfaces/stages; paths include `tower_sim/engines/econ_current.py`.
- `max_wave_ids` appears across mixed surfaces/stages; paths include `tower_sim/engines/statbook_builder.py`.
- `max_wave_latest` appears across mixed surfaces/stages; paths include `tower_sim/run/runner.py`.
- `max_wave_runner` appears across mixed surfaces/stages; paths include `tower_sim/run/runner.py`.
- `missing_at_wave` appears across mixed surfaces/stages; paths include `tower_sim/engines/stat_pipeline.py`.
- `missing_required_at_wave_stats` appears across mixed surfaces/stages; paths include `tower_sim/engines/stat_pipeline.py`.
- `missing_wave` appears across mixed surfaces/stages; paths include `tower_sim/engines/stat_pipeline.py`.
- `missing_wave_state` appears across mixed surfaces/stages; paths include `tower_sim/engines/stat_pipeline.py`.
- `module_contribution_ledger` appears across mixed surfaces/stages; paths include `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/engines/survivability_pipeline.py`.
- `module_id` appears across mixed surfaces/stages; paths include `tower_sim/run/optimizer_patch.py`.
- `module_layer_gaps` appears across mixed surfaces/stages; paths include `tower_sim/engines/survivability_pipeline.py`.
- `module_presets` appears across mixed surfaces/stages; paths include `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/loaders/account_snapshot_compiler.py`, `tower_sim/loaders/account_snapshot_loader.py`.
- `module_primary_effect` appears across mixed surfaces/stages; paths include `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`.
- `module_rules` appears across mixed surfaces/stages; paths include `tower_sim/engines/modules.py`.
- `module_substat_unmapped` appears across mixed surfaces/stages; paths include `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/registry/naming_contract.py`.
- `module_summary` appears across mixed surfaces/stages; paths include `tower_sim/engines/survivability_pipeline.py`.
- `module_unique_unmapped` appears across mixed surfaces/stages; paths include `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`.
- `multiplier_efficiency` appears across mixed surfaces/stages; paths include `tower_sim/engines/modules.py`.
- `multiplier_level` appears across mixed surfaces/stages; paths include `tower_sim/run/optimizer_engine.py`.
- `next_percent` appears across mixed surfaces/stages; paths include `tower_sim/run/optimizer_engine.py`.
- `next_uw_plus_unlock_cost` appears across mixed surfaces/stages; paths include `tower_sim/run/optimizer_engine.py`.
- `next_uw_unlock_cost` appears across mixed surfaces/stages; paths include `tower_sim/run/optimizer_engine.py`.
- `next_wave` appears across mixed surfaces/stages; paths include `tower_sim/engines/perk_timeline_generator.py`.
- `perk_multiplier` appears across mixed surfaces/stages; paths include `tower_sim/engines/edamage_pipeline.py`.
- `resolve_card_mastery_value` appears across mixed surfaces/stages; paths include `tower_sim/engines/edamage_pipeline.py`.
- `resolve_damage_perk_multiplier` appears across mixed surfaces/stages; paths include `tower_sim/engines/edamage_pipeline.py`.
- `spotlight_coin_bonus_lvl` appears across mixed surfaces/stages; paths include `tower_sim/engines/econ_current.py`.
- `target_wave` appears across mixed surfaces/stages; paths include `tower_sim/engines/perk_timeline_generator.py`, `tower_sim/engines/stat_pipeline.py`.
- `thorns_damage_mult` appears across mixed surfaces/stages; paths include `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/engines/tier_rule_apply.py`.
- `thorns_mult` appears across mixed surfaces/stages; paths include `tower_sim/engines/survivability_pipeline.py`.
- `time_multiplier_mode` appears across mixed surfaces/stages; paths include `tower_sim/engines/econ_current.py`.
- `tower_crit_factor` appears across mixed surfaces/stages; paths include `tower_sim/engines/edamage_pipeline.py`.
- `tower_damage` appears across mixed surfaces/stages; paths include `tower_sim/engines/combat/combat_engine.py`, `tower_sim/engines/edamage_pipeline.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`.
- `tower_regen` appears across mixed surfaces/stages; paths include `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/engines/combat/boss_engine.py`, `tower_sim/engines/combat/boss_survivability.py`.
- `uw_` appears across mixed surfaces/stages; paths include `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/statbook_builder.py`, `tower_sim/registry/stat_registry.py`.
- `uw_costs` appears across mixed surfaces/stages; paths include `tower_sim/run/optimizer_engine.py`.
- `uw_ids` appears across mixed surfaces/stages; paths include `tower_sim/engines/statbook_builder.py`.
- `uw_plus` appears across mixed surfaces/stages; paths include `tower_sim/run/optimizer_engine.py`.
- `uw_plus_costs` appears across mixed surfaces/stages; paths include `tower_sim/run/optimizer_engine.py`.
- `uw_plus_locked` appears across mixed surfaces/stages; paths include `tower_sim/run/optimizer_engine.py`.
- `uw_plus_track_upgrade` appears across mixed surfaces/stages; paths include `tower_sim/run/optimizer_engine.py`.
- `uw_plus_tracks` appears across mixed surfaces/stages; paths include `tower_sim/run/optimizer_engine.py`.
- `uw_plus_unlock` appears across mixed surfaces/stages; paths include `tower_sim/run/optimizer_engine.py`.
- `uw_plus_unlock_cost` appears across mixed surfaces/stages; paths include `tower_sim/run/optimizer_engine.py`.
- `uw_plus_unlock_count` appears across mixed surfaces/stages; paths include `tower_sim/run/optimizer_engine.py`.
- `uw_plus_unlocked_count` appears across mixed surfaces/stages; paths include `tower_sim/run/optimizer_engine.py`.
- `uw_scalar` appears across mixed surfaces/stages; paths include `tower_sim/engines/econ_current.py`.
- `uw_state` appears across mixed surfaces/stages; paths include `tower_sim/run/optimizer_engine.py`.
- `uw_track_costs` appears across mixed surfaces/stages; paths include `tower_sim/run/optimizer_engine.py`.
- `uw_track_upgrade` appears across mixed surfaces/stages; paths include `tower_sim/run/optimizer_engine.py`.
- `uw_unlock` appears across mixed surfaces/stages; paths include `tower_sim/run/optimizer_engine.py`.
- `uw_unlock_cost` appears across mixed surfaces/stages; paths include `tower_sim/run/optimizer_engine.py`.
- `uw_unlock_count` appears across mixed surfaces/stages; paths include `tower_sim/run/optimizer_engine.py`.
- `uw_unlocked_count` appears across mixed surfaces/stages; paths include `tower_sim/run/optimizer_engine.py`.
- `wall_health_ratio` appears across mixed surfaces/stages; paths include `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`.
- `wall_hp` appears across mixed surfaces/stages; paths include `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/engines/combat/boss_survivability.py`, `tower_sim/engines/combat_stat_derivation.py`.
- `wall_ratio` appears across mixed surfaces/stages; paths include `tower_sim/engines/survivability_pipeline.py`.
- `wall_regen` appears across mixed surfaces/stages; paths include `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/engines/combat/boss_survivability.py`, `tower_sim/engines/combat_stat_derivation.py`.
- `wall_regen_ratio` appears across mixed surfaces/stages; paths include `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`.
- `wave_accel_mastery_lvl` appears across mixed surfaces/stages; paths include `tower_sim/engines/econ_current.py`.
- `wave_inputs` appears across mixed surfaces/stages; paths include `tower_sim/engines/stat_pipeline.py`.

### 3.2 Multiple repo_names for one semantic concept (heuristic groups)
- Concept `critical_chance` has variants: `crit_chance`, `critical_chance`.
- Concept `defense_percent` has variants: `defense_pct`, `defense_percent`.
- Concept `wall_health` has variants: `wall_health`, `wall_hp`.

### 3.3 Identifiers used in both static and runtime contexts
- `attack` appears in static and runtime-related paths.
- `bot_amplify_bonus` appears in static and runtime-related paths.
- `bot_amplify_cooldown` appears in static and runtime-related paths.
- `bot_amplify_duration` appears in static and runtime-related paths.
- `bot_flame_cooldown` appears in static and runtime-related paths.
- `bot_flame_damage` appears in static and runtime-related paths.
- `bot_flame_damage_reduction` appears in static and runtime-related paths.
- `bot_golden_bonus` appears in static and runtime-related paths.
- `bot_golden_cooldown` appears in static and runtime-related paths.
- `bot_golden_duration` appears in static and runtime-related paths.
- `card_name` appears in static and runtime-related paths.
- `card_presets` appears in static and runtime-related paths.
- `cards_rare` appears in static and runtime-related paths.
- `damage` appears in static and runtime-related paths.
- `def_pct` appears in static and runtime-related paths.
- `enhancement_multiplier` appears in static and runtime-related paths.
- `health` appears in static and runtime-related paths.
- `module_contribution_ledger` appears in static and runtime-related paths.
- `module_presets` appears in static and runtime-related paths.
- `module_primary_effect` appears in static and runtime-related paths.
- `module_substat_unmapped` appears in static and runtime-related paths.
- `module_unique_unmapped` appears in static and runtime-related paths.
- `thorns_damage_mult` appears in static and runtime-related paths.
- `tower_damage` appears in static and runtime-related paths.
- `tower_regen` appears in static and runtime-related paths.
- `uw_` appears in static and runtime-related paths.
- `wall_health_ratio` appears in static and runtime-related paths.
- `wall_hp` appears in static and runtime-related paths.
- `wall_regen` appears in static and runtime-related paths.
- `wall_regen_ratio` appears in static and runtime-related paths.
- `workshop_wall_health` appears in static and runtime-related paths.
- `workshop_wall_regen` appears in static and runtime-related paths.

### 3.4 Report-only names masquerading as canonical stats
- `boss_engine` appears report-only/non-ledger; classify before canonical use.
- `boss_survivability` appears report-only/non-ledger; classify before canonical use.
- `cards_lib` appears report-only/non-ledger; classify before canonical use.
- `def_pct` appears report-only/non-ledger; classify before canonical use.
- `defense_percent` appears report-only/non-ledger; classify before canonical use.
- `enhancement_multiplier` appears report-only/non-ledger; classify before canonical use.
- `key_modules` appears report-only/non-ledger; classify before canonical use.
- `module_name` appears report-only/non-ledger; classify before canonical use.
- `modules_lib` appears report-only/non-ledger; classify before canonical use.
- `modules_library` appears report-only/non-ledger; classify before canonical use.
- `regen` appears report-only/non-ledger; classify before canonical use.
- `skipped_missing_targets` appears report-only/non-ledger; classify before canonical use.
- `test_boss_engine` appears report-only/non-ledger; classify before canonical use.
- `test_boss_survivability` appears report-only/non-ledger; classify before canonical use.
- `tier_multiplier` appears report-only/non-ledger; classify before canonical use.
- `tower_regen` appears report-only/non-ledger; classify before canonical use.
- `uw_lib` appears report-only/non-ledger; classify before canonical use.
- `wall_hp` appears report-only/non-ledger; classify before canonical use.
- `wave_damage_strict` appears report-only/non-ledger; classify before canonical use.
- `wave_engine` appears report-only/non-ledger; classify before canonical use.

## 4. Hotspot ranking
| rank | surface | risky_identifier_count |
|---:|---|---:|
| 1 | `tower_sim/engines/stat_input_compiler.py` | 199 |
| 2 | `tower_sim/registry/stat_registry.py` | 139 |
| 3 | `tower_sim/engines/survivability_pipeline.py` | 84 |
| 4 | `tower_sim/engines/combat_stat_derivation.py` | 80 |
| 5 | `tower_sim/engines/stat_pipeline.py` | 64 |
| 6 | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | 60 |
| 7 | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | 54 |
| 8 | `tower_sim/loaders/ep_export_loader.py` | 39 |
| 9 | `tower_sim/run/optimizer_engine.py` | 36 |
| 10 | `tower_sim/engines/econ_current.py` | 30 |
| 11 | `tables/meta/registry/ep_formulas/formula_library.yaml` | 30 |
| 12 | `tower_sim/engines/combat/boss_survivability.py` | 25 |
| 13 | `tower_sim/loaders/table_paths.py` | 25 |
| 14 | `tower_sim/registry/combat_stat_contract.py` | 24 |
| 15 | `tower_sim/engines/combat/boss_engine.py` | 22 |

## 5. Recommendations
1. Freeze this inventory as the baseline namespace map for rename planning.
2. Classify all `action=investigate` identifiers before any refactor; do not infer equivalence.
3. For `action=split`, separate static canonical names from runtime/report aliases first.
4. Build an explicit alias map document from `alias-map` rows; keep runtime unchanged until approved rename phase.
5. Start future rename work at highest-risk surfaces (`stat_input_compiler`, `survivability_pipeline`, `stat_pipeline`) one boundary at a time.
