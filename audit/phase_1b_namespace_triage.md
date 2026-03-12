# Phase 1B.2 Namespace Triage

## Files inspected
- `audit/phase_1b_stat_surface_inventory.md`
- `audit/reference/tower_sim_3_handover/towersim_static_ledger_latest.csv`
- `audit/reference/tower_sim_3_handover/towersim_static_ledger_naming_contract_v1_10.md`
- `audit/reference/tower_sim_3_handover/towersim_v1_handover_pack.md`
- `CODEX_HANDOFF_V1_FULL.md`
- `STATUS_V1.yaml`
- `CONTRACT.md`

## 1. Summary counts by bucket
- Total identifiers triaged: **633**
- `canonical_target_stat`: 23
- `canonical_contributor_input`: 0
- `approved_alias`: 20
- `derived_stat`: 0
- `runtime_state_field`: 200
- `report_or_audit_field`: 34
- `table_or_config_symbol`: 121
- `implementation_artifact`: 4
- `legacy_or_unresolved`: 231

## 2. Reclassified inventory table
| repo_name | prior category | primary bucket | semantic_role | source_surface | owner_function(s) | stage | ledger_match | confidence (0-10) | action |
|---|---|---|---|---|---|---|---|---:|---|
| `absolute_chance_subtract` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/tier_rule_apply.py` | — | mixed | no | 4 | investigate |
| `assist_mult` | alias | approved_alias | declared_identifier | `tower_sim/engines/econ_current.py` | `EPG_MODULE_BONUS` | mixed | no | 7 | split |
| `assist_multiplier` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_armor_module_multiplier` | static | no | 4 | investigate |
| `at_wave` | runtime | runtime_state_field | declared_identifier | `tower_sim/engines/survivability_pipeline.py`, `tower_sim/registry/stat_registry.py` | `build_survivability_report` | static | no | 7 | classify |
| `at_wave_inputs` | runtime | runtime_state_field | declared_identifier | `tower_sim/engines/stat_snapshots.py` | `build_at_wave_snapshot` | mixed | no | 7 | classify |
| `at_wave_missing` | runtime | runtime_state_field | declared_identifier | `tower_sim/engines/stat_pipeline.py` | `build_canonical_stat_pipeline_for_problem_spec` | mixed | no | 7 | classify |
| `at_wave_snapshot` | runtime | runtime_state_field | declared_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/engines/survivability_pipeline.py` | `build_canonical_stat_pipeline_for_problem_spec`, `build_survivability_report`, `derive_canonical_combat_snapshot` | runtime | no | 7 | classify |
| `at_wave_stage` | runtime | runtime_state_field | declared_identifier | `tower_sim/engines/stat_pipeline.py` | `build_canonical_stat_pipeline_for_problem_spec` | mixed | no | 7 | classify |
| `at_wave_stage_missing` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_pipeline.py` | `build_canonical_stat_pipeline_for_problem_spec` | mixed | no | 7 | classify |
| `at_wave_stage_skipped` | runtime | runtime_state_field | emitted_key | `tower_sim/engines/stat_pipeline.py` | `build_canonical_stat_pipeline_for_problem_spec` | mixed | no | 7 | classify |
| `at_wave_stats` | runtime | runtime_state_field | declared_identifier | `tower_sim/engines/stat_snapshots.py` | `build_at_wave_snapshot` | mixed | no | 7 | classify |
| `attack` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/combat/boss_survivability.py`, `tower_sim/engines/combat/combat_engine.py`, `tower_sim/engines/free_upgrades.py`, … | `_free_upgrade_chances`, `_parse_boss_stats`, `_workshop_category` | mixed | no | 4 | investigate |
| `attack_interval` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_survivability.py`, `tower_sim/run/problem_spec.py`, `tower_sim/run/spec_loader.py` | `_parse_boss_stats` | runtime | no | 4 | investigate |
| `attack_speed` | target_stat | canonical_target_stat | declared_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/engines/edamage_formulas.py`, … | `_apply_card_effects`, `_compile_relic_stat_inputs`, `build_edamage_stat_inputs` | static | target_stat | 10 | aligned |
| `base_cooldown` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `base_cooldown_s` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/uptime.py` | `build_gcomp_activation_intervals` | runtime | no | 4 | investigate |
| `base_duration` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `bc_mult` | alias | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | — | static | no | 7 | alias-map |
| `bh_coin_bonus_lvl` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `bonus_multiplier` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `boss_attack` | unknown | runtime_state_field | declared_and_emitted | `tower_sim/engines/combat/boss_survivability.py`, `tower_sim/engines/combat_stat_derivation.py` | `resolve_boss_fight`, `validate_boss_survivability_spec` | runtime | no | 4 | investigate |
| `boss_attack_interval` | unknown | runtime_state_field | emitted_key | `tower_sim/engines/combat_stat_derivation.py` | `validate_boss_survivability_spec` | runtime | no | 4 | investigate |
| `boss_attack_mult` | alias | runtime_state_field | consumed_identifier | `tower_sim/engines/combat/boss_params_loader.py` | `load_bc_params` | runtime | no | 7 | alias-map |
| `boss_engine` | report-only | report_or_audit_field | consumed_identifier | `tower_sim/audit/status.py`, `tower_sim/engines/combat/__init__.py` | `_components` | runtime | no | 7 | classify |
| `boss_enrage_mult` | alias | runtime_state_field | emitted_key | `tower_sim/engines/combat_stat_derivation.py` | `validate_boss_survivability_spec` | runtime | no | 7 | alias-map |
| `boss_hit_interval` | unknown | table_or_config_symbol | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 4 | investigate |
| `boss_hit_interval_v1` | unknown | table_or_config_symbol | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 4 | investigate |
| `boss_hp` | unknown | runtime_state_field | emitted_key | `tower_sim/engines/combat_stat_derivation.py` | `validate_boss_survivability_spec` | runtime | no | 4 | investigate |
| `boss_hp_frac_damage` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | `evaluate` | runtime | no | 4 | investigate |
| `boss_hp_frac_damage_per_hit` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | — | runtime | no | 4 | investigate |
| `boss_hp_mult` | alias | runtime_state_field | consumed_identifier | `tower_sim/engines/combat/boss_params_loader.py` | `load_bc_params` | runtime | no | 7 | alias-map |
| `boss_hp_remaining_mult` | alias | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | `evaluate` | runtime | no | 7 | alias-map |
| `boss_hp_remaining_mult_per_hit` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | — | runtime | no | 4 | investigate |
| `boss_interval_waves` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/tier_rule_apply.py` | — | mixed | no | 7 | classify |
| `boss_kills_tower` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat/boss_survivability.py` | `resolve_boss_fight` | runtime | no | 4 | investigate |
| `boss_params_loader` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat/__init__.py` | — | runtime | no | 4 | investigate |
| `boss_survivability` | report-only | report_or_audit_field | declared_identifier | `tower_sim/audit/status.py`, `tower_sim/engines/combat/__init__.py`, `tower_sim/engines/combat_stat_derivation.py`, … | `_components`, `_parse_boss_survivability`, `_parse_scenario` | runtime | no | 7 | classify |
| `boss_survivability_invalid` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | `validate_boss_survivability_spec` | runtime | no | 4 | investigate |
| `boss_wall_thorns_frac_v1` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | — | static | no | 4 | investigate |
| `bot_amplify_bonus` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry`, `resolve_runtime_bot_effects` | mixed | no | 4 | investigate |
| `bot_amplify_cooldown` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry`, `resolve_runtime_bot_effects` | mixed | no | 4 | investigate |
| `bot_amplify_duration` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry`, `resolve_runtime_bot_effects` | mixed | no | 4 | investigate |
| `bot_amplify_range` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `bot_attribute_unmapped` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/registry/naming_contract.py` | `validate_account_snapshot_naming` | static | no | 4 | investigate |
| `bot_attributes` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/registry/naming_contract.py` | `_build_named_entity_maps`, `validate_account_snapshot_naming`, `validate_repo_naming_contract` | static | no | 4 | investigate |
| `bot_bonus_multiplier` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | `resolve_runtime_bot_effects` | runtime | no | 4 | investigate |
| `bot_cooldown_multiplier` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | `_read_profile_from_snapshot`, `resolve_runtime_bot_effects` | runtime | no | 4 | investigate |
| `bot_duration_multiplier` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | `_read_profile_from_snapshot`, `resolve_runtime_bot_effects` | runtime | no | 4 | investigate |
| `bot_flame_cooldown` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry`, `resolve_runtime_bot_effects` | mixed | no | 4 | investigate |
| `bot_flame_damage` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry`, `resolve_runtime_bot_effects` | mixed | no | 4 | investigate |
| `bot_flame_damage_reduction` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry`, `resolve_runtime_bot_effects` | mixed | no | 4 | investigate |
| `bot_flame_range` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `bot_golden_bonus` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry`, `resolve_runtime_bot_effects` | mixed | no | 4 | investigate |
| `bot_golden_cooldown` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry`, `resolve_runtime_bot_effects` | mixed | no | 4 | investigate |
| `bot_golden_duration` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry`, `resolve_runtime_bot_effects` | mixed | no | 4 | investigate |
| `bot_golden_range` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `bot_level_invalid` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_bot_stat_inputs` | static | no | 4 | investigate |
| `bot_level_missing` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_bot_stat_inputs` | static | no | 4 | investigate |
| `bot_levels` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat_stat_derivation.py` | `resolve_runtime_bot_effects` | runtime | no | 4 | investigate |
| `bot_range` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/registry/stat_registry.py` | `_apply_unique_effects`, `_compile_relic_stat_inputs`, `default_registry` | static | no | 4 | investigate |
| `bot_range_bonus_m` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_unique_effects` | static | no | 4 | investigate |
| `bot_table` | unknown | table_or_config_symbol | declared_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/naming_contract.py` | `_build_named_entity_maps`, `_compile_bot_stat_inputs` | static | no | 4 | investigate |
| `bot_thunder_cooldown` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `bot_thunder_duration` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `bot_thunder_linger` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `bot_thunder_range` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `bot_tracks` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_bot_stat_inputs` | static | no | 4 | investigate |
| `bot_unmapped` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/registry/naming_contract.py` | `validate_account_snapshot_naming` | static | no | 4 | investigate |
| `bot_upgrades` | unknown | table_or_config_symbol | declared_identifier | `tower_sim/loaders/account_snapshot_compiler.py`, `tower_sim/loaders/account_snapshot_loader.py`, `tower_sim/loaders/table_paths.py` | `_load_snapshot`, `_parse_bot_upgrades`, `_parse_bots` | static | no | 4 | investigate |
| `bot_upgrades_v1` | unknown | table_or_config_symbol | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 4 | investigate |
| `bot_values` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/loaders/account_snapshot_compiler.py` | `_parse_bots` | static | no | 4 | investigate |
| `bounce_shot_chance` | target_stat | canonical_target_stat | consumed_identifier | `tower_sim/loaders/ep_export_loader.py` | — | static | target_stat | 10 | aligned |
| `build_canonical_wave_row` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | — | runtime | no | 7 | classify |
| `build_canonical_wave_snapshot` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | — | runtime | no | 7 | classify |
| `build_edamage_stat_inputs` | unknown | implementation_artifact | consumed_identifier | `tower_sim/engines/edamage_pipeline.py` | — | mixed | no | 4 | investigate |
| `canonical_stat_inputs_for_wave` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | — | runtime | no | 7 | classify |
| `card_canonical` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_card_effects` | static | no | 4 | investigate |
| `card_id` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/run/optimizer_patch.py` | `_validate_card_actions` | mixed | no | 4 | investigate |
| `card_level` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/engines/edamage_formulas.py` | `epd_aspd`, `epd_crit_chance` | static | no | 4 | investigate |
| `card_masteries` | unknown | table_or_config_symbol | declared_identifier | `tower_sim/loaders/table_paths.py`, `tower_sim/run/optimizer_engine.py` | `_load_card_masteries`, `_stone_actions` | static | no | 4 | investigate |
| `card_masteries_v1` | unknown | table_or_config_symbol | consumed_identifier | `tower_sim/engines/edamage_pipeline.py`, `tower_sim/loaders/table_paths.py`, `tower_sim/run/optimizer_engine.py` | `_load_card_masteries`, `_mastery_action`, `resolve_card_mastery_value` | static | no | 4 | investigate |
| `card_mastery` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/run/optimizer_engine.py` | `_load_card_masteries` | mixed | no | 4 | investigate |
| `card_name` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/loaders/account_snapshot_compiler.py` | `_compile_survivability_loadout_inputs_resilient`, `_level_from_provenance`, `_parse_cards` | mixed | no | 4 | investigate |
| `card_pct` | alias | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | — | static | no | 7 | alias-map |
| `card_presets` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/loaders/account_snapshot_loader.py` | `_load_snapshot`, `_parse_card_presets`, `_resolve_loadout_inputs` | mixed | no | 4 | investigate |
| `card_unmapped` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/registry/naming_contract.py` | `validate_account_snapshot_naming` | static | no | 4 | investigate |
| `card_val` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `cards_common` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/loaders/wiki/cards.py` | `_load_cards_df` | static | no | 4 | investigate |
| `cards_epic` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/loaders/wiki/cards.py` | `_load_cards_df` | static | no | 4 | investigate |
| `cards_inventory` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/loaders/account_snapshot_loader.py` | `_load_snapshot`, `_parse_cards` | static | no | 4 | investigate |
| `cards_lib` | report-only | report_or_audit_field | consumed_identifier | `tower_sim/audit/repo_audit.py` | `_check_modules` | report | no | 7 | classify |
| `cards_rare` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tower_sim/engines/combat/boss_engine.py`, `tower_sim/loaders/wiki/cards.py` | `_load_cards_df` | mixed | no | 4 | investigate |
| `cash_bonus` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/registry/stat_registry.py` | `_compile_relic_stat_inputs`, `default_registry` | static | no | 4 | investigate |
| `chain_lightning_chance` | target_stat | canonical_target_stat | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | target_stat | 10 | aligned |
| `chain_lightning_damage` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_slot_main_effect` | static | no | 4 | investigate |
| `chain_lightning_quantity` | target_stat | canonical_target_stat | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | target_stat | 10 | aligned |
| `chrono_field_cooldown` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | no | 4 | investigate |
| `chrono_field_duration` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | no | 4 | investigate |
| `chrono_field_speed_reduction` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | no | 4 | investigate |
| `cl_chance` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `cl_damage` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `coin_actions_not_implemented` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/run/optimizer_engine.py` | `run_resource_optimizer` | mixed | no | 4 | investigate |
| `coin_level` | unknown | table_or_config_symbol | declared_identifier | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/loaders/account_snapshot_compiler.py`, … | `_apply_snapshot_patch`, `_parse_workshop`, `_serialize_workshop_entry` | static | no | 4 | investigate |
| `coin_mult` | alias | runtime_state_field | declared_identifier | `tower_sim/engines/uptime.py` | `aggregate_uptime` | runtime | no | 7 | alias-map |
| `coin_multiplier` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/econ_current.py`, `tower_sim/engines/uptime.py` | `_read_profile_from_snapshot`, `build_bot_effects`, `resolve_runtime_bot_effects` | runtime | no | 4 | investigate |
| `coin_sum` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/uptime.py` | `aggregate_uptime` | runtime | no | 4 | investigate |
| `coins_bonus` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `_compile_relic_stat_inputs`, `default_registry` | static | no | 4 | investigate |
| `coins_card` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/econ_current.py` | `econ_current` | mixed | no | 4 | investigate |
| `coins_mastery_lvl` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `coins_per_kill_bonus` | target_stat | canonical_target_stat | consumed_identifier | `tower_sim/loaders/ep_export_loader.py` | — | static | target_stat | 10 | aligned |
| `coins_per_kill_bonus_lvl` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `coins_per_kill_mult` | alias | approved_alias | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 7 | split |
| `compile_workshop_values_at_wave` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py` | — | static | no | 7 | classify |
| `compute_edamage_outputs` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/edamage_pipeline.py` | — | mixed | no | 4 | investigate |
| `cooldown_s` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/uptime.py` | `_read_profile_from_snapshot`, `build_bot_effects`, `build_periodic_activation_intervals` | runtime | no | 4 | investigate |
| `crit_chance` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/edamage_pipeline.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/loaders/ep_export_loader.py` | `_compile_relic_stat_inputs`, `build_edamage_stat_inputs`, `compute_edamage_outputs` | static | no | 4 | investigate |
| `crit_factor` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/edamage_pipeline.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/loaders/ep_export_loader.py` | `_compile_relic_stat_inputs`, `compute_edamage_outputs` | static | no | 4 | investigate |
| `crit_multiplier` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/edamage_pipeline.py` | `build_edamage_stat_inputs`, `compute_edamage_outputs` | mixed | no | 4 | investigate |
| `critical_chance` | target_stat | canonical_target_stat | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_card_effects` | static | target_stat | 10 | aligned |
| `current_bot` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/loaders/account_snapshot_compiler.py` | `_parse_bots` | static | no | 4 | investigate |
| `current_wave` | runtime | runtime_state_field | declared_identifier | `tower_sim/engines/perk_timeline_generator.py`, `tower_sim/loaders/perk_timeline_loader.py` | `apply_perk_timeline_to_inputs`, `generate_timeline` | static | no | 7 | classify |
| `damage` | target_stat | canonical_target_stat | declared_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tower_sim/audit/status.py`, `tower_sim/engines/combat/boss_engine.py`, … | `_apply_card_effects`, `_compile_relic_stat_inputs`, `_components` | mixed | target_stat | 10 | split |
| `damage_mult` | alias | runtime_state_field | declared_identifier | `tower_sim/engines/uptime.py` | `aggregate_uptime` | runtime | no | 7 | alias-map |
| `damage_mult_sum` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/uptime.py` | `aggregate_uptime` | runtime | no | 4 | investigate |
| `damage_multiplier` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/tier_rule_apply.py`, `tower_sim/engines/uptime.py` | `_read_profile_from_snapshot`, `build_bot_effects`, `resolve_runtime_bot_effects` | runtime | no | 4 | investigate |
| `damage_per_meter` | target_stat | canonical_target_stat | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/loaders/ep_export_loader.py`, … | `_compile_relic_stat_inputs`, `default_registry` | static | target_stat | 10 | aligned |
| `damage_reduction` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_engine.py`, `tower_sim/engines/combat/boss_survivability.py`, `tower_sim/engines/combat_stat_derivation.py`, … | `_read_profile_from_snapshot`, `build_bot_effects`, `evaluate` | runtime | no | 4 | investigate |
| `damage_remaining` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_survivability.py` | `_time_to_death` | runtime | no | 4 | investigate |
| `damage_taken` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/uptime.py` | `aggregate_uptime` | runtime | no | 4 | investigate |
| `death_ray_damage_mult` | alias | approved_alias | emitted_key | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/engines/tier_rule_apply.py`, … | `_apply_condition`, `_build_reaches_stat_input`, `_compile_base_stat_inputs` | static | no | 7 | alias-map |
| `death_wave_cooldown` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | no | 7 | classify |
| `death_wave_damage` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_slot_main_effect` | static | no | 7 | classify |
| `death_wave_quantity` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | no | 7 | classify |
| `def_pct` | report-only | report_or_audit_field | declared_and_emitted | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/engines/combat_stat_derivation.py`, … | `_apply_card_effects`, `_build_reaches_stat_input`, `_compile_base_stat_inputs` | mixed | no | 7 | classify |
| `default_wave_damage_tier` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | — | runtime | no | 7 | classify |
| `defense` | unknown | table_or_config_symbol | declared_identifier | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/engines/free_upgrades.py`, `tower_sim/engines/stat_input_compiler.py`, … | `_free_upgrade_chances`, `_parse_tower_defense`, `_workshop_category` | static | no | 4 | investigate |
| `defense_abs` | alias | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_survivability.py` | `resolve_boss_fight` | runtime | no | 7 | alias-map |
| `defense_absolute` | target_stat | canonical_target_stat | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/loaders/ep_export_loader.py`, … | `_apply_card_effects`, `_compile_relic_stat_inputs`, `default_registry` | static | target_stat | 10 | aligned |
| `defense_pct` | target_stat | canonical_target_stat | declared_identifier | `tower_sim/engines/combat/boss_engine.py`, `tower_sim/engines/combat/boss_survivability.py`, `tower_sim/engines/survivability_pipeline.py` | `_missing_inputs`, `_resolve_survivability_verdict`, `evaluate` | runtime | target_stat | 10 | aligned |
| `defense_percent` | report-only | report_or_audit_field | consumed_identifier | `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/loaders/ep_export_loader.py` | `_compile_relic_stat_inputs` | static | no | 7 | classify |
| `delta_mult` | alias | approved_alias | consumed_identifier | `tower_sim/registry/stat_registry.py` | — | static | no | 7 | alias-map |
| `duration_s` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/uptime.py` | `_read_profile_from_snapshot`, `build_bot_effects`, `build_gcomp_activation_intervals` | runtime | no | 4 | investigate |
| `dw_coin_bonus_lvl` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `dwdamage` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `dwdamageamp` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `eals_pct` | alias | approved_alias | declared_and_emitted | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/engines/tier_rule_apply.py`, … | `_apply_skip_reduction`, `_build_reaches_stat_input`, `_build_wave_state` | static | no | 7 | alias-map |
| `eals_ramp` | unknown | runtime_state_field | declared_identifier | `tower_sim/run/problem_spec.py`, `tower_sim/run/spec_loader.py` | `_parse_scenario` | mixed | no | 4 | investigate |
| `edamage` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/edamage_pipeline.py` | `inputs_from_canonical_values` | mixed | no | 4 | investigate |
| `effective_damage` | derived | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | `evaluate` | runtime | no | 4 | investigate |
| `effective_damage_per_sec` | derived | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | — | runtime | no | 4 | investigate |
| `effective_regen` | derived | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | `evaluate` | runtime | no | 4 | investigate |
| `effective_regen_per_sec` | derived | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | — | runtime | no | 4 | investigate |
| `ehls_pct` | alias | approved_alias | declared_and_emitted | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/engines/tier_rule_apply.py`, … | `_apply_skip_reduction`, `_build_reaches_stat_input`, `_build_wave_state` | static | no | 7 | alias-map |
| `ehls_ramp` | unknown | runtime_state_field | declared_identifier | `tower_sim/run/problem_spec.py`, `tower_sim/run/spec_loader.py` | `_parse_scenario` | mixed | no | 4 | investigate |
| `electrons_damage_frac` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_survivability.py` | `resolve_boss_fight` | runtime | no | 4 | investigate |
| `enemy_attack` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/combat_engine.py` | `resolve_combat` | runtime | no | 4 | investigate |
| `enemy_attack_mult` | alias | runtime_state_field | consumed_identifier | `tower_sim/engines/combat/combat_engine.py` | `resolve_combat` | runtime | no | 7 | alias-map |
| `enemy_attack_wave` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_pipeline.py` | `build_canonical_wave_row`, `resolve_wave_snapshot_for_problem_spec`, `wave_state_from_row` | runtime | no | 7 | classify |
| `enemy_damage_table` | unknown | table_or_config_symbol | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 4 | investigate |
| `enemy_health_table` | unknown | table_or_config_symbol | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 4 | investigate |
| `enemy_health_wave` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_pipeline.py` | `build_canonical_wave_row`, `resolve_wave_snapshot_for_problem_spec`, `wave_state_from_row` | runtime | no | 7 | classify |
| `enemy_hp` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/combat_engine.py` | — | runtime | no | 4 | investigate |
| `enemy_level_skip_reduction` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/tier_rule_apply.py` | `_apply_condition` | mixed | no | 4 | investigate |
| `enhancement_multiplier` | report-only | report_or_audit_field | declared_identifier | `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_engine.py`, … | `_build_row`, `_compile_workshop_stat_inputs`, `_extract_value` | mixed | no | 7 | classify |
| `enrage_mult` | alias | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_survivability.py`, `tower_sim/run/problem_spec.py`, `tower_sim/run/spec_loader.py` | `_parse_boss_stats` | runtime | no | 7 | alias-map |
| `ep_edamage_cr5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml`, `tower_sim/loaders/ep_export_loader.py` | — | static | no | 4 | investigate |
| `ep_edamage_cs5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_ct5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_cu5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_cv5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_cw5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_cx5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_cz5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_da5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_db5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_dc5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml`, `tower_sim/loaders/ep_export_loader.py` | — | static | no | 4 | investigate |
| `ep_edamage_dd5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_de5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_df5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_dg5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_dh5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_di5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_dj5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_dk5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_dl5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml`, `tower_sim/loaders/ep_export_loader.py` | — | static | no | 4 | investigate |
| `ep_edamage_dm5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml`, `tower_sim/loaders/ep_export_loader.py` | — | static | no | 4 | investigate |
| `ep_edamage_dp5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml`, `tower_sim/loaders/ep_export_loader.py` | — | static | no | 4 | investigate |
| `ep_edamage_ds5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_dt5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_du5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_dv5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_dw5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_dy5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_eb5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 4 | investigate |
| `ep_edamage_ef5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml`, `tower_sim/loaders/ep_export_loader.py` | — | static | no | 4 | investigate |
| `ep_lambda_ep_uw_sl_coverage` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_ep_uw_total_damage` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_epd_crit_chance` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_epd_critical` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_epd_multishot` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_epd_range` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_epd_rangedpm` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_epd_supertower_cooldown` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_epd_uwcritical` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_eph_def_pct` | alias | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | alias-map |
| `ep_lambda_eph_health` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_eph_regen` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_eph_wall_health` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_eph_wall_regen` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_stat_uw_cl_final_ch` | derived | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_stat_uw_cl_final_dmg` | derived | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_stat_uw_cl_final_qty` | derived | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_stat_uw_dw_final_cd` | derived | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_stat_uw_dw_final_dmg` | derived | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_stat_uw_dw_final_qty` | derived | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_stat_uw_sl_final_angle` | derived | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_stat_uw_sl_final_dmg` | derived | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_stat_uw_sl_final_lr` | derived | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_stat_uw_sm_final_cd` | derived | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_stat_uw_sm_final_cf` | derived | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_stat_uw_sm_final_dmg` | derived | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `ep_lambda_stat_uw_sm_final_qty` | derived | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `epd_crit_chance` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/edamage_formulas.py` | — | mixed | no | 4 | investigate |
| `epd_critical` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/edamage_formulas.py` | — | mixed | no | 4 | investigate |
| `equipped_cards` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/run/api.py` | `_serialize_loadout` | mixed | no | 4 | investigate |
| `expected_coin_multiplier` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/uptime.py` | — | runtime | no | 4 | investigate |
| `expected_damage_multiplier` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/uptime.py` | — | runtime | no | 4 | investigate |
| `expected_damage_taken` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/uptime.py` | — | runtime | no | 4 | investigate |
| `expected_skipped_waves` | runtime | report_or_audit_field | consumed_identifier | `tower_sim/audit/status.py` | `_components` | report | no | 7 | classify |
| `extra_defense` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_card_effects` | static | no | 4 | investigate |
| `extra_orb_mastery_lvl` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `extract_max_wave_targets` | runtime | runtime_state_field | consumed_identifier | `tower_sim/loaders/ep_export_loader.py` | — | static | no | 7 | classify |
| `final_wave` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/perk_timeline_generator.py` | `generate_timeline` | mixed | no | 7 | classify |
| `flame_bot_damage_reduction_multiplier` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | `resolve_runtime_bot_effects` | runtime | no | 4 | investigate |
| `free_attack_upgrade` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/loaders/ep_export_loader.py`, … | `_compile_relic_stat_inputs`, `default_registry` | static | no | 4 | investigate |
| `free_attack_upgrade_rate` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `free_defense_upgrade` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/loaders/ep_export_loader.py`, … | `_compile_relic_stat_inputs`, `default_registry` | static | no | 4 | investigate |
| `from_wave` | runtime | runtime_state_field | declared_identifier | `tower_sim/engines/combat_stat_derivation.py` | `derive_canonical_combat_snapshot` | runtime | no | 7 | classify |
| `generator_module` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `gold_bot_cooldown_lvl` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `gold_bot_duration_lvl` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `golden_tower_cooldown` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | no | 4 | investigate |
| `golden_tower_duration` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | no | 4 | investigate |
| `golden_tower_multiplier` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | no | 4 | investigate |
| `gt_duration_lvl` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `has_card` | unknown | table_or_config_symbol | declared_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/engines/econ_current.py`, … | `epd_aspd`, `epd_crit_chance` | static | no | 4 | investigate |
| `has_coins_perk` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `has_module` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `has_more_bosses` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/loaders/tournament_bc_selection.py` | `load_league_rules` | static | no | 4 | investigate |
| `health` | target_stat | canonical_target_stat | consumed_identifier | `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/audit/wiring_health_check.py`, `tower_sim/engines/combat/combat_engine.py`, … | `_apply_card_effects`, `_compile_relic_stat_inputs`, `_parse_args` | mixed | target_stat | 10 | split |
| `health_regen` | target_stat | canonical_target_stat | consumed_identifier | `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, … | `_apply_card_effects`, `_compile_relic_stat_inputs` | static | target_stat | 10 | aligned |
| `heat_mult` | alias | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_survivability.py` | `_time_to_death` | runtime | no | 7 | alias-map |
| `hpregen` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/registry/naming_contract.py` | — | static | no | 4 | investigate |
| `incoming_damage` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | `evaluate` | runtime | no | 4 | investigate |
| `inner_land_mines_cooldown` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | no | 4 | investigate |
| `inner_land_mines_damage` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_slot_main_effect` | static | no | 4 | investigate |
| `inner_land_mines_quantity` | target_stat | canonical_target_stat | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | target_stat | 10 | aligned |
| `is_boss` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/combat_engine.py` | — | runtime | no | 4 | investigate |
| `key_modules` | report-only | report_or_audit_field | declared_identifier | `tower_sim/audit/repo_audit.py` | `_check_modules` | report | no | 7 | classify |
| `kill_at_range` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `knockback_mult` | alias | approved_alias | emitted_key | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/engines/tier_rule_apply.py`, … | `_apply_condition`, `_build_reaches_stat_input`, `_compile_base_stat_inputs` | static | no | 7 | alias-map |
| `knockback_multiplier` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/tier_rule_apply.py` | — | mixed | no | 4 | investigate |
| `lab_enemy_attack_level_skip` | unknown | runtime_state_field | consumed_identifier | `tower_sim/loaders/wiki/labs_eals_ehls.py` | `get_eals_lab_pp` | static | no | 4 | investigate |
| `lab_enemy_health_level_skip` | unknown | runtime_state_field | consumed_identifier | `tower_sim/loaders/wiki/labs_eals_ehls.py` | `get_ehls_lab_pp` | static | no | 4 | investigate |
| `lab_health` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/loaders/wiki/labs.py` | — | static | no | 4 | investigate |
| `lab_health_regen` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/loaders/wiki/labs.py` | — | static | no | 4 | investigate |
| `lab_multiplier` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_workshop_stat_inputs` | static | no | 4 | investigate |
| `lab_pct` | alias | approved_alias | declared_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_armor_module_multiplier` | static | no | 7 | alias-map |
| `lab_recovery_package_chance` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/loaders/wiki/labs.py` | — | static | no | 4 | investigate |
| `lab_speed` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `_compile_relic_stat_inputs`, `default_registry` | static | no | 4 | investigate |
| `lineage_required_max_wave_gap_count` | runtime | report_or_audit_field | consumed_identifier | `tower_sim/audit/wiring_health_check.py` | `run_wiring_health_check` | report | no | 7 | classify |
| `load_card_masteries` | unknown | implementation_artifact | consumed_identifier | `tower_sim/loaders/card_masteries.py` | — | static | no | 4 | investigate |
| `locked_uws` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/run/optimizer_engine.py` | `_parse_uw_rows`, `_stone_actions` | mixed | no | 4 | investigate |
| `make_wave_state` | runtime | report_or_audit_field | consumed_identifier | `tower_sim/audit/status.py` | `_components` | report | no | 7 | classify |
| `mastery_mult` | alias | approved_alias | declared_identifier | `tower_sim/engines/econ_current.py` | `EPC_CARD_COINS` | mixed | no | 7 | split |
| `max_recovery_vault_mult` | alias | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | alias-map |
| `max_recovery_wse_mult` | alias | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | alias-map |
| `max_rend_mult` | alias | approved_alias | consumed_identifier | `tower_sim/loaders/ep_export_loader.py` | — | static | no | 7 | alias-map |
| `max_wave` | runtime | report_or_audit_field | declared_identifier | `tower_sim/audit/status.py`, `tower_sim/loaders/bc_heat_loader.py`, `tower_sim/loaders/ep_export_loader.py`, … | `_components`, `_parse_problem_spec`, `extract_max_wave_targets` | static | no | 7 | classify |
| `max_wave_ids` | runtime | runtime_state_field | declared_identifier | `tower_sim/engines/statbook_builder.py` | `_target_stat_ids` | mixed | no | 7 | classify |
| `max_wave_latest` | runtime | runtime_state_field | consumed_identifier | `tower_sim/run/runner.py` | — | mixed | no | 7 | classify |
| `max_wave_report` | runtime | report_or_audit_field | consumed_identifier | `tower_sim/audit/status.py` | `_components` | report | no | 7 | classify |
| `max_wave_runner` | runtime | runtime_state_field | consumed_identifier | `tower_sim/run/runner.py` | — | mixed | no | 7 | classify |
| `min_wave` | runtime | runtime_state_field | declared_identifier | `tower_sim/loaders/bc_heat_loader.py` | `value_at` | static | no | 7 | classify |
| `missing_at_wave` | runtime | runtime_state_field | emitted_key | `tower_sim/engines/stat_pipeline.py` | `build_canonical_stat_pipeline_for_problem_spec` | mixed | no | 7 | classify |
| `missing_cards` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/loaders/account_snapshot_compiler.py` | `_parse_cards` | static | no | 4 | investigate |
| `missing_required_at_wave_stats` | runtime | runtime_state_field | emitted_key | `tower_sim/engines/stat_pipeline.py` | `build_canonical_stat_pipeline_for_problem_spec` | mixed | no | 7 | classify |
| `missing_wave` | runtime | runtime_state_field | declared_identifier | `tower_sim/engines/stat_pipeline.py` | `build_canonical_stat_pipeline_for_problem_spec` | mixed | no | 7 | classify |
| `missing_wave_state` | runtime | runtime_state_field | emitted_key | `tower_sim/engines/stat_pipeline.py` | `build_canonical_stat_pipeline_for_problem_spec` | mixed | no | 7 | classify |
| `module_` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | `_canonical_unmapped_by_source`, `_families_from_stat_input` | runtime | no | 4 | investigate |
| `module_blocks` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_build_inventory_summary`, `compile_baseline_loadout_stat_inputs` | static | no | 4 | investigate |
| `module_context` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_pipeline.py` | `_compile_survivability_loadout_inputs_resilient`, `_resolve_loadout_inputs` | runtime | no | 4 | investigate |
| `module_contribution_ledger` | unknown | legacy_or_unresolved | declared_and_emitted | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, … | `_compile_survivability_loadout_inputs_resilient`, `build_canonical_stat_inputs`, `build_canonical_stat_pipeline_for_problem_spec` | mixed | no | 4 | investigate |
| `module_id` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/run/optimizer_patch.py` | `_validate_module_actions` | mixed | no | 4 | investigate |
| `module_layer_gaps` | unknown | legacy_or_unresolved | emitted_key | `tower_sim/engines/survivability_pipeline.py` | `build_survivability_report` | mixed | no | 4 | investigate |
| `module_main_effect_bands` | unknown | table_or_config_symbol | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 4 | investigate |
| `module_main_effect_bands_v1` | unknown | table_or_config_symbol | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 4 | investigate |
| `module_main_effect_bases` | unknown | table_or_config_symbol | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 4 | investigate |
| `module_main_effect_bases_v1` | unknown | table_or_config_symbol | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 4 | investigate |
| `module_name` | report-only | report_or_audit_field | declared_identifier | `tower_sim/audit/repo_audit.py`, `tower_sim/engines/survivability_pipeline.py` | `_check_modules`, `_parse_module_block` | report | no | 7 | classify |
| `module_preset_unmapped` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/registry/naming_contract.py` | `validate_account_snapshot_naming` | static | no | 4 | investigate |
| `module_presets` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/loaders/account_snapshot_compiler.py`, `tower_sim/loaders/account_snapshot_loader.py` | `_load_snapshot`, `_parse_module_presets`, `_parse_modules` | mixed | no | 4 | investigate |
| `module_primary_effect` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_slot_main_effect`, `_module_unmapped_by_layer` | mixed | no | 4 | investigate |
| `module_rules` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/modules.py` | — | mixed | no | 4 | investigate |
| `module_substat_unmapped` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, … | `_apply_module_substats`, `_module_unmapped_by_layer`, `validate_account_snapshot_naming` | mixed | no | 4 | investigate |
| `module_substats` | unknown | table_or_config_symbol | consumed_identifier | `tower_sim/loaders/table_paths.py`, `tower_sim/registry/naming_contract.py` | `_build_named_entity_maps`, `validate_account_snapshot_naming`, `validate_repo_naming_contract` | static | no | 4 | investigate |
| `module_substats_v1` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/loaders/table_paths.py` | — | static | no | 4 | investigate |
| `module_summary` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/survivability_pipeline.py` | `_build_inventory_summary` | mixed | no | 4 | investigate |
| `module_system_state` | unknown | runtime_state_field | declared_identifier | `tower_sim/loaders/account_snapshot_compiler.py`, `tower_sim/loaders/account_snapshot_loader.py` | `_load_snapshot`, `_parse_module_system_state`, `_parse_modules` | static | no | 4 | investigate |
| `module_unique_unmapped` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_module_effects`, `_module_unmapped_by_layer` | mixed | no | 4 | investigate |
| `module_unmapped` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/registry/naming_contract.py` | `validate_account_snapshot_naming` | static | no | 4 | investigate |
| `module_unmapped_by_layer` | unknown | runtime_state_field | declared_and_emitted | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_pipeline.py` | `build_canonical_stat_inputs`, `build_canonical_stat_pipeline_for_problem_spec` | runtime | no | 4 | investigate |
| `modules_inventory` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/loaders/account_snapshot_compiler.py`, `tower_sim/loaders/account_snapshot_loader.py` | `_load_snapshot`, `_parse_modules` | static | no | 4 | investigate |
| `modules_lib` | report-only | report_or_audit_field | consumed_identifier | `tower_sim/audit/repo_audit.py` | `_check_modules` | report | no | 7 | classify |
| `modules_library` | report-only | report_or_audit_field | consumed_identifier | `tower_sim/audit/repo_audit.py`, `tower_sim/engines/modules.py` | `_check_modules`, `_iter_reference_files` | report | no | 7 | classify |
| `more_bosses` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/tier_rule_apply.py`, `tower_sim/loaders/bc_heat_loader.py`, `tower_sim/loaders/tournament_bc_selection.py` | `_apply_condition`, `enumerate_tournament_bc_sets`, `load_tournament_heat_table` | static | no | 4 | investigate |
| `multi_rapid_bounce` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `multiplier_cap` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/loaders/account_snapshot_compiler.py`, `tower_sim/loaders/account_snapshot_loader.py` | `_parse_module_system_state` | static | no | 4 | investigate |
| `multiplier_efficiency` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/modules.py` | `apply_multiplier_efficiency` | mixed | no | 4 | investigate |
| `multiplier_level` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/run/optimizer_engine.py` | `_stone_actions` | mixed | no | 4 | investigate |
| `multishot_chance` | target_stat | canonical_target_stat | consumed_identifier | `tower_sim/loaders/ep_export_loader.py` | — | static | target_stat | 10 | aligned |
| `multishot_targets` | target_stat | canonical_target_stat | consumed_identifier | `tower_sim/loaders/ep_export_loader.py` | — | static | target_stat | 10 | aligned |
| `net_damage` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | `evaluate` | runtime | no | 4 | investigate |
| `net_damage_per_sec` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | — | runtime | no | 4 | investigate |
| `next_percent` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/run/optimizer_engine.py` | `_apply_unlock` | mixed | no | 4 | investigate |
| `next_uw_plus_unlock_cost` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/run/optimizer_engine.py` | `_stone_actions` | mixed | no | 4 | investigate |
| `next_uw_unlock_cost` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/run/optimizer_engine.py` | `_stone_actions` | mixed | no | 4 | investigate |
| `next_wave` | runtime | runtime_state_field | declared_identifier | `tower_sim/engines/perk_timeline_generator.py` | `generate_timeline` | mixed | no | 7 | classify |
| `no_authoritative_bot_mapping_for_stat` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/registry/combat_stat_contract.py` | `_excluded_reason`, `stat_lineage_status_lists` | static | no | 4 | investigate |
| `no_authoritative_card_mapping_for_stat` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/registry/combat_stat_contract.py` | `_excluded_reason`, `stat_lineage_status_lists` | static | no | 4 | investigate |
| `no_authoritative_module_mapping_for_stat` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/registry/combat_stat_contract.py` | `_excluded_reason`, `stat_lineage_status_lists` | static | no | 4 | investigate |
| `no_authoritative_uw_mapping_for_stat` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/registry/combat_stat_contract.py` | `_excluded_reason`, `stat_lineage_status_lists` | static | no | 4 | investigate |
| `op_chain` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `orb_damage_frac` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_survivability.py` | `resolve_boss_fight` | runtime | no | 4 | investigate |
| `orb_damage_mult` | alias | approved_alias | emitted_key | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/engines/tier_rule_apply.py`, … | `_apply_condition`, `_build_reaches_stat_input`, `_compile_base_stat_inputs` | static | no | 7 | alias-map |
| `orb_resistance` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/survivability_pipeline.py`, `tower_sim/engines/tier_rule_apply.py`, `tower_sim/loaders/tournament_bc_enrichment.py` | `_apply_condition`, `_tier_rules_applied` | static | no | 4 | investigate |
| `orb_speed` | target_stat | canonical_target_stat | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/registry/stat_registry.py` | `_compile_relic_stat_inputs`, `default_registry` | static | target_stat | 10 | aligned |
| `out_of_range` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | `validate_boss_survivability_spec` | runtime | no | 4 | investigate |
| `package_chance` | target_stat | canonical_target_stat | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | `evaluate` | runtime | target_stat | 10 | aligned |
| `package_heal` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | `evaluate` | runtime | no | 4 | investigate |
| `package_regen` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | `evaluate` | runtime | no | 4 | investigate |
| `pc_boss_mult` | alias | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_engine.py`, `tower_sim/engines/combat/boss_survivability.py`, `tower_sim/engines/combat/combat_engine.py` | `evaluate`, `resolve_boss_fight`, `resolve_combat` | runtime | no | 7 | alias-map |
| `per_hit_boss_frac` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_survivability.py` | `resolve_boss_fight` | runtime | no | 4 | investigate |
| `percent_points` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/loaders/wiki/promote_labs_tables.py`, … | `_compile_wall_survivability_aliases`, `_parse_value`, `_resolve_lab_delta` | static | no | 4 | investigate |
| `percent_string` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/loaders/wiki/cache_audit.py` | `_detect_unit_hint`, `_strip_unit` | static | no | 4 | investigate |
| `perk_multiplier` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/edamage_pipeline.py` | `resolve_damage_perk_multiplier` | mixed | no | 4 | investigate |
| `plasma_cannon_card_frac_v1` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | — | static | no | 4 | investigate |
| `plasma_cannon_damage_mult` | alias | approved_alias | emitted_key | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/engines/tier_rule_apply.py`, … | `_apply_card_effects`, `_apply_condition`, `_build_reaches_stat_input` | static | no | 7 | alias-map |
| `poison_swamp_cooldown` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | no | 4 | investigate |
| `poison_swamp_damage` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_slot_main_effect` | static | no | 4 | investigate |
| `poison_swamp_duration` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | no | 4 | investigate |
| `preset_cards` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/wave_time.py` | `wa_reduction_from_snapshot` | runtime | no | 4 | investigate |
| `ramp_waves` | runtime | runtime_state_field | declared_identifier | `tower_sim/engines/wave_engine.py`, `tower_sim/run/problem_spec.py`, `tower_sim/run/spec_loader.py` | `_parse_skip_ramp` | runtime | no | 7 | classify |
| `range_dpm` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | — | static | no | 4 | investigate |
| `range_multiplier` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | — | static | no | 4 | investigate |
| `rapid_fire_chance` | target_stat | canonical_target_stat | consumed_identifier | `tower_sim/loaders/ep_export_loader.py` | — | static | target_stat | 10 | aligned |
| `rapid_fire_duration` | unknown | runtime_state_field | consumed_identifier | `tower_sim/loaders/ep_export_loader.py` | — | static | no | 4 | investigate |
| `raw_damage` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_survivability.py` | `_time_to_death` | runtime | no | 4 | investigate |
| `raw_multiplier` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/stat_input_compiler.py` | `_parse_workshop_enhancement_multipliers` | static | no | 4 | investigate |
| `recovery_package_chance` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/engines/survivability_pipeline.py`, … | `_apply_card_effects` | static | no | 4 | investigate |
| `recovery_package_max` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `reduced_damage` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | `evaluate` | runtime | no | 4 | investigate |
| `regen` | report-only | report_or_audit_field | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/audit/status.py`, `tower_sim/engines/stat_input_compiler.py`, … | `_components`, `_workshop_value`, `default_registry` | static | no | 7 | classify |
| `regen_per_hit` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_survivability.py` | `_time_to_death` | runtime | no | 4 | investigate |
| `regen_per_sec` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_survivability.py`, `tower_sim/run/problem_spec.py`, `tower_sim/run/spec_loader.py` | `_parse_tower_defense` | runtime | no | 4 | investigate |
| `relic_pct` | alias | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | alias-map |
| `remaining_enemy_hp` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat/combat_engine.py` | `resolve_combat` | runtime | no | 4 | investigate |
| `rend_mult` | alias | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | — | static | no | 7 | alias-map |
| `required_max_wave` | runtime | report_or_audit_field | consumed_identifier | `tower_sim/audit/stat_lineage_report.py` | `_build_full_table` | report | no | 7 | classify |
| `required_max_wave_gap_count` | runtime | report_or_audit_field | consumed_identifier | `tower_sim/audit/stat_lineage_report.py`, `tower_sim/audit/wiring_health_check.py` | `_parse_args`, `render_report`, `run_wiring_health_check` | report | no | 7 | classify |
| `required_max_wave_gaps` | runtime | report_or_audit_field | declared_identifier | `tower_sim/audit/stat_lineage_report.py` | `render_report`, `summarize_manifest` | report | no | 7 | classify |
| `required_max_wave_other` | runtime | runtime_state_field | declared_identifier | `tower_sim/registry/combat_stat_contract.py` | `ordered_stat_lineage_sections` | static | no | 7 | classify |
| `required_max_wave_other_stat_inputs` | runtime | runtime_state_field | consumed_identifier | `tower_sim/registry/combat_stat_contract.py` | `ordered_stat_lineage_sections` | static | no | 7 | classify |
| `required_max_wave_stat_input_ids` | runtime | report_or_audit_field | consumed_identifier | `tower_sim/audit/stat_lineage_report.py`, `tower_sim/registry/combat_stat_contract.py` | `load_manifest`, `summarize_manifest` | static | no | 7 | classify |
| `resolve_canonical_wave_damage` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | — | runtime | no | 7 | classify |
| `resolve_canonical_wave_damage_for_attack_wave` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | — | runtime | no | 7 | classify |
| `resolve_card_mastery_value` | unknown | implementation_artifact | consumed_identifier | `tower_sim/engines/edamage_pipeline.py` | — | mixed | no | 4 | investigate |
| `resolve_damage_perk_multiplier` | unknown | implementation_artifact | consumed_identifier | `tower_sim/engines/edamage_pipeline.py` | — | mixed | no | 4 | investigate |
| `resolve_wave_state_for_wave` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | — | runtime | no | 7 | classify |
| `selected_cards` | unknown | runtime_state_field | declared_and_emitted | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_pipeline.py` | `_compile_survivability_loadout_inputs_resilient`, `_resolve_loadout_inputs` | runtime | no | 4 | investigate |
| `skip_ramp` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_pipeline.py` | `_build_wave_state`, `resolve_wave_state_for_wave` | runtime | no | 4 | investigate |
| `skipped_missing_targets` | report-only | report_or_audit_field | consumed_identifier | `tower_sim/audit/max_wave_ep_parity.py` | `validate_runner_against_ep_export` | runtime | no | 7 | classify |
| `sl_damage` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `sl_lightrange` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `sm_cooldown` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `sm_damage` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `smart_missiles_cooldown` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | no | 4 | investigate |
| `smart_missiles_damage` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_slot_main_effect` | static | no | 4 | investigate |
| `smart_missiles_quantity` | target_stat | canonical_target_stat | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | target_stat | 10 | aligned |
| `spotlight_coin_bonus_lvl` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `spotlight_multiplier` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/econ_current.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | no | 4 | investigate |
| `st_uw_mastery` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `standard_perks_bonus_mult` | alias | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | alias-map |
| `stone_pct` | alias | approved_alias | declared_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_armor_module_multiplier`, `_resolve_assist_efficiencies` | static | no | 7 | alias-map |
| `super_crit_chance` | target_stat | canonical_target_stat | declared_identifier | `tower_sim/engines/edamage_pipeline.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, … | `_compile_relic_stat_inputs`, `default_registry`, `inputs_from_canonical_values` | static | target_stat | 10 | aligned |
| `super_crit_mult` | alias | approved_alias | declared_identifier | `tower_sim/engines/edamage_pipeline.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, … | `_compile_relic_stat_inputs`, `default_registry`, `inputs_from_canonical_values` | static | no | 7 | alias-map |
| `super_crit_multiplier` | target_stat | canonical_target_stat | consumed_identifier | `tower_sim/loaders/ep_export_loader.py` | — | static | target_stat | 10 | aligned |
| `survivability_loadout_unknown_card` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | `_compile_survivability_loadout_inputs_resilient` | runtime | no | 4 | investigate |
| `survivability_loadout_unsupported_card` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | `_compile_survivability_loadout_inputs_resilient` | runtime | no | 4 | investigate |
| `target_wall_hp_base` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat_stat_derivation.py` | `_rebase_wall_stats_from_tower` | runtime | no | 4 | investigate |
| `target_wall_regen_base` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat_stat_derivation.py` | `_rebase_wall_stats_from_tower` | runtime | no | 4 | investigate |
| `target_wave` | runtime | runtime_state_field | declared_identifier | `tower_sim/engines/perk_timeline_generator.py`, `tower_sim/engines/stat_pipeline.py` | `build_canonical_stat_pipeline_for_problem_spec`, `load_policy` | mixed | no | 7 | classify |
| `test_boss_engine` | report-only | report_or_audit_field | consumed_identifier | `tower_sim/audit/status.py` | `_components` | report | no | 7 | classify |
| `test_boss_survivability` | report-only | report_or_audit_field | consumed_identifier | `tower_sim/audit/status.py` | `_components` | report | no | 7 | classify |
| `test_max_wave_observability` | runtime | report_or_audit_field | consumed_identifier | `tower_sim/audit/status.py` | `_components` | report | no | 7 | classify |
| `test_max_wave_v1_contract` | runtime | report_or_audit_field | consumed_identifier | `tower_sim/audit/status.py` | `_components` | report | no | 7 | classify |
| `test_wave_damage_strict` | runtime | report_or_audit_field | consumed_identifier | `tower_sim/audit/status.py` | `_components` | report | no | 7 | classify |
| `test_wave_engine` | runtime | report_or_audit_field | consumed_identifier | `tower_sim/audit/status.py` | `_components` | report | no | 7 | classify |
| `thorns_damage_mult` | alias | approved_alias | emitted_key | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, … | `_apply_condition`, `_build_reaches_stat_input`, `_compile_base_stat_inputs` | mixed | no | 7 | split |
| `thorns_frac` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_engine.py`, `tower_sim/engines/combat/boss_survivability.py`, `tower_sim/engines/combat/combat_engine.py`, … | `_resolve_survivability_verdict`, `evaluate`, `resolve_boss_fight` | runtime | no | 4 | investigate |
| `thorns_mult` | alias | approved_alias | consumed_identifier | `tower_sim/engines/survivability_pipeline.py` | `_resolve_thorns_inputs` | mixed | no | 7 | split |
| `thorns_pct` | alias | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | `_missing_inputs`, `evaluate` | runtime | no | 7 | alias-map |
| `thorns_resistance` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/survivability_pipeline.py`, `tower_sim/engines/tier_rule_apply.py`, `tower_sim/loaders/tournament_bc_enrichment.py` | `_apply_condition`, `_tier_rules_applied` | static | no | 4 | investigate |
| `tier_multiplier` | report-only | report_or_audit_field | declared_identifier | `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_snapshots.py` | `_extract_value`, `_resolve_stat_input_value`, `_resolved_stat_input_value` | runtime | no | 7 | classify |
| `tier_rule_multiplier` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/stat_engine.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/run/api.py`, … | `_merge_stat_input_for_run_stats`, `_parse_stat_input`, `_resolved_stat_input_value` | static | no | 4 | investigate |
| `tier_wave_damage` | runtime | table_or_config_symbol | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 7 | classify |
| `tier_wave_damage_legacy` | runtime | table_or_config_symbol | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 7 | classify |
| `time_multiplier_mode` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `total_damage` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/combat_engine.py` | `resolve_combat` | runtime | no | 4 | investigate |
| `tournament_more_bosses_static` | unknown | table_or_config_symbol | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 4 | investigate |
| `tournament_wave_damage` | runtime | table_or_config_symbol | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 7 | classify |
| `tournament_wave_damage_legacy` | runtime | table_or_config_symbol | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 7 | classify |
| `tower_attack_speed` | unknown | legacy_or_unresolved | declared_and_emitted | `tower_sim/engines/edamage_pipeline.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, … | `_apply_card_effects`, `_build_reaches_stat_input`, `_compile_relic_stat_inputs` | static | no | 4 | investigate |
| `tower_crit_chance` | unknown | legacy_or_unresolved | declared_and_emitted | `tower_sim/engines/edamage_pipeline.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, … | `_apply_card_effects`, `_build_reaches_stat_input`, `_compile_relic_stat_inputs` | static | no | 4 | investigate |
| `tower_crit_factor` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/edamage_pipeline.py` | — | mixed | no | 4 | investigate |
| `tower_crit_multiplier` | unknown | legacy_or_unresolved | emitted_key | `tower_sim/engines/edamage_pipeline.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, … | `_build_reaches_stat_input`, `_compile_relic_stat_inputs`, `build_edamage_stat_inputs` | static | no | 4 | investigate |
| `tower_damage` | unknown | legacy_or_unresolved | declared_and_emitted | `tower_sim/engines/combat/combat_engine.py`, `tower_sim/engines/edamage_pipeline.py`, `tower_sim/engines/stat_input_compiler.py`, … | `_apply_card_effects`, `_apply_slot_main_effect`, `_build_reaches_stat_input` | mixed | no | 4 | investigate |
| `tower_damage_taken` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat/combat_engine.py` | `resolve_combat` | runtime | no | 4 | investigate |
| `tower_kills_boss` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat/boss_survivability.py` | `resolve_boss_fight` | runtime | no | 4 | investigate |
| `tower_regen` | report-only | report_or_audit_field | declared_and_emitted | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/engines/combat/boss_engine.py`, … | `_apply_card_effects`, `_build_reaches_stat_input`, `_compile_base_stat_inputs` | mixed | no | 7 | classify |
| `tower_regen_per_sec` | unknown | runtime_state_field | emitted_key | `tower_sim/engines/combat_stat_derivation.py` | `validate_boss_survivability_spec` | runtime | no | 4 | investigate |
| `transfer_multiplier` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat_stat_derivation.py` | `_replace_base` | runtime | no | 4 | investigate |
| `ultimate_crit` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_card_effects` | static | no | 4 | investigate |
| `ultimate_damage` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `_compile_relic_stat_inputs`, `default_registry` | static | no | 4 | investigate |
| `unknown_card` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | `_canonical_unmapped_by_source` | runtime | no | 4 | investigate |
| `unsupported_card` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | `_canonical_unmapped_by_source` | runtime | no | 4 | investigate |
| `upgrade_mult` | alias | approved_alias | declared_identifier | `tower_sim/engines/stat_input_compiler.py` | `_free_upgrade_chances` | static | no | 7 | alias-map |
| `uw_` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/statbook_builder.py`, … | `_canonical_unmapped_by_source`, `_ordered_target_stat_ids`, `_uw_canonical_aliases` | mixed | no | 4 | investigate |
| `uw_alias` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_uw_stat_inputs` | static | no | 4 | investigate |
| `uw_alias_pairs` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_behavior` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_unique_effects` | static | no | 4 | investigate |
| `uw_black_hole_consume` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_black_hole_cooldown` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_black_hole_duration` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_black_hole_size` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_canonical` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/registry/naming_contract.py` | `_build_named_entity_maps` | static | no | 4 | investigate |
| `uw_chain_lightning_chance` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_chain_lightning_damage` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_chain_lightning_quantity` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_chain_lightning_smite` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_chrono_field_chrono_loop` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_chrono_field_cooldown` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_chrono_field_duration` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_chrono_field_speed_reduction` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_cost_stats` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_costs` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/run/optimizer_engine.py` | `_load_uw_purchase_costs` | mixed | no | 4 | investigate |
| `uw_crit_card` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `uw_damage_boost` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `uw_death_wave_cooldown` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 7 | classify |
| `uw_death_wave_damage` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 7 | classify |
| `uw_death_wave_kill_wall` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 7 | classify |
| `uw_death_wave_quantity` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 7 | classify |
| `uw_golden_tower_cooldown` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_golden_tower_duration` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_golden_tower_golden_combo` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_golden_tower_multiplier` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_ids` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/statbook_builder.py` | `_target_stat_ids` | mixed | no | 4 | investigate |
| `uw_inner_land_mines_charged_mines` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_inner_land_mines_cooldown` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_inner_land_mines_damage` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_inner_land_mines_quantity` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_level_missing` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py` | `_parse_uw_tracks` | static | no | 4 | investigate |
| `uw_lib` | report-only | report_or_audit_field | consumed_identifier | `tower_sim/audit/repo_audit.py` | `_check_modules` | report | no | 7 | classify |
| `uw_locked` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_uw_stat_inputs` | static | no | 4 | investigate |
| `uw_mapping` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_uw_stat_inputs` | static | no | 4 | investigate |
| `uw_name` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/run/optimizer_engine.py` | `_load_uw_plus_ladders`, `_load_uw_track_ladders`, `_load_uw_track_values` | static | no | 4 | investigate |
| `uw_plus` | unknown | legacy_or_unresolved | emitted_key | `tower_sim/run/optimizer_engine.py` | `_load_uw_purchase_costs`, `_stone_actions` | mixed | no | 4 | investigate |
| `uw_plus_costs` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/run/optimizer_engine.py` | `_load_uw_purchase_costs`, `_stone_actions` | mixed | no | 4 | investigate |
| `uw_plus_ladders` | unknown | table_or_config_symbol | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/loaders/table_paths.py`, `tower_sim/run/optimizer_engine.py` | `_load_uw_plus_ladders`, `_load_uw_track_values` | static | no | 4 | investigate |
| `uw_plus_ladders_v1` | unknown | table_or_config_symbol | consumed_identifier | `tower_sim/loaders/table_paths.py`, `tower_sim/run/optimizer_engine.py` | `_load_uw_plus_ladders`, `_uw_plus_track_upgrade_action` | static | no | 4 | investigate |
| `uw_plus_locked` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/run/optimizer_engine.py` | `_parse_uw_rows`, `_stone_actions` | mixed | no | 4 | investigate |
| `uw_plus_track_upgrade` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/run/optimizer_engine.py` | `_uw_plus_track_upgrade_action` | mixed | no | 4 | investigate |
| `uw_plus_tracks` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/run/optimizer_engine.py` | `_parse_uw_rows`, `_stone_actions` | mixed | no | 4 | investigate |
| `uw_plus_unlock` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/run/optimizer_engine.py` | `_uw_plus_unlock_action` | mixed | no | 4 | investigate |
| `uw_plus_unlock_cost` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/run/optimizer_engine.py` | `_load_uw_purchase_costs` | mixed | no | 4 | investigate |
| `uw_plus_unlock_count` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/run/optimizer_engine.py` | `_load_uw_purchase_costs` | mixed | no | 4 | investigate |
| `uw_plus_unlocked_count` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/run/optimizer_engine.py` | `_parse_uw_rows`, `_stone_actions` | mixed | no | 4 | investigate |
| `uw_poison_swamp_cooldown` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_poison_swamp_damage` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_poison_swamp_death_creep` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_poison_swamp_duration` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_purchase_costs` | unknown | table_or_config_symbol | declared_identifier | `tower_sim/loaders/table_paths.py`, `tower_sim/run/optimizer_engine.py` | `_load_uw_purchase_costs`, `_stone_actions` | static | no | 4 | investigate |
| `uw_purchase_costs_v1` | unknown | table_or_config_symbol | consumed_identifier | `tower_sim/loaders/table_paths.py`, `tower_sim/run/optimizer_engine.py` | `_load_uw_purchase_costs`, `_uw_plus_unlock_action`, `_uw_unlock_action` | static | no | 4 | investigate |
| `uw_scalar` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `uw_section` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py` | `_level_from_provenance`, `_uw_provenance` | static | no | 4 | investigate |
| `uw_smart_missiles_cooldown` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_smart_missiles_cover_fire` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_smart_missiles_damage` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_smart_missiles_quantity` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_spotlight_angle` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_spotlight_light_range` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_spotlight_multiplier` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_spotlight_quantity` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_state` | unknown | runtime_state_field | declared_identifier | `tower_sim/run/optimizer_engine.py` | `_stone_actions` | mixed | no | 4 | investigate |
| `uw_table_level` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py` | `_load_uw_track_values` | static | no | 4 | investigate |
| `uw_table_value` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py` | `_load_uw_track_values` | static | no | 4 | investigate |
| `uw_tables_v2_1_2` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_track_costs` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/run/optimizer_engine.py` | `_stone_actions` | mixed | no | 4 | investigate |
| `uw_track_ladders` | unknown | table_or_config_symbol | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/loaders/table_paths.py`, `tower_sim/run/optimizer_engine.py` | `_load_uw_track_ladders`, `_load_uw_track_values` | static | no | 4 | investigate |
| `uw_track_ladders_v1` | unknown | table_or_config_symbol | consumed_identifier | `tower_sim/loaders/table_paths.py`, `tower_sim/run/optimizer_engine.py` | `_load_uw_track_ladders`, `_uw_track_upgrade_action` | static | no | 4 | investigate |
| `uw_track_upgrade` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/run/optimizer_engine.py` | `_uw_track_upgrade_action` | mixed | no | 4 | investigate |
| `uw_tracks` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/registry/naming_contract.py`, `tower_sim/run/optimizer_engine.py` | `_build_named_entity_maps`, `_parse_uw_rows`, `_stone_actions` | static | no | 4 | investigate |
| `uw_unlock` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/run/optimizer_engine.py` | `_uw_unlock_action` | mixed | no | 4 | investigate |
| `uw_unlock_cost` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/run/optimizer_engine.py` | `_load_uw_purchase_costs` | mixed | no | 4 | investigate |
| `uw_unlock_count` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/run/optimizer_engine.py` | `_load_uw_purchase_costs` | mixed | no | 4 | investigate |
| `uw_unlocked_count` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/run/optimizer_engine.py` | `_parse_uw_rows`, `_stone_actions` | mixed | no | 4 | investigate |
| `uw_unmapped` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/registry/naming_contract.py` | `validate_account_snapshot_naming` | static | no | 4 | investigate |
| `validate_boss_survivability_spec` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | — | runtime | no | 4 | investigate |
| `value_percent_points` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/loaders/wiki/labs_eals_ehls.py`, `tower_sim/loaders/wiki/promote_labs_tables.py` | `_discover_lab_sources`, `_parse_value`, `get_eals_lab_pp` | static | no | 4 | investigate |
| `vault_pct` | alias | table_or_config_symbol | declared_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/engines/econ_current.py` | — | static | no | 7 | alias-map |
| `wa_card` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/wave_time.py` | `wa_reduction_from_snapshot` | runtime | no | 4 | investigate |
| `wall_current` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_survivability.py` | `_time_to_death` | runtime | no | 4 | investigate |
| `wall_fort_overheal_ratio` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 4 | investigate |
| `wall_fortification` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/loaders/ep_export_loader.py` | — | static | no | 4 | investigate |
| `wall_health` | target_stat | canonical_target_stat | consumed_identifier | `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, … | `_apply_unique_effects`, `_compile_relic_stat_inputs` | static | target_stat | 10 | aligned |
| `wall_health_data` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/stat_input_compiler.py` | `compile_workshop_values_at_wave` | static | no | 4 | investigate |
| `wall_health_input` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat_stat_derivation.py` | `_wall_ratio_from_ids` | runtime | no | 4 | investigate |
| `wall_health_lab` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_wall_survivability_aliases`, `compile_workshop_values_at_wave` | static | no | 4 | investigate |
| `wall_health_ratio` | unknown | table_or_config_symbol | declared_identifier | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py` | `_compile_wall_survivability_aliases`, `_wall_ratio_from_ids`, `compile_workshop_values_at_wave` | mixed | no | 4 | investigate |
| `wall_health_ratio_input` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_wall_survivability_aliases` | static | no | 4 | investigate |
| `wall_health_regen_mult_x` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_unique_effects` | static | no | 4 | investigate |
| `wall_hp` | report-only | report_or_audit_field | declared_and_emitted | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/engines/combat/boss_survivability.py`, … | `_apply_unique_effects`, `_build_reaches_stat_input`, `_compile_base_stat_inputs` | mixed | no | 7 | classify |
| `wall_lab_` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/loaders/wiki/promote_labs_tables.py` | `_discover_lab_sources` | static | no | 4 | investigate |
| `wall_lab_wall_health` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/loaders/wiki/labs.py` | — | static | no | 4 | investigate |
| `wall_lab_wall_regen` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/loaders/wiki/labs.py` | — | static | no | 4 | investigate |
| `wall_max` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_survivability.py` | `_time_to_death` | runtime | no | 4 | investigate |
| `wall_ratio` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/survivability_pipeline.py` | `_compile_base_stat_inputs` | mixed | no | 4 | investigate |
| `wall_rebuild` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/registry/stat_registry.py` | `_compile_relic_stat_inputs`, `default_registry` | static | no | 4 | investigate |
| `wall_regen` | target_stat | canonical_target_stat | declared_and_emitted | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/engines/combat/boss_survivability.py`, … | `_apply_unique_effects`, `_build_reaches_stat_input`, `_compile_base_stat_inputs` | mixed | target_stat | 10 | split |
| `wall_regen_blocked` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_wall_survivability_aliases`, `compile_workshop_values_at_wave` | static | no | 4 | investigate |
| `wall_regen_data` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/stat_input_compiler.py` | `compile_workshop_values_at_wave` | static | no | 4 | investigate |
| `wall_regen_entry` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_wall_survivability_aliases`, `compile_workshop_values_at_wave` | static | no | 4 | investigate |
| `wall_regen_input` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat_stat_derivation.py` | `_wall_ratio_from_ids` | runtime | no | 4 | investigate |
| `wall_regen_lab` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_wall_survivability_aliases`, `compile_workshop_values_at_wave` | static | no | 4 | investigate |
| `wall_regen_per_hit` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_survivability.py` | `_time_to_death` | runtime | no | 4 | investigate |
| `wall_regen_ratio` | unknown | table_or_config_symbol | declared_identifier | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, … | `_compile_base_stat_inputs`, `_compile_wall_survivability_aliases`, `_wall_ratio_from_ids` | mixed | no | 4 | investigate |
| `wall_regen_ratio_input` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_wall_survivability_aliases` | static | no | 4 | investigate |
| `wall_thorns_entry` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_wall_survivability_aliases`, `compile_workshop_values_at_wave` | static | no | 4 | investigate |
| `wall_thorns_lvl` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | — | static | no | 4 | investigate |
| `wall_thorns_mult` | alias | approved_alias | emitted_key | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `_compile_wall_survivability_aliases`, `compile_workshop_values_at_wave`, `default_registry` | static | no | 7 | alias-map |
| `wave_accel_mastery_lvl` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `wave_actual` | unknown | runtime_state_field | declared_identifier | `tower_sim/loaders/bc_heat_loader.py` | `_load_tournament_heat_values`, `value_at` | static | no | 4 | investigate |
| `wave_attack_index` | runtime | runtime_state_field | emitted_key | `tower_sim/engines/stat_engine.py`, `tower_sim/engines/stat_snapshots.py`, `tower_sim/registry/combat_stat_contract.py`, … | `_append_wave_state_inputs`, `_build_reaches_stat_input`, `_resolve_at_wave_value` | static | no | 7 | classify |
| `wave_damage` | unknown | runtime_state_field | declared_and_emitted | `tower_sim/engines/combat/boss_engine.py`, `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/survivability_pipeline.py` | `_missing_inputs`, `_resolve_survivability_verdict`, `resolve_canonical_wave_damage` | runtime | no | 4 | investigate |
| `wave_damage_error` | unknown | runtime_state_field | emitted_key | `tower_sim/engines/combat_stat_derivation.py` | `resolve_canonical_wave_damage` | runtime | no | 4 | investigate |
| `wave_damage_strict` | report-only | report_or_audit_field | consumed_identifier | `tower_sim/audit/status.py` | `_components` | report | no | 7 | classify |
| `wave_damage_table` | unknown | table_or_config_symbol | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | `resolve_canonical_wave_damage`, `resolve_canonical_wave_damage_for_attack_wave` | runtime | no | 4 | investigate |
| `wave_damage_tier` | unknown | runtime_state_field | declared_and_emitted | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/run/problem_spec.py`, `tower_sim/run/spec_loader.py` | `_parse_scenario`, `resolve_canonical_wave_damage`, `resolve_canonical_wave_damage_for_attack_wave` | runtime | no | 4 | investigate |
| `wave_damage_wave` | runtime | runtime_state_field | emitted_key | `tower_sim/engines/combat_stat_derivation.py` | `resolve_canonical_wave_damage` | runtime | no | 7 | classify |
| `wave_engine` | report-only | report_or_audit_field | consumed_identifier | `tower_sim/audit/status.py`, `tower_sim/engines/stat_engine.py` | `_append_wave_state_inputs`, `_components` | report | no | 7 | classify |
| `wave_health_index` | runtime | runtime_state_field | emitted_key | `tower_sim/engines/stat_engine.py`, `tower_sim/engines/stat_snapshots.py`, `tower_sim/registry/combat_stat_contract.py`, … | `_append_wave_state_inputs`, `_build_reaches_stat_input`, `_resolve_at_wave_value` | static | no | 7 | classify |
| `wave_inputs` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/stat_pipeline.py` | `build_canonical_stat_pipeline_for_problem_spec` | mixed | no | 4 | investigate |
| `wave_limit` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py` | `compile_workshop_values_at_wave` | static | no | 4 | investigate |
| `wave_max` | unknown | runtime_state_field | declared_identifier | `tower_sim/loaders/ep_export_loader.py`, `tower_sim/run/problem_spec.py`, `tower_sim/run/spec_loader.py` | `_parse_scenario`, `extract_max_wave_targets` | static | no | 4 | investigate |
| `wave_probe` | unknown | runtime_state_field | declared_identifier | `tower_sim/run/problem_spec.py`, `tower_sim/run/spec_loader.py` | `_parse_scenario` | mixed | no | 4 | investigate |
| `wave_raw` | unknown | runtime_state_field | declared_identifier | `tower_sim/loaders/perk_timeline_loader.py` | `_parse_row` | static | no | 4 | investigate |
| `wave_row` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/stat_pipeline.py` | `resolve_wave_snapshot_for_problem_spec` | mixed | no | 4 | investigate |
| `wave_rows` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_pipeline.py` | `resolve_wave_snapshot_for_problem_spec` | mixed | no | 4 | investigate |
| `wave_skip_mastery_lvl` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `wave_snapshot` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_pipeline.py` | `resolve_wave_snapshot_for_problem_spec` | mixed | no | 4 | investigate |
| `wave_snapshot_error` | unknown | runtime_state_field | emitted_key | `tower_sim/engines/stat_pipeline.py` | `resolve_wave_snapshot_for_problem_spec` | mixed | no | 4 | investigate |
| `wave_snapshot_inputs` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_pipeline.py` | `resolve_wave_snapshot_for_problem_spec` | mixed | no | 4 | investigate |
| `wave_state` | unknown | runtime_state_field | declared_and_emitted | `tower_sim/engines/stat_pipeline.py`, `tower_sim/engines/stat_snapshots.py`, `tower_sim/engines/survivability_pipeline.py` | `build_at_wave_snapshot`, `build_canonical_stat_pipeline_for_problem_spec`, `build_survivability_report` | mixed | no | 4 | investigate |
| `wave_state_from_row` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | — | runtime | no | 4 | investigate |
| `wave_tier` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/survivability_pipeline.py` | `_resolve_wave_damage`, `resolve_canonical_wave_damage`, `resolve_canonical_wave_damage_for_attack_wave` | runtime | no | 4 | investigate |
| `wave_time` | runtime | runtime_state_field | declared_identifier | `tower_sim/engines/econ_current.py` | `econ_current` | mixed | no | 7 | classify |
| `wave_time_boost` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 7 | classify |
| `waves_required_lab` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/perk_timeline_generator.py` | `load_policy` | mixed | no | 4 | investigate |
| `waves_skipped` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/free_upgrades.py` | `expected_upgrades_per_wave` | mixed | no | 4 | investigate |
| `waves_skipped_per_wave` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/workshop_progression.py` | `simulate_workshop_progression` | mixed | no | 7 | classify |
| `waves_to_end` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/workshop_progression.py` | `simulate_workshop_progression` | mixed | no | 4 | investigate |
| `weight_percent` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/loaders/perk_tables.py` | `load_perk_pool_weights` | static | no | 4 | investigate |
| `wmax_wave_relative` | runtime | report_or_audit_field | consumed_identifier | `tower_sim/audit/max_wave_ep_parity.py` | `_resolve_wmax_tolerance` | runtime | no | 7 | classify |
| `workshop_attack_speed` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_bounce_shot_chance` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/engines/survivability_pipeline.py`, … | `default_registry` | static | no | 4 | investigate |
| `workshop_bounce_shot_range` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_cash_bonus` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/registry/stat_registry.py` | `_apply_card_effects`, `default_registry` | static | no | 4 | investigate |
| `workshop_cash_per_wave` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 7 | classify |
| `workshop_coins_per_kill_bonus` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/engines/survivability_pipeline.py`, … | `_apply_card_effects`, `default_registry` | static | no | 4 | investigate |
| `workshop_coins_per_wave` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 7 | classify |
| `workshop_critical_chance` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/loaders/ep_export_loader.py`, … | `default_registry` | static | no | 4 | investigate |
| `workshop_critical_factor` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_damage` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/loaders/ep_export_loader.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_damage_per_meter` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/loaders/ep_export_loader.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_defense_absolute` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/loaders/ep_export_loader.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_defense_percent` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_enemy_attack_level_skip` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `_parse_workshop_enhancement_multipliers`, `default_registry` | static | no | 4 | investigate |
| `workshop_enemy_health_level_skip` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `_parse_workshop_enhancement_multipliers`, `default_registry` | static | no | 4 | investigate |
| `workshop_enemy_level_skip` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_free_attack_upgrade` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/loaders/ep_export_loader.py`, … | `_free_upgrade_chances`, `default_registry` | static | no | 4 | investigate |
| `workshop_free_defense_upgrade` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/loaders/ep_export_loader.py`, … | `_free_upgrade_chances`, `default_registry` | static | no | 4 | investigate |
| `workshop_health` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_health_regen` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_knockback_chance` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_land_mine` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_land_mine_chance` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/engines/survivability_pipeline.py`, … | `default_registry` | static | no | 4 | investigate |
| `workshop_land_mine_damage` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_land_mine_radius` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_level_to_chance` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/loaders/wiki/enemy_level_skip.py` | — | static | no | 4 | investigate |
| `workshop_multishot_chance` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/loaders/ep_export_loader.py`, … | `default_registry` | static | no | 4 | investigate |
| `workshop_multishot_targets` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/engines/survivability_pipeline.py`, … | `default_registry` | static | no | 4 | investigate |
| `workshop_orb_size` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_orb_speed` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_orbs` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_package_chance` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/engines/survivability_pipeline.py`, … | `_apply_card_effects`, `default_registry` | static | no | 4 | investigate |
| `workshop_range_meters` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/engines/survivability_pipeline.py`, … | `_apply_card_effects`, `default_registry` | static | no | 4 | investigate |
| `workshop_rapid_fire_chance` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/loaders/ep_export_loader.py`, … | `default_registry` | static | no | 4 | investigate |
| `workshop_rapid_fire_duration` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/loaders/ep_export_loader.py`, … | `default_registry` | static | no | 4 | investigate |
| `workshop_recovery_packages` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/loaders/ep_export_loader.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_rend_armor_chance` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_rend_armor_mult` | alias | approved_alias | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/loaders/ep_export_loader.py`, … | `default_registry` | static | no | 7 | alias-map |
| `workshop_shockwave` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_shockwave_frequency` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_shockwave_size` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_super_crit_chance` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_super_crit_mult` | alias | approved_alias | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 7 | alias-map |
| `workshop_super_crit_mult_alt` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_thorn_damage` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_thorns` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/survivability_pipeline.py` | `_resolve_thorns_inputs` | mixed | no | 4 | investigate |
| `workshop_wall_fortification` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_wall_health` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, … | `_compile_wall_survivability_aliases`, `_wall_ratio_from_ids`, `compile_workshop_values_at_wave` | mixed | no | 4 | investigate |
| `workshop_wall_rebuild` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_wall_regen` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `_compile_wall_survivability_aliases`, `_wall_ratio_from_ids`, `compile_workshop_values_at_wave` | mixed | no | 4 | investigate |

## 3. Reduced candidate set for ownership audit (Phase 1C eligible)
- Candidate count: **41**
- Inclusion rule: bucket in `{canonical_target_stat, canonical_contributor_input, approved_alias, derived_stat}` and not runtime-stage-only.
| repo_name | bucket | stage | ledger_match | action |
|---|---|---|---|---|
| `assist_mult` | approved_alias | mixed | no | split |
| `attack_speed` | canonical_target_stat | static | target_stat | aligned |
| `bounce_shot_chance` | canonical_target_stat | static | target_stat | aligned |
| `chain_lightning_chance` | canonical_target_stat | static | target_stat | aligned |
| `chain_lightning_quantity` | canonical_target_stat | static | target_stat | aligned |
| `coins_per_kill_bonus` | canonical_target_stat | static | target_stat | aligned |
| `coins_per_kill_mult` | approved_alias | mixed | no | split |
| `critical_chance` | canonical_target_stat | static | target_stat | aligned |
| `damage` | canonical_target_stat | mixed | target_stat | split |
| `damage_per_meter` | canonical_target_stat | static | target_stat | aligned |
| `death_ray_damage_mult` | approved_alias | static | no | alias-map |
| `defense_absolute` | canonical_target_stat | static | target_stat | aligned |
| `delta_mult` | approved_alias | static | no | alias-map |
| `eals_pct` | approved_alias | static | no | alias-map |
| `ehls_pct` | approved_alias | static | no | alias-map |
| `health` | canonical_target_stat | mixed | target_stat | split |
| `health_regen` | canonical_target_stat | static | target_stat | aligned |
| `inner_land_mines_quantity` | canonical_target_stat | static | target_stat | aligned |
| `knockback_mult` | approved_alias | static | no | alias-map |
| `lab_pct` | approved_alias | static | no | alias-map |
| `mastery_mult` | approved_alias | mixed | no | split |
| `max_rend_mult` | approved_alias | static | no | alias-map |
| `multishot_chance` | canonical_target_stat | static | target_stat | aligned |
| `multishot_targets` | canonical_target_stat | static | target_stat | aligned |
| `orb_damage_mult` | approved_alias | static | no | alias-map |
| `orb_speed` | canonical_target_stat | static | target_stat | aligned |
| `plasma_cannon_damage_mult` | approved_alias | static | no | alias-map |
| `rapid_fire_chance` | canonical_target_stat | static | target_stat | aligned |
| `smart_missiles_quantity` | canonical_target_stat | static | target_stat | aligned |
| `stone_pct` | approved_alias | static | no | alias-map |
| `super_crit_chance` | canonical_target_stat | static | target_stat | aligned |
| `super_crit_mult` | approved_alias | static | no | alias-map |
| `super_crit_multiplier` | canonical_target_stat | static | target_stat | aligned |
| `thorns_damage_mult` | approved_alias | mixed | no | split |
| `thorns_mult` | approved_alias | mixed | no | split |
| `upgrade_mult` | approved_alias | static | no | alias-map |
| `wall_health` | canonical_target_stat | static | target_stat | aligned |
| `wall_regen` | canonical_target_stat | mixed | target_stat | split |
| `wall_thorns_mult` | approved_alias | static | no | alias-map |
| `workshop_rend_armor_mult` | approved_alias | static | no | alias-map |
| `workshop_super_crit_mult` | approved_alias | static | no | alias-map |

## 4. Excluded sets
### runtime-only
- Count: **200**
`at_wave`, `at_wave_inputs`, `at_wave_missing`, `at_wave_snapshot`, `at_wave_stage`, `at_wave_stage_missing`, `at_wave_stage_skipped`, `at_wave_stats`, `attack_interval`, `base_cooldown`, `base_cooldown_s`, `base_duration`, `boss_attack`, `boss_attack_interval`, `boss_attack_mult`, `boss_enrage_mult`, `boss_hp`, `boss_hp_frac_damage`, `boss_hp_frac_damage_per_hit`, `boss_hp_mult`, `boss_hp_remaining_mult`, `boss_hp_remaining_mult_per_hit`, `boss_interval_waves`, `boss_kills_tower`, `boss_params_loader`, `boss_survivability_invalid`, `bot_amplify_cooldown`, `bot_amplify_duration`, `bot_bonus_multiplier`, `bot_cooldown_multiplier`, `bot_duration_multiplier`, `bot_flame_cooldown`, `bot_golden_cooldown`, `bot_golden_duration`, `bot_levels`, `bot_thunder_cooldown`, `bot_thunder_duration`, `build_canonical_wave_row`, `build_canonical_wave_snapshot`, `canonical_stat_inputs_for_wave`, `chrono_field_cooldown`, `chrono_field_duration`, `coin_mult`, `coin_multiplier`, `coin_sum`, `compile_workshop_values_at_wave`, `cooldown_s`, `current_wave`, `damage_mult`, `damage_mult_sum`, `damage_multiplier`, `damage_reduction`, `damage_remaining`, `damage_taken`, `death_wave_cooldown`, `death_wave_damage`, `death_wave_quantity`, `default_wave_damage_tier`, `defense_abs`, `duration_s`, `eals_ramp`, `effective_damage`, `effective_damage_per_sec`, `effective_regen`, `effective_regen_per_sec`, `ehls_ramp`, `electrons_damage_frac`, `enemy_attack`, `enemy_attack_mult`, `enemy_attack_wave`, `enemy_health_wave`, `enemy_hp`, `enemy_level_skip_reduction`, `enrage_mult`, `expected_coin_multiplier`, `expected_damage_multiplier`, `expected_damage_taken`, `extract_max_wave_targets`, `final_wave`, `flame_bot_damage_reduction_multiplier`, `from_wave`, `gold_bot_cooldown_lvl`, `gold_bot_duration_lvl`, `golden_tower_cooldown`, `golden_tower_duration`, `gt_duration_lvl`, `heat_mult`, `incoming_damage`, `inner_land_mines_cooldown`, `is_boss`, `lab_enemy_attack_level_skip`, `lab_enemy_health_level_skip`, `max_wave_ids`, `max_wave_latest`, `max_wave_runner`, `min_wave`, `missing_at_wave`, `missing_required_at_wave_stats`, `missing_wave`, `missing_wave_state`, `module_`, `module_context`, `module_system_state`, `module_unmapped_by_layer`, `net_damage`, `net_damage_per_sec`, `next_wave`, `orb_damage_frac`, `out_of_range`, `package_heal`, `package_regen`, `pc_boss_mult`, `per_hit_boss_frac`, `poison_swamp_cooldown`, `poison_swamp_duration`, `preset_cards`, `ramp_waves`, `rapid_fire_duration`, `raw_damage`, `reduced_damage`, `regen_per_hit`, `regen_per_sec`, `remaining_enemy_hp`, `required_max_wave_other`, `required_max_wave_other_stat_inputs`, `resolve_canonical_wave_damage`, `resolve_canonical_wave_damage_for_attack_wave`, `resolve_wave_state_for_wave`, `selected_cards`, `skip_ramp`, `smart_missiles_cooldown`, `survivability_loadout_unknown_card`, `survivability_loadout_unsupported_card`, `target_wall_hp_base`, `target_wall_regen_base`, `target_wave`, `thorns_frac`, `thorns_pct`, `total_damage`, `tower_damage_taken`, `tower_kills_boss`, `tower_regen_per_sec`, `transfer_multiplier`, `unknown_card`, `unsupported_card`, `uw_black_hole_cooldown`, `uw_black_hole_duration`, `uw_chrono_field_cooldown`, `uw_chrono_field_duration`, `uw_death_wave_cooldown`, `uw_death_wave_damage`, `uw_death_wave_kill_wall`, `uw_death_wave_quantity`, `uw_golden_tower_cooldown`, `uw_golden_tower_duration`, `uw_inner_land_mines_cooldown`, `uw_poison_swamp_cooldown`, `uw_poison_swamp_duration`, `uw_smart_missiles_cooldown`, `uw_state`, `validate_boss_survivability_spec`, `wa_card`, `wall_current`, `wall_health_input`, `wall_max`, `wall_regen_input`, `wall_regen_per_hit`, `wave_accel_mastery_lvl`, `wave_actual`, `wave_attack_index`, `wave_damage`, `wave_damage_error`, `wave_damage_tier`, `wave_damage_wave`, `wave_health_index`, `wave_inputs`, `wave_limit`, `wave_max`, `wave_probe`, `wave_raw`, `wave_row`, `wave_rows`, `wave_skip_mastery_lvl`, `wave_snapshot`, `wave_snapshot_error`, `wave_snapshot_inputs`, `wave_state`, `wave_state_from_row`, `wave_tier`, `wave_time`, `wave_time_boost`, `waves_skipped_per_wave`, `workshop_cash_per_wave`, `workshop_coins_per_wave`, `workshop_enemy_attack_level_skip`, `workshop_enemy_health_level_skip`, `workshop_enemy_level_skip`, `workshop_rapid_fire_duration`, `workshop_shockwave_frequency`, `workshop_shockwave_size`

### report-only
- Count: **34**
`boss_engine`, `boss_survivability`, `cards_lib`, `def_pct`, `defense_percent`, `enhancement_multiplier`, `expected_skipped_waves`, `key_modules`, `lineage_required_max_wave_gap_count`, `make_wave_state`, `max_wave`, `max_wave_report`, `module_name`, `modules_lib`, `modules_library`, `regen`, `required_max_wave`, `required_max_wave_gap_count`, `required_max_wave_gaps`, `required_max_wave_stat_input_ids`, `skipped_missing_targets`, `test_boss_engine`, `test_boss_survivability`, `test_max_wave_observability`, `test_max_wave_v1_contract`, `test_wave_damage_strict`, `test_wave_engine`, `tier_multiplier`, `tower_regen`, `uw_lib`, `wall_hp`, `wave_damage_strict`, `wave_engine`, `wmax_wave_relative`

### config/table symbols
- Count: **121**
`bc_mult`, `boss_hit_interval`, `boss_hit_interval_v1`, `boss_wall_thorns_frac_v1`, `bot_table`, `bot_upgrades`, `bot_upgrades_v1`, `card_level`, `card_masteries`, `card_masteries_v1`, `card_pct`, `card_val`, `cards_rare`, `cl_chance`, `cl_damage`, `coin_level`, `defense`, `dwdamage`, `dwdamageamp`, `enemy_damage_table`, `enemy_health_table`, `ep_edamage_cr5`, `ep_edamage_cs5`, `ep_edamage_ct5`, `ep_edamage_cu5`, `ep_edamage_cv5`, `ep_edamage_cw5`, `ep_edamage_cx5`, `ep_edamage_cz5`, `ep_edamage_da5`, `ep_edamage_db5`, `ep_edamage_dc5`, `ep_edamage_dd5`, `ep_edamage_de5`, `ep_edamage_df5`, `ep_edamage_dg5`, `ep_edamage_dh5`, `ep_edamage_di5`, `ep_edamage_dj5`, `ep_edamage_dk5`, `ep_edamage_dl5`, `ep_edamage_dm5`, `ep_edamage_dp5`, `ep_edamage_ds5`, `ep_edamage_dt5`, `ep_edamage_du5`, `ep_edamage_dv5`, `ep_edamage_dw5`, `ep_edamage_dy5`, `ep_edamage_eb5`, `ep_edamage_ef5`, `ep_lambda_ep_uw_sl_coverage`, `ep_lambda_ep_uw_total_damage`, `ep_lambda_epd_crit_chance`, `ep_lambda_epd_critical`, `ep_lambda_epd_multishot`, `ep_lambda_epd_range`, `ep_lambda_epd_rangedpm`, `ep_lambda_epd_supertower_cooldown`, `ep_lambda_epd_uwcritical`, `ep_lambda_eph_def_pct`, `ep_lambda_eph_health`, `ep_lambda_eph_regen`, `ep_lambda_eph_wall_health`, `ep_lambda_eph_wall_regen`, `ep_lambda_stat_uw_cl_final_ch`, `ep_lambda_stat_uw_cl_final_dmg`, `ep_lambda_stat_uw_cl_final_qty`, `ep_lambda_stat_uw_dw_final_cd`, `ep_lambda_stat_uw_dw_final_dmg`, `ep_lambda_stat_uw_dw_final_qty`, `ep_lambda_stat_uw_sl_final_angle`, `ep_lambda_stat_uw_sl_final_dmg`, `ep_lambda_stat_uw_sl_final_lr`, `ep_lambda_stat_uw_sm_final_cd`, `ep_lambda_stat_uw_sm_final_cf`, `ep_lambda_stat_uw_sm_final_dmg`, `ep_lambda_stat_uw_sm_final_qty`, `has_card`, `kill_at_range`, `max_recovery_vault_mult`, `max_recovery_wse_mult`, `module_main_effect_bands`, `module_main_effect_bands_v1`, `module_main_effect_bases`, `module_main_effect_bases_v1`, `module_substats`, `module_substats_v1`, `multi_rapid_bounce`, `op_chain`, `plasma_cannon_card_frac_v1`, `range_dpm`, `range_multiplier`, `recovery_package_max`, `relic_pct`, `rend_mult`, `sl_damage`, `sl_lightrange`, `sm_cooldown`, `sm_damage`, `st_uw_mastery`, `standard_perks_bonus_mult`, `tier_wave_damage`, `tier_wave_damage_legacy`, `tournament_more_bosses_static`, `tournament_wave_damage`, `tournament_wave_damage_legacy`, `uw_crit_card`, `uw_damage_boost`, `uw_plus_ladders`, `uw_plus_ladders_v1`, `uw_purchase_costs`, `uw_purchase_costs_v1`, `uw_track_ladders`, `uw_track_ladders_v1`, `vault_pct`, `wall_fort_overheal_ratio`, `wall_health_ratio`, `wall_regen_ratio`, `wall_thorns_lvl`, `wave_damage_table`

### implementation artifacts
- Count: **4**
`build_edamage_stat_inputs`, `load_card_masteries`, `resolve_card_mastery_value`, `resolve_damage_perk_multiplier`

## 5. Top unresolved identifiers that still block safe ownership analysis
| repo_name | prior category | stage | confidence | reason_to_block |
|---|---|---|---:|---|
| `absolute_chance_subtract` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `attack` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `bh_coin_bonus_lvl` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `bonus_multiplier` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `bot_amplify_bonus` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `bot_flame_damage` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `bot_flame_damage_reduction` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `bot_golden_bonus` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `card_id` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `card_mastery` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `card_name` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `card_presets` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `coin_actions_not_implemented` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `coins_card` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `coins_mastery_lvl` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `coins_per_kill_bonus_lvl` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `compute_edamage_outputs` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `crit_multiplier` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `dw_coin_bonus_lvl` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `edamage` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `epd_crit_chance` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `epd_critical` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `equipped_cards` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `extra_orb_mastery_lvl` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `free_attack_upgrade_rate` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `generator_module` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `has_coins_perk` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `has_module` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `knockback_multiplier` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `locked_uws` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `module_contribution_ledger` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `module_id` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `module_layer_gaps` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `module_presets` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `module_primary_effect` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `module_rules` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `module_substat_unmapped` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `module_summary` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `module_unique_unmapped` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `multiplier_efficiency` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `multiplier_level` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `next_percent` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `next_uw_plus_unlock_cost` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `next_uw_unlock_cost` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `perk_multiplier` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `spotlight_coin_bonus_lvl` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `time_multiplier_mode` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `tower_crit_factor` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `tower_damage` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `uw_` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `uw_costs` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `uw_ids` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `uw_plus` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `uw_plus_costs` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `uw_plus_locked` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `uw_plus_track_upgrade` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `uw_plus_tracks` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `uw_plus_unlock` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `uw_plus_unlock_cost` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |
| `uw_plus_unlock_count` | unknown | mixed | 4 | ambiguous semantic meaning; could overlap canonical stat concept |

## 6. Recommendation
- Repository is **not ready** for full Phase 1C ownership audit. Another normalization pass is needed first on `legacy_or_unresolved` identifiers (especially mixed-stage names).
- Smallest-safe next step: triage unresolved identifiers in top hotspot files from Phase 1B.1 before ownership assertions.
