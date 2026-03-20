# Phase 1B.3 Ledger-Driven Namespace Normalization

## Files inspected
- `audit/phase_1b_stat_surface_inventory.md`
- `audit/reference/tower_sim_3_handover/towersim_static_ledger_latest.csv`
- `audit/reference/tower_sim_3_handover/towersim_static_ledger_naming_contract_v1_10.md`
- `audit/reference/tower_sim_3_handover/towersim_v1_handover_pack.md`
- `legacy/governance_handoff/CODEX_HANDOFF_V1_FULL.md`
- `legacy/governance_handoff/STATUS_V1.yaml`
- `CONTRACT.md`

## 1. Normalized summary counts
- `canonical_target_stat`: 23
- `canonical_contributor_input`: 38
- `approved_alias`: 2
- `derived_stat`: 26
- `runtime_state_field`: 233
- `report_or_audit_field`: 7
- `table_or_config_symbol`: 98
- `implementation_artifact`: 4
- `legacy_or_unresolved`: 202
- Total triaged identifiers: **633**

## 2. Normalized inventory table
| repo_name | prior_category | normalized_bucket | semantic_role | source_surface | owner_function | stage | ledger_match | confidence (0-10) | recommended_action |
|---|---|---|---|---|---|---|---|---:|---|
| `absolute_chance_subtract` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/tier_rule_apply.py` | — | mixed | no | 4 | investigate |
| `assist_mult` | alias | legacy_or_unresolved | declared_identifier | `tower_sim/engines/econ_current.py` | `EPG_MODULE_BONUS` | mixed | no | 4 | investigate |
| `assist_multiplier` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_armor_module_multiplier` | static | no | 4 | investigate |
| `at_wave` | runtime | runtime_state_field | declared_identifier | `tower_sim/engines/survivability_pipeline.py`, `tower_sim/registry/stat_registry.py` | `build_survivability_report` | static | no | 7 | exclude-runtime |
| `at_wave_inputs` | runtime | runtime_state_field | declared_identifier | `tower_sim/engines/stat_snapshots.py` | `build_at_wave_snapshot` | mixed | no | 7 | exclude-runtime |
| `at_wave_missing` | runtime | runtime_state_field | declared_identifier | `tower_sim/engines/stat_pipeline.py` | `build_canonical_stat_pipeline_for_problem_spec` | mixed | no | 7 | exclude-runtime |
| `at_wave_snapshot` | runtime | runtime_state_field | declared_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/engines/survivability_pipeline.py` | `build_canonical_stat_pipeline_for_problem_spec`, `build_survivability_report`, `derive_canonical_combat_snapshot` | runtime | no | 7 | exclude-runtime |
| `at_wave_stage` | runtime | runtime_state_field | declared_identifier | `tower_sim/engines/stat_pipeline.py` | `build_canonical_stat_pipeline_for_problem_spec` | mixed | no | 7 | exclude-runtime |
| `at_wave_stage_missing` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_pipeline.py` | `build_canonical_stat_pipeline_for_problem_spec` | mixed | no | 7 | exclude-runtime |
| `at_wave_stage_skipped` | runtime | runtime_state_field | emitted_key | `tower_sim/engines/stat_pipeline.py` | `build_canonical_stat_pipeline_for_problem_spec` | mixed | no | 7 | exclude-runtime |
| `at_wave_stats` | runtime | runtime_state_field | declared_identifier | `tower_sim/engines/stat_snapshots.py` | `build_at_wave_snapshot` | mixed | no | 7 | exclude-runtime |
| `attack` | unknown | canonical_contributor_input | declared_identifier | `tower_sim/engines/combat/boss_survivability.py`, `tower_sim/engines/combat/combat_engine.py`, `tower_sim/engines/free_upgrades.py`, … | `_free_upgrade_chances`, `_parse_boss_stats`, `_workshop_category` | mixed | contributor_input | 8 | aligned |
| `attack_interval` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_survivability.py`, `tower_sim/run/problem_spec.py`, `tower_sim/run/spec_loader.py` | `_parse_boss_stats` | runtime | no | 7 | exclude-runtime |
| `attack_speed` | target_stat | canonical_target_stat | declared_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/engines/edamage_formulas.py`, … | `_apply_card_effects`, `_compile_relic_stat_inputs`, `build_edamage_stat_inputs` | static | target_stat | 10 | aligned |
| `base_cooldown` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 7 | exclude-runtime |
| `base_cooldown_s` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/uptime.py` | `build_gcomp_activation_intervals` | runtime | no | 7 | exclude-runtime |
| `base_duration` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 7 | exclude-runtime |
| `bc_mult` | alias | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | — | static | no | 7 | exclude-config |
| `bh_coin_bonus_lvl` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `bonus_multiplier` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `boss_attack` | unknown | runtime_state_field | declared_and_emitted | `tower_sim/engines/combat/boss_survivability.py`, `tower_sim/engines/combat_stat_derivation.py` | `resolve_boss_fight`, `validate_boss_survivability_spec` | runtime | no | 7 | exclude-runtime |
| `boss_attack_interval` | unknown | runtime_state_field | emitted_key | `tower_sim/engines/combat_stat_derivation.py` | `validate_boss_survivability_spec` | runtime | no | 7 | exclude-runtime |
| `boss_attack_mult` | alias | runtime_state_field | consumed_identifier | `tower_sim/engines/combat/boss_params_loader.py` | `load_bc_params` | runtime | no | 7 | exclude-runtime |
| `boss_engine` | report-only | runtime_state_field | consumed_identifier | `tower_sim/audit/status.py`, `tower_sim/engines/combat/__init__.py` | `_components` | runtime | no | 7 | exclude-runtime |
| `boss_enrage_mult` | alias | runtime_state_field | emitted_key | `tower_sim/engines/combat_stat_derivation.py` | `validate_boss_survivability_spec` | runtime | no | 7 | exclude-runtime |
| `boss_hit_interval` | unknown | runtime_state_field | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 7 | exclude-runtime |
| `boss_hit_interval_v1` | unknown | runtime_state_field | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 7 | exclude-runtime |
| `boss_hp` | unknown | runtime_state_field | emitted_key | `tower_sim/engines/combat_stat_derivation.py` | `validate_boss_survivability_spec` | runtime | no | 7 | exclude-runtime |
| `boss_hp_frac_damage` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | `evaluate` | runtime | no | 7 | exclude-runtime |
| `boss_hp_frac_damage_per_hit` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | — | runtime | no | 7 | exclude-runtime |
| `boss_hp_mult` | alias | runtime_state_field | consumed_identifier | `tower_sim/engines/combat/boss_params_loader.py` | `load_bc_params` | runtime | no | 7 | exclude-runtime |
| `boss_hp_remaining_mult` | alias | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | `evaluate` | runtime | no | 7 | exclude-runtime |
| `boss_hp_remaining_mult_per_hit` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | — | runtime | no | 7 | exclude-runtime |
| `boss_interval_waves` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/tier_rule_apply.py` | — | mixed | no | 7 | exclude-runtime |
| `boss_kills_tower` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat/boss_survivability.py` | `resolve_boss_fight` | runtime | no | 7 | exclude-runtime |
| `boss_params_loader` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat/__init__.py` | — | runtime | no | 7 | exclude-runtime |
| `boss_survivability` | report-only | derived_stat | declared_identifier | `tower_sim/audit/status.py`, `tower_sim/engines/combat/__init__.py`, `tower_sim/engines/combat_stat_derivation.py`, … | `_components`, `_parse_boss_survivability`, `_parse_scenario` | runtime | no | 7 | classify-derived |
| `boss_survivability_invalid` | unknown | derived_stat | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | `validate_boss_survivability_spec` | runtime | no | 7 | classify-derived |
| `boss_wall_thorns_frac_v1` | unknown | runtime_state_field | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | — | static | no | 7 | exclude-runtime |
| `bot_amplify_bonus` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry`, `resolve_runtime_bot_effects` | mixed | no | 7 | exclude-runtime |
| `bot_amplify_cooldown` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry`, `resolve_runtime_bot_effects` | mixed | no | 7 | exclude-runtime |
| `bot_amplify_duration` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry`, `resolve_runtime_bot_effects` | mixed | no | 7 | exclude-runtime |
| `bot_amplify_range` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `bot_attribute_unmapped` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/registry/naming_contract.py` | `validate_account_snapshot_naming` | static | no | 4 | investigate |
| `bot_attributes` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/registry/naming_contract.py` | `_build_named_entity_maps`, `validate_account_snapshot_naming`, `validate_repo_naming_contract` | static | no | 4 | investigate |
| `bot_bonus_multiplier` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | `resolve_runtime_bot_effects` | runtime | no | 7 | exclude-runtime |
| `bot_cooldown_multiplier` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | `_read_profile_from_snapshot`, `resolve_runtime_bot_effects` | runtime | no | 7 | exclude-runtime |
| `bot_duration_multiplier` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | `_read_profile_from_snapshot`, `resolve_runtime_bot_effects` | runtime | no | 7 | exclude-runtime |
| `bot_flame_cooldown` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry`, `resolve_runtime_bot_effects` | mixed | no | 7 | exclude-runtime |
| `bot_flame_damage` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry`, `resolve_runtime_bot_effects` | mixed | no | 7 | exclude-runtime |
| `bot_flame_damage_reduction` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry`, `resolve_runtime_bot_effects` | mixed | no | 7 | exclude-runtime |
| `bot_flame_range` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `bot_golden_bonus` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry`, `resolve_runtime_bot_effects` | mixed | no | 7 | exclude-runtime |
| `bot_golden_cooldown` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry`, `resolve_runtime_bot_effects` | mixed | no | 7 | exclude-runtime |
| `bot_golden_duration` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry`, `resolve_runtime_bot_effects` | mixed | no | 7 | exclude-runtime |
| `bot_golden_range` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `bot_level_invalid` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_bot_stat_inputs` | static | no | 4 | investigate |
| `bot_level_missing` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_bot_stat_inputs` | static | no | 4 | investigate |
| `bot_levels` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat_stat_derivation.py` | `resolve_runtime_bot_effects` | runtime | no | 7 | exclude-runtime |
| `bot_range` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/registry/stat_registry.py` | `_apply_unique_effects`, `_compile_relic_stat_inputs`, `default_registry` | static | no | 4 | investigate |
| `bot_range_bonus_m` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_unique_effects` | static | no | 4 | investigate |
| `bot_table` | unknown | table_or_config_symbol | declared_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/naming_contract.py` | `_build_named_entity_maps`, `_compile_bot_stat_inputs` | static | no | 7 | exclude-config |
| `bot_thunder_cooldown` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 7 | exclude-runtime |
| `bot_thunder_duration` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 7 | exclude-runtime |
| `bot_thunder_linger` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `bot_thunder_range` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `bot_tracks` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_bot_stat_inputs` | static | no | 4 | investigate |
| `bot_unmapped` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/registry/naming_contract.py` | `validate_account_snapshot_naming` | static | no | 4 | investigate |
| `bot_upgrades` | unknown | table_or_config_symbol | declared_identifier | `tower_sim/loaders/account_snapshot_compiler.py`, `tower_sim/loaders/account_snapshot_loader.py`, `tower_sim/loaders/table_paths.py` | `_load_snapshot`, `_parse_bot_upgrades`, `_parse_bots` | static | no | 7 | exclude-config |
| `bot_upgrades_v1` | unknown | table_or_config_symbol | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 7 | exclude-config |
| `bot_values` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/loaders/account_snapshot_compiler.py` | `_parse_bots` | static | no | 4 | investigate |
| `bounce_shot_chance` | target_stat | canonical_target_stat | consumed_identifier | `tower_sim/loaders/ep_export_loader.py` | — | static | target_stat | 10 | aligned |
| `build_canonical_wave_row` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | — | runtime | no | 7 | exclude-runtime |
| `build_canonical_wave_snapshot` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | — | runtime | no | 7 | exclude-runtime |
| `build_edamage_stat_inputs` | unknown | implementation_artifact | consumed_identifier | `tower_sim/engines/edamage_pipeline.py` | — | mixed | no | 6 | exclude-implementation |
| `canonical_stat_inputs_for_wave` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | — | runtime | no | 7 | exclude-runtime |
| `card_canonical` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_card_effects` | static | no | 4 | investigate |
| `card_id` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/run/optimizer_patch.py` | `_validate_card_actions` | mixed | no | 4 | investigate |
| `card_level` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/engines/edamage_formulas.py` | `epd_aspd`, `epd_crit_chance` | static | no | 7 | exclude-config |
| `card_masteries` | unknown | table_or_config_symbol | declared_identifier | `tower_sim/loaders/table_paths.py`, `tower_sim/run/optimizer_engine.py` | `_load_card_masteries`, `_stone_actions` | static | no | 7 | exclude-config |
| `card_masteries_v1` | unknown | table_or_config_symbol | consumed_identifier | `tower_sim/engines/edamage_pipeline.py`, `tower_sim/loaders/table_paths.py`, `tower_sim/run/optimizer_engine.py` | `_load_card_masteries`, `_mastery_action`, `resolve_card_mastery_value` | static | no | 7 | exclude-config |
| `card_mastery` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/run/optimizer_engine.py` | `_load_card_masteries` | mixed | no | 4 | investigate |
| `card_name` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/loaders/account_snapshot_compiler.py` | `_compile_survivability_loadout_inputs_resilient`, `_level_from_provenance`, `_parse_cards` | mixed | no | 7 | exclude-runtime |
| `card_pct` | alias | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | — | static | no | 7 | exclude-config |
| `card_presets` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/loaders/account_snapshot_loader.py` | `_load_snapshot`, `_parse_card_presets`, `_resolve_loadout_inputs` | mixed | no | 7 | exclude-runtime |
| `card_unmapped` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/registry/naming_contract.py` | `validate_account_snapshot_naming` | static | no | 4 | investigate |
| `card_val` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | exclude-config |
| `cards_common` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/loaders/wiki/cards.py` | `_load_cards_df` | static | no | 4 | investigate |
| `cards_epic` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/loaders/wiki/cards.py` | `_load_cards_df` | static | no | 4 | investigate |
| `cards_inventory` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/loaders/account_snapshot_loader.py` | `_load_snapshot`, `_parse_cards` | static | no | 4 | investigate |
| `cards_lib` | report-only | report_or_audit_field | consumed_identifier | `tower_sim/audit/repo_audit.py` | `_check_modules` | report | no | 7 | exclude-report |
| `cards_rare` | unknown | runtime_state_field | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tower_sim/engines/combat/boss_engine.py`, `tower_sim/loaders/wiki/cards.py` | `_load_cards_df` | mixed | no | 7 | exclude-runtime |
| `cash_bonus` | unknown | canonical_contributor_input | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/registry/stat_registry.py` | `_compile_relic_stat_inputs`, `default_registry` | static | contributor_input | 8 | aligned |
| `chain_lightning_chance` | target_stat | canonical_target_stat | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | target_stat | 10 | aligned |
| `chain_lightning_damage` | unknown | canonical_contributor_input | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_slot_main_effect` | static | contributor_input | 8 | aligned |
| `chain_lightning_quantity` | target_stat | canonical_target_stat | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | target_stat | 10 | aligned |
| `chrono_field_cooldown` | unknown | canonical_contributor_input | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | contributor_input | 8 | aligned |
| `chrono_field_duration` | unknown | canonical_contributor_input | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | contributor_input | 8 | aligned |
| `chrono_field_speed_reduction` | unknown | canonical_contributor_input | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | contributor_input | 8 | aligned |
| `cl_chance` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | exclude-config |
| `cl_damage` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | exclude-config |
| `coin_actions_not_implemented` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/run/optimizer_engine.py` | `run_resource_optimizer` | mixed | no | 4 | investigate |
| `coin_level` | unknown | table_or_config_symbol | declared_identifier | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/loaders/account_snapshot_compiler.py`, … | `_apply_snapshot_patch`, `_parse_workshop`, `_serialize_workshop_entry` | static | no | 7 | exclude-config |
| `coin_mult` | alias | runtime_state_field | declared_identifier | `tower_sim/engines/uptime.py` | `aggregate_uptime` | runtime | no | 7 | exclude-runtime |
| `coin_multiplier` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/econ_current.py`, `tower_sim/engines/uptime.py` | `_read_profile_from_snapshot`, `build_bot_effects`, `resolve_runtime_bot_effects` | runtime | no | 7 | exclude-runtime |
| `coin_sum` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/uptime.py` | `aggregate_uptime` | runtime | no | 7 | exclude-runtime |
| `coins_bonus` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `_compile_relic_stat_inputs`, `default_registry` | static | no | 4 | investigate |
| `coins_card` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/econ_current.py` | `econ_current` | mixed | no | 4 | investigate |
| `coins_mastery_lvl` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `coins_per_kill_bonus` | target_stat | canonical_target_stat | consumed_identifier | `tower_sim/loaders/ep_export_loader.py` | — | static | target_stat | 10 | aligned |
| `coins_per_kill_bonus_lvl` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `coins_per_kill_mult` | alias | legacy_or_unresolved | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `compile_workshop_values_at_wave` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py` | — | static | no | 7 | exclude-runtime |
| `compute_edamage_outputs` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/edamage_pipeline.py` | — | mixed | no | 4 | investigate |
| `cooldown_s` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/uptime.py` | `_read_profile_from_snapshot`, `build_bot_effects`, `build_periodic_activation_intervals` | runtime | no | 7 | exclude-runtime |
| `crit_chance` | unknown | canonical_contributor_input | declared_identifier | `tower_sim/engines/edamage_pipeline.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/loaders/ep_export_loader.py` | `_compile_relic_stat_inputs`, `build_edamage_stat_inputs`, `compute_edamage_outputs` | static | contributor_input | 8 | aligned |
| `crit_factor` | unknown | canonical_contributor_input | declared_identifier | `tower_sim/engines/edamage_pipeline.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/loaders/ep_export_loader.py` | `_compile_relic_stat_inputs`, `compute_edamage_outputs` | static | contributor_input | 8 | aligned |
| `crit_multiplier` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/edamage_pipeline.py` | `build_edamage_stat_inputs`, `compute_edamage_outputs` | mixed | no | 4 | investigate |
| `critical_chance` | target_stat | canonical_target_stat | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_card_effects` | static | target_stat | 10 | aligned |
| `current_bot` | unknown | runtime_state_field | declared_identifier | `tower_sim/loaders/account_snapshot_compiler.py` | `_parse_bots` | static | no | 7 | exclude-runtime |
| `current_wave` | runtime | runtime_state_field | declared_identifier | `tower_sim/engines/perk_timeline_generator.py`, `tower_sim/loaders/perk_timeline_loader.py` | `apply_perk_timeline_to_inputs`, `generate_timeline` | static | no | 7 | exclude-runtime |
| `damage` | target_stat | canonical_target_stat | declared_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tower_sim/audit/status.py`, `tower_sim/engines/combat/boss_engine.py`, … | `_apply_card_effects`, `_compile_relic_stat_inputs`, `_components` | mixed | target_stat | 10 | aligned |
| `damage_mult` | alias | runtime_state_field | declared_identifier | `tower_sim/engines/uptime.py` | `aggregate_uptime` | runtime | no | 7 | exclude-runtime |
| `damage_mult_sum` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/uptime.py` | `aggregate_uptime` | runtime | no | 7 | exclude-runtime |
| `damage_multiplier` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/tier_rule_apply.py`, `tower_sim/engines/uptime.py` | `_read_profile_from_snapshot`, `build_bot_effects`, `resolve_runtime_bot_effects` | runtime | no | 7 | exclude-runtime |
| `damage_per_meter` | target_stat | canonical_target_stat | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/loaders/ep_export_loader.py`, … | `_compile_relic_stat_inputs`, `default_registry` | static | target_stat | 10 | aligned |
| `damage_reduction` | unknown | canonical_contributor_input | declared_identifier | `tower_sim/engines/combat/boss_engine.py`, `tower_sim/engines/combat/boss_survivability.py`, `tower_sim/engines/combat_stat_derivation.py`, … | `_read_profile_from_snapshot`, `build_bot_effects`, `evaluate` | runtime | contributor_input | 8 | aligned |
| `damage_remaining` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_survivability.py` | `_time_to_death` | runtime | no | 7 | exclude-runtime |
| `damage_taken` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/uptime.py` | `aggregate_uptime` | runtime | no | 7 | exclude-runtime |
| `death_ray_damage_mult` | alias | legacy_or_unresolved | emitted_key | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/engines/tier_rule_apply.py`, … | `_apply_condition`, `_build_reaches_stat_input`, `_compile_base_stat_inputs` | static | no | 4 | investigate |
| `death_wave_cooldown` | runtime | canonical_contributor_input | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | contributor_input | 8 | aligned |
| `death_wave_damage` | runtime | canonical_contributor_input | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_slot_main_effect` | static | contributor_input | 8 | aligned |
| `death_wave_quantity` | runtime | canonical_contributor_input | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | contributor_input | 8 | aligned |
| `def_pct` | report-only | runtime_state_field | declared_and_emitted | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/engines/combat_stat_derivation.py`, … | `_apply_card_effects`, `_build_reaches_stat_input`, `_compile_base_stat_inputs` | mixed | no | 7 | exclude-runtime |
| `default_wave_damage_tier` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | — | runtime | no | 7 | exclude-runtime |
| `defense` | unknown | canonical_contributor_input | declared_identifier | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/engines/free_upgrades.py`, `tower_sim/engines/stat_input_compiler.py`, … | `_free_upgrade_chances`, `_parse_tower_defense`, `_workshop_category` | static | contributor_input | 8 | aligned |
| `defense_abs` | alias | approved_alias | declared_identifier | `tower_sim/engines/combat/boss_survivability.py` | `resolve_boss_fight` | runtime | alias->defense_absolute | 8 | alias-map->defense_absolute |
| `defense_absolute` | target_stat | canonical_target_stat | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/loaders/ep_export_loader.py`, … | `_apply_card_effects`, `_compile_relic_stat_inputs`, `default_registry` | static | target_stat | 10 | aligned |
| `defense_pct` | target_stat | canonical_target_stat | declared_identifier | `tower_sim/engines/combat/boss_engine.py`, `tower_sim/engines/combat/boss_survivability.py`, `tower_sim/engines/survivability_pipeline.py` | `_missing_inputs`, `_resolve_survivability_verdict`, `evaluate` | runtime | target_stat | 10 | aligned |
| `defense_percent` | report-only | canonical_contributor_input | consumed_identifier | `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/loaders/ep_export_loader.py` | `_compile_relic_stat_inputs` | static | contributor_input | 8 | aligned |
| `delta_mult` | alias | legacy_or_unresolved | consumed_identifier | `tower_sim/registry/stat_registry.py` | — | static | no | 4 | investigate |
| `duration_s` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/uptime.py` | `_read_profile_from_snapshot`, `build_bot_effects`, `build_gcomp_activation_intervals` | runtime | no | 7 | exclude-runtime |
| `dw_coin_bonus_lvl` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `dwdamage` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | exclude-config |
| `dwdamageamp` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | exclude-config |
| `eals_pct` | alias | legacy_or_unresolved | declared_and_emitted | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/engines/tier_rule_apply.py`, … | `_apply_skip_reduction`, `_build_reaches_stat_input`, `_build_wave_state` | static | no | 4 | investigate |
| `eals_ramp` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/run/problem_spec.py`, `tower_sim/run/spec_loader.py` | `_parse_scenario` | mixed | no | 4 | investigate |
| `edamage` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/edamage_pipeline.py` | `inputs_from_canonical_values` | mixed | no | 4 | investigate |
| `effective_damage` | derived | derived_stat | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | `evaluate` | runtime | no | 7 | classify-derived |
| `effective_damage_per_sec` | derived | derived_stat | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | — | runtime | no | 7 | classify-derived |
| `effective_regen` | derived | derived_stat | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | `evaluate` | runtime | no | 7 | classify-derived |
| `effective_regen_per_sec` | derived | derived_stat | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | — | runtime | no | 7 | classify-derived |
| `ehls_pct` | alias | legacy_or_unresolved | declared_and_emitted | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/engines/tier_rule_apply.py`, … | `_apply_skip_reduction`, `_build_reaches_stat_input`, `_build_wave_state` | static | no | 4 | investigate |
| `ehls_ramp` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/run/problem_spec.py`, `tower_sim/run/spec_loader.py` | `_parse_scenario` | mixed | no | 4 | investigate |
| `electrons_damage_frac` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_survivability.py` | `resolve_boss_fight` | runtime | no | 7 | exclude-runtime |
| `enemy_attack` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/combat_engine.py` | `resolve_combat` | runtime | no | 7 | exclude-runtime |
| `enemy_attack_mult` | alias | runtime_state_field | consumed_identifier | `tower_sim/engines/combat/combat_engine.py` | `resolve_combat` | runtime | no | 7 | exclude-runtime |
| `enemy_attack_wave` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_pipeline.py` | `build_canonical_wave_row`, `resolve_wave_snapshot_for_problem_spec`, `wave_state_from_row` | runtime | no | 7 | exclude-runtime |
| `enemy_damage_table` | unknown | runtime_state_field | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 7 | exclude-runtime |
| `enemy_health_table` | unknown | runtime_state_field | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 7 | exclude-runtime |
| `enemy_health_wave` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_pipeline.py` | `build_canonical_wave_row`, `resolve_wave_snapshot_for_problem_spec`, `wave_state_from_row` | runtime | no | 7 | exclude-runtime |
| `enemy_hp` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/combat_engine.py` | — | runtime | no | 7 | exclude-runtime |
| `enemy_level_skip_reduction` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/tier_rule_apply.py` | `_apply_condition` | mixed | no | 7 | exclude-runtime |
| `enhancement_multiplier` | report-only | runtime_state_field | declared_identifier | `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_engine.py`, … | `_build_row`, `_compile_workshop_stat_inputs`, `_extract_value` | mixed | no | 7 | exclude-runtime |
| `enrage_mult` | alias | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_survivability.py`, `tower_sim/run/problem_spec.py`, `tower_sim/run/spec_loader.py` | `_parse_boss_stats` | runtime | no | 7 | exclude-runtime |
| `ep_edamage_cr5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml`, `tower_sim/loaders/ep_export_loader.py` | — | static | no | 7 | exclude-config |
| `ep_edamage_cs5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 7 | exclude-config |
| `ep_edamage_ct5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 7 | exclude-config |
| `ep_edamage_cu5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 7 | exclude-config |
| `ep_edamage_cv5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 7 | exclude-config |
| `ep_edamage_cw5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 7 | exclude-config |
| `ep_edamage_cx5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 7 | exclude-config |
| `ep_edamage_cz5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 7 | exclude-config |
| `ep_edamage_da5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 7 | exclude-config |
| `ep_edamage_db5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 7 | exclude-config |
| `ep_edamage_dc5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml`, `tower_sim/loaders/ep_export_loader.py` | — | static | no | 7 | exclude-config |
| `ep_edamage_dd5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 7 | exclude-config |
| `ep_edamage_de5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 7 | exclude-config |
| `ep_edamage_df5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 7 | exclude-config |
| `ep_edamage_dg5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 7 | exclude-config |
| `ep_edamage_dh5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 7 | exclude-config |
| `ep_edamage_di5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 7 | exclude-config |
| `ep_edamage_dj5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 7 | exclude-config |
| `ep_edamage_dk5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 7 | exclude-config |
| `ep_edamage_dl5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml`, `tower_sim/loaders/ep_export_loader.py` | — | static | no | 7 | exclude-config |
| `ep_edamage_dm5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml`, `tower_sim/loaders/ep_export_loader.py` | — | static | no | 7 | exclude-config |
| `ep_edamage_dp5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml`, `tower_sim/loaders/ep_export_loader.py` | — | static | no | 7 | exclude-config |
| `ep_edamage_ds5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 7 | exclude-config |
| `ep_edamage_dt5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 7 | exclude-config |
| `ep_edamage_du5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 7 | exclude-config |
| `ep_edamage_dv5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 7 | exclude-config |
| `ep_edamage_dw5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 7 | exclude-config |
| `ep_edamage_dy5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 7 | exclude-config |
| `ep_edamage_eb5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml` | — | static | no | 7 | exclude-config |
| `ep_edamage_ef5` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/formula_library.yaml`, `tower_sim/loaders/ep_export_loader.py` | — | static | no | 7 | exclude-config |
| `ep_lambda_ep_uw_sl_coverage` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | exclude-config |
| `ep_lambda_ep_uw_total_damage` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | exclude-config |
| `ep_lambda_epd_crit_chance` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | exclude-config |
| `ep_lambda_epd_critical` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | exclude-config |
| `ep_lambda_epd_multishot` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | exclude-config |
| `ep_lambda_epd_range` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | exclude-config |
| `ep_lambda_epd_rangedpm` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | exclude-config |
| `ep_lambda_epd_supertower_cooldown` | unknown | runtime_state_field | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | — | static | no | 7 | exclude-runtime |
| `ep_lambda_epd_uwcritical` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | exclude-config |
| `ep_lambda_eph_def_pct` | alias | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | exclude-config |
| `ep_lambda_eph_health` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | exclude-config |
| `ep_lambda_eph_regen` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | exclude-config |
| `ep_lambda_eph_wall_health` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | exclude-config |
| `ep_lambda_eph_wall_regen` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | exclude-config |
| `ep_lambda_stat_uw_cl_final_ch` | derived | derived_stat | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | classify-derived |
| `ep_lambda_stat_uw_cl_final_dmg` | derived | derived_stat | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | classify-derived |
| `ep_lambda_stat_uw_cl_final_qty` | derived | derived_stat | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | classify-derived |
| `ep_lambda_stat_uw_dw_final_cd` | derived | derived_stat | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | classify-derived |
| `ep_lambda_stat_uw_dw_final_dmg` | derived | derived_stat | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | classify-derived |
| `ep_lambda_stat_uw_dw_final_qty` | derived | derived_stat | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | classify-derived |
| `ep_lambda_stat_uw_sl_final_angle` | derived | derived_stat | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | classify-derived |
| `ep_lambda_stat_uw_sl_final_dmg` | derived | derived_stat | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | classify-derived |
| `ep_lambda_stat_uw_sl_final_lr` | derived | derived_stat | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | classify-derived |
| `ep_lambda_stat_uw_sm_final_cd` | derived | derived_stat | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | classify-derived |
| `ep_lambda_stat_uw_sm_final_cf` | derived | derived_stat | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | classify-derived |
| `ep_lambda_stat_uw_sm_final_dmg` | derived | derived_stat | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | classify-derived |
| `ep_lambda_stat_uw_sm_final_qty` | derived | derived_stat | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | classify-derived |
| `epd_crit_chance` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/edamage_formulas.py` | — | mixed | no | 4 | investigate |
| `epd_critical` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/edamage_formulas.py` | — | mixed | no | 4 | investigate |
| `equipped_cards` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/run/api.py` | `_serialize_loadout` | mixed | no | 4 | investigate |
| `expected_coin_multiplier` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/uptime.py` | — | runtime | no | 7 | exclude-runtime |
| `expected_damage_multiplier` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/uptime.py` | — | runtime | no | 7 | exclude-runtime |
| `expected_damage_taken` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/uptime.py` | — | runtime | no | 7 | exclude-runtime |
| `expected_skipped_waves` | runtime | runtime_state_field | consumed_identifier | `tower_sim/audit/status.py` | `_components` | report | no | 7 | exclude-runtime |
| `extra_defense` | unknown | canonical_contributor_input | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_card_effects` | static | contributor_input | 8 | aligned |
| `extra_orb_mastery_lvl` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `extract_max_wave_targets` | runtime | runtime_state_field | consumed_identifier | `tower_sim/loaders/ep_export_loader.py` | — | static | no | 7 | exclude-runtime |
| `final_wave` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/perk_timeline_generator.py` | `generate_timeline` | mixed | no | 7 | exclude-runtime |
| `flame_bot_damage_reduction_multiplier` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | `resolve_runtime_bot_effects` | runtime | no | 7 | exclude-runtime |
| `free_attack_upgrade` | unknown | canonical_contributor_input | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/loaders/ep_export_loader.py`, … | `_compile_relic_stat_inputs`, `default_registry` | static | contributor_input | 8 | aligned |
| `free_attack_upgrade_rate` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `free_defense_upgrade` | unknown | canonical_contributor_input | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/loaders/ep_export_loader.py`, … | `_compile_relic_stat_inputs`, `default_registry` | static | contributor_input | 8 | aligned |
| `from_wave` | runtime | runtime_state_field | declared_identifier | `tower_sim/engines/combat_stat_derivation.py` | `derive_canonical_combat_snapshot` | runtime | no | 7 | exclude-runtime |
| `generator_module` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `gold_bot_cooldown_lvl` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 7 | exclude-runtime |
| `gold_bot_duration_lvl` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 7 | exclude-runtime |
| `golden_tower_cooldown` | unknown | canonical_contributor_input | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | contributor_input | 8 | aligned |
| `golden_tower_duration` | unknown | canonical_contributor_input | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | contributor_input | 8 | aligned |
| `golden_tower_multiplier` | unknown | canonical_contributor_input | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | contributor_input | 8 | aligned |
| `gt_duration_lvl` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 7 | exclude-runtime |
| `has_card` | unknown | table_or_config_symbol | declared_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/engines/econ_current.py`, … | `epd_aspd`, `epd_crit_chance` | static | no | 7 | exclude-config |
| `has_coins_perk` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `has_module` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `has_more_bosses` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/loaders/tournament_bc_selection.py` | `load_league_rules` | static | no | 4 | investigate |
| `health` | target_stat | canonical_target_stat | consumed_identifier | `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/audit/wiring_health_check.py`, `tower_sim/engines/combat/combat_engine.py`, … | `_apply_card_effects`, `_compile_relic_stat_inputs`, `_parse_args` | mixed | target_stat | 10 | aligned |
| `health_regen` | target_stat | canonical_target_stat | consumed_identifier | `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, … | `_apply_card_effects`, `_compile_relic_stat_inputs` | static | target_stat | 10 | aligned |
| `heat_mult` | alias | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_survivability.py` | `_time_to_death` | runtime | no | 7 | exclude-runtime |
| `hpregen` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/registry/naming_contract.py` | — | static | no | 4 | investigate |
| `incoming_damage` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | `evaluate` | runtime | no | 7 | exclude-runtime |
| `inner_land_mines_cooldown` | unknown | canonical_contributor_input | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | contributor_input | 8 | aligned |
| `inner_land_mines_damage` | unknown | canonical_contributor_input | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_slot_main_effect` | static | contributor_input | 8 | aligned |
| `inner_land_mines_quantity` | target_stat | canonical_target_stat | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | target_stat | 10 | aligned |
| `is_boss` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/combat_engine.py` | — | runtime | no | 7 | exclude-runtime |
| `key_modules` | report-only | report_or_audit_field | declared_identifier | `tower_sim/audit/repo_audit.py` | `_check_modules` | report | no | 7 | exclude-report |
| `kill_at_range` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | exclude-config |
| `knockback_mult` | alias | legacy_or_unresolved | emitted_key | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/engines/tier_rule_apply.py`, … | `_apply_condition`, `_build_reaches_stat_input`, `_compile_base_stat_inputs` | static | no | 4 | investigate |
| `knockback_multiplier` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/tier_rule_apply.py` | — | mixed | no | 4 | investigate |
| `lab_enemy_attack_level_skip` | unknown | runtime_state_field | consumed_identifier | `tower_sim/loaders/wiki/labs_eals_ehls.py` | `get_eals_lab_pp` | static | no | 7 | exclude-runtime |
| `lab_enemy_health_level_skip` | unknown | runtime_state_field | consumed_identifier | `tower_sim/loaders/wiki/labs_eals_ehls.py` | `get_ehls_lab_pp` | static | no | 7 | exclude-runtime |
| `lab_health` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/loaders/wiki/labs.py` | — | static | no | 4 | investigate |
| `lab_health_regen` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/loaders/wiki/labs.py` | — | static | no | 4 | investigate |
| `lab_multiplier` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_workshop_stat_inputs` | static | no | 4 | investigate |
| `lab_pct` | alias | legacy_or_unresolved | declared_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_armor_module_multiplier` | static | no | 4 | investigate |
| `lab_recovery_package_chance` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/loaders/wiki/labs.py` | — | static | no | 4 | investigate |
| `lab_speed` | unknown | canonical_contributor_input | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `_compile_relic_stat_inputs`, `default_registry` | static | contributor_input | 8 | aligned |
| `lineage_required_max_wave_gap_count` | runtime | runtime_state_field | consumed_identifier | `tower_sim/audit/wiring_health_check.py` | `run_wiring_health_check` | report | no | 7 | exclude-runtime |
| `load_card_masteries` | unknown | implementation_artifact | consumed_identifier | `tower_sim/loaders/card_masteries.py` | — | static | no | 6 | exclude-implementation |
| `locked_uws` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/run/optimizer_engine.py` | `_parse_uw_rows`, `_stone_actions` | mixed | no | 4 | investigate |
| `make_wave_state` | runtime | runtime_state_field | consumed_identifier | `tower_sim/audit/status.py` | `_components` | report | no | 7 | exclude-runtime |
| `mastery_mult` | alias | legacy_or_unresolved | declared_identifier | `tower_sim/engines/econ_current.py` | `EPC_CARD_COINS` | mixed | no | 4 | investigate |
| `max_recovery_vault_mult` | alias | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | exclude-config |
| `max_recovery_wse_mult` | alias | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | exclude-config |
| `max_rend_mult` | alias | legacy_or_unresolved | consumed_identifier | `tower_sim/loaders/ep_export_loader.py` | — | static | no | 4 | investigate |
| `max_wave` | runtime | runtime_state_field | declared_identifier | `tower_sim/audit/status.py`, `tower_sim/loaders/bc_heat_loader.py`, `tower_sim/loaders/ep_export_loader.py`, … | `_components`, `_parse_problem_spec`, `extract_max_wave_targets` | static | no | 7 | exclude-runtime |
| `max_wave_ids` | runtime | runtime_state_field | declared_identifier | `tower_sim/engines/statbook_builder.py` | `_target_stat_ids` | mixed | no | 7 | exclude-runtime |
| `max_wave_latest` | runtime | runtime_state_field | consumed_identifier | `tower_sim/run/runner.py` | — | mixed | no | 7 | exclude-runtime |
| `max_wave_report` | runtime | runtime_state_field | consumed_identifier | `tower_sim/audit/status.py` | `_components` | report | no | 7 | exclude-runtime |
| `max_wave_runner` | runtime | runtime_state_field | consumed_identifier | `tower_sim/run/runner.py` | — | mixed | no | 7 | exclude-runtime |
| `min_wave` | runtime | runtime_state_field | declared_identifier | `tower_sim/loaders/bc_heat_loader.py` | `value_at` | static | no | 7 | exclude-runtime |
| `missing_at_wave` | runtime | runtime_state_field | emitted_key | `tower_sim/engines/stat_pipeline.py` | `build_canonical_stat_pipeline_for_problem_spec` | mixed | no | 7 | exclude-runtime |
| `missing_cards` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/loaders/account_snapshot_compiler.py` | `_parse_cards` | static | no | 4 | investigate |
| `missing_required_at_wave_stats` | runtime | runtime_state_field | emitted_key | `tower_sim/engines/stat_pipeline.py` | `build_canonical_stat_pipeline_for_problem_spec` | mixed | no | 7 | exclude-runtime |
| `missing_wave` | runtime | runtime_state_field | declared_identifier | `tower_sim/engines/stat_pipeline.py` | `build_canonical_stat_pipeline_for_problem_spec` | mixed | no | 7 | exclude-runtime |
| `missing_wave_state` | runtime | runtime_state_field | emitted_key | `tower_sim/engines/stat_pipeline.py` | `build_canonical_stat_pipeline_for_problem_spec` | mixed | no | 7 | exclude-runtime |
| `module_` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | `_canonical_unmapped_by_source`, `_families_from_stat_input` | runtime | no | 7 | exclude-runtime |
| `module_blocks` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_build_inventory_summary`, `compile_baseline_loadout_stat_inputs` | static | no | 4 | investigate |
| `module_context` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_pipeline.py` | `_compile_survivability_loadout_inputs_resilient`, `_resolve_loadout_inputs` | runtime | no | 7 | exclude-runtime |
| `module_contribution_ledger` | unknown | runtime_state_field | declared_and_emitted | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, … | `_compile_survivability_loadout_inputs_resilient`, `build_canonical_stat_inputs`, `build_canonical_stat_pipeline_for_problem_spec` | mixed | no | 7 | exclude-runtime |
| `module_id` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/run/optimizer_patch.py` | `_validate_module_actions` | mixed | no | 4 | investigate |
| `module_layer_gaps` | unknown | legacy_or_unresolved | emitted_key | `tower_sim/engines/survivability_pipeline.py` | `build_survivability_report` | mixed | no | 4 | investigate |
| `module_main_effect_bands` | unknown | table_or_config_symbol | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 7 | exclude-config |
| `module_main_effect_bands_v1` | unknown | table_or_config_symbol | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 7 | exclude-config |
| `module_main_effect_bases` | unknown | table_or_config_symbol | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 7 | exclude-config |
| `module_main_effect_bases_v1` | unknown | table_or_config_symbol | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 7 | exclude-config |
| `module_name` | report-only | report_or_audit_field | declared_identifier | `tower_sim/audit/repo_audit.py`, `tower_sim/engines/survivability_pipeline.py` | `_check_modules`, `_parse_module_block` | report | no | 7 | exclude-report |
| `module_preset_unmapped` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/registry/naming_contract.py` | `validate_account_snapshot_naming` | static | no | 4 | investigate |
| `module_presets` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/loaders/account_snapshot_compiler.py`, `tower_sim/loaders/account_snapshot_loader.py` | `_load_snapshot`, `_parse_module_presets`, `_parse_modules` | mixed | no | 7 | exclude-runtime |
| `module_primary_effect` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_slot_main_effect`, `_module_unmapped_by_layer` | mixed | no | 7 | exclude-runtime |
| `module_rules` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/modules.py` | — | mixed | no | 4 | investigate |
| `module_substat_unmapped` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, … | `_apply_module_substats`, `_module_unmapped_by_layer`, `validate_account_snapshot_naming` | mixed | no | 7 | exclude-runtime |
| `module_substats` | unknown | table_or_config_symbol | consumed_identifier | `tower_sim/loaders/table_paths.py`, `tower_sim/registry/naming_contract.py` | `_build_named_entity_maps`, `validate_account_snapshot_naming`, `validate_repo_naming_contract` | static | no | 7 | exclude-config |
| `module_substats_v1` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/loaders/table_paths.py` | — | static | no | 7 | exclude-config |
| `module_summary` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/survivability_pipeline.py` | `_build_inventory_summary` | mixed | no | 4 | investigate |
| `module_system_state` | unknown | runtime_state_field | declared_identifier | `tower_sim/loaders/account_snapshot_compiler.py`, `tower_sim/loaders/account_snapshot_loader.py` | `_load_snapshot`, `_parse_module_system_state`, `_parse_modules` | static | no | 7 | exclude-runtime |
| `module_unique_unmapped` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_module_effects`, `_module_unmapped_by_layer` | mixed | no | 7 | exclude-runtime |
| `module_unmapped` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/registry/naming_contract.py` | `validate_account_snapshot_naming` | static | no | 4 | investigate |
| `module_unmapped_by_layer` | unknown | runtime_state_field | declared_and_emitted | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_pipeline.py` | `build_canonical_stat_inputs`, `build_canonical_stat_pipeline_for_problem_spec` | runtime | no | 7 | exclude-runtime |
| `modules_inventory` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/loaders/account_snapshot_compiler.py`, `tower_sim/loaders/account_snapshot_loader.py` | `_load_snapshot`, `_parse_modules` | static | no | 4 | investigate |
| `modules_lib` | report-only | report_or_audit_field | consumed_identifier | `tower_sim/audit/repo_audit.py` | `_check_modules` | report | no | 7 | exclude-report |
| `modules_library` | report-only | report_or_audit_field | consumed_identifier | `tower_sim/audit/repo_audit.py`, `tower_sim/engines/modules.py` | `_check_modules`, `_iter_reference_files` | report | no | 7 | exclude-report |
| `more_bosses` | unknown | canonical_contributor_input | declared_identifier | `tower_sim/engines/tier_rule_apply.py`, `tower_sim/loaders/bc_heat_loader.py`, `tower_sim/loaders/tournament_bc_selection.py` | `_apply_condition`, `enumerate_tournament_bc_sets`, `load_tournament_heat_table` | static | contributor_input | 8 | aligned |
| `multi_rapid_bounce` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | exclude-config |
| `multiplier_cap` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/loaders/account_snapshot_compiler.py`, `tower_sim/loaders/account_snapshot_loader.py` | `_parse_module_system_state` | static | no | 4 | investigate |
| `multiplier_efficiency` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/modules.py` | `apply_multiplier_efficiency` | mixed | no | 4 | investigate |
| `multiplier_level` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/run/optimizer_engine.py` | `_stone_actions` | mixed | no | 4 | investigate |
| `multishot_chance` | target_stat | canonical_target_stat | consumed_identifier | `tower_sim/loaders/ep_export_loader.py` | — | static | target_stat | 10 | aligned |
| `multishot_targets` | target_stat | canonical_target_stat | consumed_identifier | `tower_sim/loaders/ep_export_loader.py` | — | static | target_stat | 10 | aligned |
| `net_damage` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | `evaluate` | runtime | no | 7 | exclude-runtime |
| `net_damage_per_sec` | unknown | derived_stat | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | — | runtime | no | 7 | classify-derived |
| `next_percent` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/run/optimizer_engine.py` | `_apply_unlock` | mixed | no | 4 | investigate |
| `next_uw_plus_unlock_cost` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/run/optimizer_engine.py` | `_stone_actions` | mixed | no | 4 | investigate |
| `next_uw_unlock_cost` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/run/optimizer_engine.py` | `_stone_actions` | mixed | no | 4 | investigate |
| `next_wave` | runtime | runtime_state_field | declared_identifier | `tower_sim/engines/perk_timeline_generator.py` | `generate_timeline` | mixed | no | 7 | exclude-runtime |
| `no_authoritative_bot_mapping_for_stat` | unknown | runtime_state_field | consumed_identifier | `tower_sim/registry/combat_stat_contract.py` | `_excluded_reason`, `stat_lineage_status_lists` | static | no | 7 | exclude-runtime |
| `no_authoritative_card_mapping_for_stat` | unknown | runtime_state_field | consumed_identifier | `tower_sim/registry/combat_stat_contract.py` | `_excluded_reason`, `stat_lineage_status_lists` | static | no | 7 | exclude-runtime |
| `no_authoritative_module_mapping_for_stat` | unknown | runtime_state_field | consumed_identifier | `tower_sim/registry/combat_stat_contract.py` | `_excluded_reason`, `stat_lineage_status_lists` | static | no | 7 | exclude-runtime |
| `no_authoritative_uw_mapping_for_stat` | unknown | runtime_state_field | consumed_identifier | `tower_sim/registry/combat_stat_contract.py` | `_excluded_reason`, `stat_lineage_status_lists` | static | no | 7 | exclude-runtime |
| `op_chain` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | exclude-config |
| `orb_damage_frac` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_survivability.py` | `resolve_boss_fight` | runtime | no | 7 | exclude-runtime |
| `orb_damage_mult` | alias | legacy_or_unresolved | emitted_key | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/engines/tier_rule_apply.py`, … | `_apply_condition`, `_build_reaches_stat_input`, `_compile_base_stat_inputs` | static | no | 4 | investigate |
| `orb_resistance` | unknown | canonical_contributor_input | consumed_identifier | `tower_sim/engines/survivability_pipeline.py`, `tower_sim/engines/tier_rule_apply.py`, `tower_sim/loaders/tournament_bc_enrichment.py` | `_apply_condition`, `_tier_rules_applied` | static | contributor_input | 8 | aligned |
| `orb_speed` | target_stat | canonical_target_stat | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/registry/stat_registry.py` | `_compile_relic_stat_inputs`, `default_registry` | static | target_stat | 10 | aligned |
| `out_of_range` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | `validate_boss_survivability_spec` | runtime | no | 7 | exclude-runtime |
| `package_chance` | target_stat | canonical_target_stat | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | `evaluate` | runtime | target_stat | 10 | aligned |
| `package_heal` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | `evaluate` | runtime | no | 7 | exclude-runtime |
| `package_regen` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | `evaluate` | runtime | no | 7 | exclude-runtime |
| `pc_boss_mult` | alias | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_engine.py`, `tower_sim/engines/combat/boss_survivability.py`, `tower_sim/engines/combat/combat_engine.py` | `evaluate`, `resolve_boss_fight`, `resolve_combat` | runtime | no | 7 | exclude-runtime |
| `per_hit_boss_frac` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_survivability.py` | `resolve_boss_fight` | runtime | no | 7 | exclude-runtime |
| `percent_points` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/loaders/wiki/promote_labs_tables.py`, … | `_compile_wall_survivability_aliases`, `_parse_value`, `_resolve_lab_delta` | static | no | 4 | investigate |
| `percent_string` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/loaders/wiki/cache_audit.py` | `_detect_unit_hint`, `_strip_unit` | static | no | 4 | investigate |
| `perk_multiplier` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/edamage_pipeline.py` | `resolve_damage_perk_multiplier` | mixed | no | 4 | investigate |
| `plasma_cannon_card_frac_v1` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | — | static | no | 7 | exclude-config |
| `plasma_cannon_damage_mult` | alias | legacy_or_unresolved | emitted_key | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/engines/tier_rule_apply.py`, … | `_apply_card_effects`, `_apply_condition`, `_build_reaches_stat_input` | static | no | 4 | investigate |
| `poison_swamp_cooldown` | unknown | canonical_contributor_input | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | contributor_input | 8 | aligned |
| `poison_swamp_damage` | unknown | canonical_contributor_input | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_slot_main_effect` | static | contributor_input | 8 | aligned |
| `poison_swamp_duration` | unknown | canonical_contributor_input | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | contributor_input | 8 | aligned |
| `preset_cards` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/wave_time.py` | `wa_reduction_from_snapshot` | runtime | no | 7 | exclude-runtime |
| `ramp_waves` | runtime | runtime_state_field | declared_identifier | `tower_sim/engines/wave_engine.py`, `tower_sim/run/problem_spec.py`, `tower_sim/run/spec_loader.py` | `_parse_skip_ramp` | runtime | no | 7 | exclude-runtime |
| `range_dpm` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | — | static | no | 7 | exclude-config |
| `range_multiplier` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | — | static | no | 7 | exclude-config |
| `rapid_fire_chance` | target_stat | canonical_target_stat | consumed_identifier | `tower_sim/loaders/ep_export_loader.py` | — | static | target_stat | 10 | aligned |
| `rapid_fire_duration` | unknown | canonical_contributor_input | consumed_identifier | `tower_sim/loaders/ep_export_loader.py` | — | static | contributor_input | 8 | aligned |
| `raw_damage` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_survivability.py` | `_time_to_death` | runtime | no | 7 | exclude-runtime |
| `raw_multiplier` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/stat_input_compiler.py` | `_parse_workshop_enhancement_multipliers` | static | no | 4 | investigate |
| `recovery_package_chance` | unknown | canonical_contributor_input | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/engines/survivability_pipeline.py`, … | `_apply_card_effects` | static | contributor_input | 8 | aligned |
| `recovery_package_max` | unknown | canonical_contributor_input | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | contributor_input | 8 | aligned |
| `reduced_damage` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | `evaluate` | runtime | no | 7 | exclude-runtime |
| `regen` | report-only | report_or_audit_field | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/audit/status.py`, `tower_sim/engines/stat_input_compiler.py`, … | `_components`, `_workshop_value`, `default_registry` | static | no | 7 | exclude-report |
| `regen_per_hit` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_survivability.py` | `_time_to_death` | runtime | no | 7 | exclude-runtime |
| `regen_per_sec` | unknown | derived_stat | declared_identifier | `tower_sim/engines/combat/boss_survivability.py`, `tower_sim/run/problem_spec.py`, `tower_sim/run/spec_loader.py` | `_parse_tower_defense` | runtime | no | 7 | classify-derived |
| `relic_pct` | alias | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | exclude-config |
| `remaining_enemy_hp` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat/combat_engine.py` | `resolve_combat` | runtime | no | 7 | exclude-runtime |
| `rend_mult` | alias | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | — | static | no | 7 | exclude-config |
| `required_max_wave` | runtime | runtime_state_field | consumed_identifier | `tower_sim/audit/stat_lineage_report.py` | `_build_full_table` | report | no | 7 | exclude-runtime |
| `required_max_wave_gap_count` | runtime | runtime_state_field | consumed_identifier | `tower_sim/audit/stat_lineage_report.py`, `tower_sim/audit/wiring_health_check.py` | `_parse_args`, `render_report`, `run_wiring_health_check` | report | no | 7 | exclude-runtime |
| `required_max_wave_gaps` | runtime | runtime_state_field | declared_identifier | `tower_sim/audit/stat_lineage_report.py` | `render_report`, `summarize_manifest` | report | no | 7 | exclude-runtime |
| `required_max_wave_other` | runtime | runtime_state_field | declared_identifier | `tower_sim/registry/combat_stat_contract.py` | `ordered_stat_lineage_sections` | static | no | 7 | exclude-runtime |
| `required_max_wave_other_stat_inputs` | runtime | runtime_state_field | consumed_identifier | `tower_sim/registry/combat_stat_contract.py` | `ordered_stat_lineage_sections` | static | no | 7 | exclude-runtime |
| `required_max_wave_stat_input_ids` | runtime | runtime_state_field | consumed_identifier | `tower_sim/audit/stat_lineage_report.py`, `tower_sim/registry/combat_stat_contract.py` | `load_manifest`, `summarize_manifest` | static | no | 7 | exclude-runtime |
| `resolve_canonical_wave_damage` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | — | runtime | no | 7 | exclude-runtime |
| `resolve_canonical_wave_damage_for_attack_wave` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | — | runtime | no | 7 | exclude-runtime |
| `resolve_card_mastery_value` | unknown | implementation_artifact | consumed_identifier | `tower_sim/engines/edamage_pipeline.py` | — | mixed | no | 6 | exclude-implementation |
| `resolve_damage_perk_multiplier` | unknown | implementation_artifact | consumed_identifier | `tower_sim/engines/edamage_pipeline.py` | — | mixed | no | 6 | exclude-implementation |
| `resolve_wave_state_for_wave` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | — | runtime | no | 7 | exclude-runtime |
| `selected_cards` | unknown | runtime_state_field | declared_and_emitted | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_pipeline.py` | `_compile_survivability_loadout_inputs_resilient`, `_resolve_loadout_inputs` | runtime | no | 7 | exclude-runtime |
| `skip_ramp` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_pipeline.py` | `_build_wave_state`, `resolve_wave_state_for_wave` | runtime | no | 7 | exclude-runtime |
| `skipped_missing_targets` | report-only | runtime_state_field | consumed_identifier | `tower_sim/audit/max_wave_ep_parity.py` | `validate_runner_against_ep_export` | runtime | no | 7 | exclude-runtime |
| `sl_damage` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | exclude-config |
| `sl_lightrange` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | exclude-config |
| `sm_cooldown` | unknown | runtime_state_field | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | exclude-runtime |
| `sm_damage` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | exclude-config |
| `smart_missiles_cooldown` | unknown | canonical_contributor_input | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | contributor_input | 8 | aligned |
| `smart_missiles_damage` | unknown | canonical_contributor_input | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_slot_main_effect` | static | contributor_input | 8 | aligned |
| `smart_missiles_quantity` | target_stat | canonical_target_stat | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | target_stat | 10 | aligned |
| `spotlight_coin_bonus_lvl` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `spotlight_multiplier` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/econ_current.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | — | static | no | 4 | investigate |
| `st_uw_mastery` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | exclude-config |
| `standard_perks_bonus_mult` | alias | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | exclude-config |
| `stone_pct` | alias | legacy_or_unresolved | declared_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_armor_module_multiplier`, `_resolve_assist_efficiencies` | static | no | 4 | investigate |
| `super_crit_chance` | target_stat | canonical_target_stat | declared_identifier | `tower_sim/engines/edamage_pipeline.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, … | `_compile_relic_stat_inputs`, `default_registry`, `inputs_from_canonical_values` | static | target_stat | 10 | aligned |
| `super_crit_mult` | alias | canonical_contributor_input | declared_identifier | `tower_sim/engines/edamage_pipeline.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, … | `_compile_relic_stat_inputs`, `default_registry`, `inputs_from_canonical_values` | static | contributor_input | 8 | aligned |
| `super_crit_multiplier` | target_stat | canonical_target_stat | consumed_identifier | `tower_sim/loaders/ep_export_loader.py` | — | static | target_stat | 10 | aligned |
| `survivability_loadout_unknown_card` | unknown | derived_stat | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | `_compile_survivability_loadout_inputs_resilient` | runtime | no | 7 | classify-derived |
| `survivability_loadout_unsupported_card` | unknown | derived_stat | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | `_compile_survivability_loadout_inputs_resilient` | runtime | no | 7 | classify-derived |
| `target_wall_hp_base` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat_stat_derivation.py` | `_rebase_wall_stats_from_tower` | runtime | no | 7 | exclude-runtime |
| `target_wall_regen_base` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat_stat_derivation.py` | `_rebase_wall_stats_from_tower` | runtime | no | 7 | exclude-runtime |
| `target_wave` | runtime | runtime_state_field | declared_identifier | `tower_sim/engines/perk_timeline_generator.py`, `tower_sim/engines/stat_pipeline.py` | `build_canonical_stat_pipeline_for_problem_spec`, `load_policy` | mixed | no | 7 | exclude-runtime |
| `test_boss_engine` | report-only | runtime_state_field | consumed_identifier | `tower_sim/audit/status.py` | `_components` | report | no | 7 | exclude-runtime |
| `test_boss_survivability` | report-only | derived_stat | consumed_identifier | `tower_sim/audit/status.py` | `_components` | report | no | 7 | classify-derived |
| `test_max_wave_observability` | runtime | runtime_state_field | consumed_identifier | `tower_sim/audit/status.py` | `_components` | report | no | 7 | exclude-runtime |
| `test_max_wave_v1_contract` | runtime | runtime_state_field | consumed_identifier | `tower_sim/audit/status.py` | `_components` | report | no | 7 | exclude-runtime |
| `test_wave_damage_strict` | runtime | runtime_state_field | consumed_identifier | `tower_sim/audit/status.py` | `_components` | report | no | 7 | exclude-runtime |
| `test_wave_engine` | runtime | runtime_state_field | consumed_identifier | `tower_sim/audit/status.py` | `_components` | report | no | 7 | exclude-runtime |
| `thorns_damage_mult` | alias | runtime_state_field | emitted_key | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, … | `_apply_condition`, `_build_reaches_stat_input`, `_compile_base_stat_inputs` | mixed | no | 7 | exclude-runtime |
| `thorns_frac` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_engine.py`, `tower_sim/engines/combat/boss_survivability.py`, `tower_sim/engines/combat/combat_engine.py`, … | `_resolve_survivability_verdict`, `evaluate`, `resolve_boss_fight` | runtime | no | 7 | exclude-runtime |
| `thorns_mult` | alias | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/survivability_pipeline.py` | `_resolve_thorns_inputs` | mixed | no | 4 | investigate |
| `thorns_pct` | alias | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_engine.py` | `_missing_inputs`, `evaluate` | runtime | no | 7 | exclude-runtime |
| `thorns_resistance` | unknown | canonical_contributor_input | consumed_identifier | `tower_sim/engines/survivability_pipeline.py`, `tower_sim/engines/tier_rule_apply.py`, `tower_sim/loaders/tournament_bc_enrichment.py` | `_apply_condition`, `_tier_rules_applied` | static | contributor_input | 8 | aligned |
| `tier_multiplier` | report-only | runtime_state_field | declared_identifier | `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_snapshots.py` | `_extract_value`, `_resolve_stat_input_value`, `_resolved_stat_input_value` | runtime | no | 7 | exclude-runtime |
| `tier_rule_multiplier` | unknown | table_or_config_symbol | declared_identifier | `tower_sim/engines/stat_engine.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/run/api.py`, … | `_merge_stat_input_for_run_stats`, `_parse_stat_input`, `_resolved_stat_input_value` | static | no | 7 | exclude-config |
| `tier_wave_damage` | runtime | runtime_state_field | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 7 | exclude-runtime |
| `tier_wave_damage_legacy` | runtime | runtime_state_field | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 7 | exclude-runtime |
| `time_multiplier_mode` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 7 | exclude-runtime |
| `total_damage` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/combat_engine.py` | `resolve_combat` | runtime | no | 7 | exclude-runtime |
| `tournament_more_bosses_static` | unknown | table_or_config_symbol | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 7 | exclude-config |
| `tournament_wave_damage` | runtime | runtime_state_field | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 7 | exclude-runtime |
| `tournament_wave_damage_legacy` | runtime | runtime_state_field | consumed_identifier | `tower_sim/loaders/table_paths.py` | — | static | no | 7 | exclude-runtime |
| `tower_attack_speed` | unknown | legacy_or_unresolved | declared_and_emitted | `tower_sim/engines/edamage_pipeline.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, … | `_apply_card_effects`, `_build_reaches_stat_input`, `_compile_relic_stat_inputs` | static | no | 4 | investigate |
| `tower_crit_chance` | unknown | legacy_or_unresolved | declared_and_emitted | `tower_sim/engines/edamage_pipeline.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, … | `_apply_card_effects`, `_build_reaches_stat_input`, `_compile_relic_stat_inputs` | static | no | 4 | investigate |
| `tower_crit_factor` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/edamage_pipeline.py` | — | mixed | no | 4 | investigate |
| `tower_crit_multiplier` | unknown | legacy_or_unresolved | emitted_key | `tower_sim/engines/edamage_pipeline.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, … | `_build_reaches_stat_input`, `_compile_relic_stat_inputs`, `build_edamage_stat_inputs` | static | no | 4 | investigate |
| `tower_damage` | unknown | runtime_state_field | declared_and_emitted | `tower_sim/engines/combat/combat_engine.py`, `tower_sim/engines/edamage_pipeline.py`, `tower_sim/engines/stat_input_compiler.py`, … | `_apply_card_effects`, `_apply_slot_main_effect`, `_build_reaches_stat_input` | mixed | no | 7 | exclude-runtime |
| `tower_damage_taken` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat/combat_engine.py` | `resolve_combat` | runtime | no | 7 | exclude-runtime |
| `tower_kills_boss` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat/boss_survivability.py` | `resolve_boss_fight` | runtime | no | 7 | exclude-runtime |
| `tower_regen` | report-only | runtime_state_field | declared_and_emitted | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/engines/combat/boss_engine.py`, … | `_apply_card_effects`, `_build_reaches_stat_input`, `_compile_base_stat_inputs` | mixed | no | 7 | exclude-runtime |
| `tower_regen_per_sec` | unknown | derived_stat | emitted_key | `tower_sim/engines/combat_stat_derivation.py` | `validate_boss_survivability_spec` | runtime | no | 7 | classify-derived |
| `transfer_multiplier` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat_stat_derivation.py` | `_replace_base` | runtime | no | 7 | exclude-runtime |
| `ultimate_crit` | unknown | canonical_contributor_input | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_card_effects` | static | contributor_input | 8 | aligned |
| `ultimate_damage` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `_compile_relic_stat_inputs`, `default_registry` | static | no | 4 | investigate |
| `unknown_card` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | `_canonical_unmapped_by_source` | runtime | no | 7 | exclude-runtime |
| `unsupported_card` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | `_canonical_unmapped_by_source` | runtime | no | 7 | exclude-runtime |
| `upgrade_mult` | alias | legacy_or_unresolved | declared_identifier | `tower_sim/engines/stat_input_compiler.py` | `_free_upgrade_chances` | static | no | 4 | investigate |
| `uw_` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/statbook_builder.py`, … | `_canonical_unmapped_by_source`, `_ordered_target_stat_ids`, `_uw_canonical_aliases` | mixed | no | 7 | exclude-runtime |
| `uw_alias` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_uw_stat_inputs` | static | no | 4 | investigate |
| `uw_alias_pairs` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_behavior` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_unique_effects` | static | no | 4 | investigate |
| `uw_black_hole_consume` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_black_hole_cooldown` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 7 | exclude-runtime |
| `uw_black_hole_duration` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 7 | exclude-runtime |
| `uw_black_hole_size` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_canonical` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/registry/naming_contract.py` | `_build_named_entity_maps` | static | no | 4 | investigate |
| `uw_chain_lightning_chance` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_chain_lightning_damage` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_chain_lightning_quantity` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_chain_lightning_smite` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_chrono_field_chrono_loop` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_chrono_field_cooldown` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 7 | exclude-runtime |
| `uw_chrono_field_duration` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 7 | exclude-runtime |
| `uw_chrono_field_speed_reduction` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_cost_stats` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_costs` | unknown | table_or_config_symbol | declared_identifier | `tower_sim/run/optimizer_engine.py` | `_load_uw_purchase_costs` | mixed | no | 7 | exclude-config |
| `uw_crit_card` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | exclude-config |
| `uw_damage_boost` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | exclude-config |
| `uw_death_wave_cooldown` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 7 | exclude-runtime |
| `uw_death_wave_damage` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 7 | exclude-runtime |
| `uw_death_wave_kill_wall` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 7 | exclude-runtime |
| `uw_death_wave_quantity` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 7 | exclude-runtime |
| `uw_golden_tower_cooldown` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 7 | exclude-runtime |
| `uw_golden_tower_duration` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 7 | exclude-runtime |
| `uw_golden_tower_golden_combo` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_golden_tower_multiplier` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_ids` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/statbook_builder.py` | `_target_stat_ids` | mixed | no | 4 | investigate |
| `uw_inner_land_mines_charged_mines` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_inner_land_mines_cooldown` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 7 | exclude-runtime |
| `uw_inner_land_mines_damage` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_inner_land_mines_quantity` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_level_missing` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py` | `_parse_uw_tracks` | static | no | 4 | investigate |
| `uw_lib` | report-only | report_or_audit_field | consumed_identifier | `tower_sim/audit/repo_audit.py` | `_check_modules` | report | no | 7 | exclude-report |
| `uw_locked` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_uw_stat_inputs` | static | no | 4 | investigate |
| `uw_mapping` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_uw_stat_inputs` | static | no | 4 | investigate |
| `uw_name` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/run/optimizer_engine.py` | `_load_uw_plus_ladders`, `_load_uw_track_ladders`, `_load_uw_track_values` | static | no | 4 | investigate |
| `uw_plus` | unknown | legacy_or_unresolved | emitted_key | `tower_sim/run/optimizer_engine.py` | `_load_uw_purchase_costs`, `_stone_actions` | mixed | no | 4 | investigate |
| `uw_plus_costs` | unknown | table_or_config_symbol | declared_identifier | `tower_sim/run/optimizer_engine.py` | `_load_uw_purchase_costs`, `_stone_actions` | mixed | no | 7 | exclude-config |
| `uw_plus_ladders` | unknown | table_or_config_symbol | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/loaders/table_paths.py`, `tower_sim/run/optimizer_engine.py` | `_load_uw_plus_ladders`, `_load_uw_track_values` | static | no | 7 | exclude-config |
| `uw_plus_ladders_v1` | unknown | table_or_config_symbol | consumed_identifier | `tower_sim/loaders/table_paths.py`, `tower_sim/run/optimizer_engine.py` | `_load_uw_plus_ladders`, `_uw_plus_track_upgrade_action` | static | no | 7 | exclude-config |
| `uw_plus_locked` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/run/optimizer_engine.py` | `_parse_uw_rows`, `_stone_actions` | mixed | no | 4 | investigate |
| `uw_plus_track_upgrade` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/run/optimizer_engine.py` | `_uw_plus_track_upgrade_action` | mixed | no | 4 | investigate |
| `uw_plus_tracks` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/run/optimizer_engine.py` | `_parse_uw_rows`, `_stone_actions` | mixed | no | 4 | investigate |
| `uw_plus_unlock` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/run/optimizer_engine.py` | `_uw_plus_unlock_action` | mixed | no | 4 | investigate |
| `uw_plus_unlock_cost` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/run/optimizer_engine.py` | `_load_uw_purchase_costs` | mixed | no | 4 | investigate |
| `uw_plus_unlock_count` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/run/optimizer_engine.py` | `_load_uw_purchase_costs` | mixed | no | 4 | investigate |
| `uw_plus_unlocked_count` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/run/optimizer_engine.py` | `_parse_uw_rows`, `_stone_actions` | mixed | no | 4 | investigate |
| `uw_poison_swamp_cooldown` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 7 | exclude-runtime |
| `uw_poison_swamp_damage` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_poison_swamp_death_creep` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_poison_swamp_duration` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 7 | exclude-runtime |
| `uw_purchase_costs` | unknown | table_or_config_symbol | declared_identifier | `tower_sim/loaders/table_paths.py`, `tower_sim/run/optimizer_engine.py` | `_load_uw_purchase_costs`, `_stone_actions` | static | no | 7 | exclude-config |
| `uw_purchase_costs_v1` | unknown | table_or_config_symbol | consumed_identifier | `tower_sim/loaders/table_paths.py`, `tower_sim/run/optimizer_engine.py` | `_load_uw_purchase_costs`, `_uw_plus_unlock_action`, `_uw_unlock_action` | static | no | 7 | exclude-config |
| `uw_scalar` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 4 | investigate |
| `uw_section` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py` | `_level_from_provenance`, `_uw_provenance` | static | no | 4 | investigate |
| `uw_smart_missiles_cooldown` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 7 | exclude-runtime |
| `uw_smart_missiles_cover_fire` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_smart_missiles_damage` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_smart_missiles_quantity` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_spotlight_angle` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_spotlight_light_range` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_spotlight_multiplier` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_spotlight_quantity` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `uw_state` | unknown | runtime_state_field | declared_identifier | `tower_sim/run/optimizer_engine.py` | `_stone_actions` | mixed | no | 7 | exclude-runtime |
| `uw_table_level` | unknown | table_or_config_symbol | consumed_identifier | `tower_sim/engines/stat_input_compiler.py` | `_load_uw_track_values` | static | no | 7 | exclude-config |
| `uw_table_value` | unknown | table_or_config_symbol | consumed_identifier | `tower_sim/engines/stat_input_compiler.py` | `_load_uw_track_values` | static | no | 7 | exclude-config |
| `uw_tables_v2_1_2` | unknown | table_or_config_symbol | consumed_identifier | `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 7 | exclude-config |
| `uw_track_costs` | unknown | table_or_config_symbol | declared_identifier | `tower_sim/run/optimizer_engine.py` | `_stone_actions` | mixed | no | 7 | exclude-config |
| `uw_track_ladders` | unknown | table_or_config_symbol | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/loaders/table_paths.py`, `tower_sim/run/optimizer_engine.py` | `_load_uw_track_ladders`, `_load_uw_track_values` | static | no | 7 | exclude-config |
| `uw_track_ladders_v1` | unknown | table_or_config_symbol | consumed_identifier | `tower_sim/loaders/table_paths.py`, `tower_sim/run/optimizer_engine.py` | `_load_uw_track_ladders`, `_uw_track_upgrade_action` | static | no | 7 | exclude-config |
| `uw_track_upgrade` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/run/optimizer_engine.py` | `_uw_track_upgrade_action` | mixed | no | 4 | investigate |
| `uw_tracks` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/registry/naming_contract.py`, `tower_sim/run/optimizer_engine.py` | `_build_named_entity_maps`, `_parse_uw_rows`, `_stone_actions` | static | no | 4 | investigate |
| `uw_unlock` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/run/optimizer_engine.py` | `_uw_unlock_action` | mixed | no | 4 | investigate |
| `uw_unlock_cost` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/run/optimizer_engine.py` | `_load_uw_purchase_costs` | mixed | no | 4 | investigate |
| `uw_unlock_count` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/run/optimizer_engine.py` | `_load_uw_purchase_costs` | mixed | no | 4 | investigate |
| `uw_unlocked_count` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/run/optimizer_engine.py` | `_parse_uw_rows`, `_stone_actions` | mixed | no | 4 | investigate |
| `uw_unmapped` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/registry/naming_contract.py` | `validate_account_snapshot_naming` | static | no | 4 | investigate |
| `validate_boss_survivability_spec` | unknown | derived_stat | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | — | runtime | no | 7 | classify-derived |
| `value_percent_points` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/loaders/wiki/labs_eals_ehls.py`, `tower_sim/loaders/wiki/promote_labs_tables.py` | `_discover_lab_sources`, `_parse_value`, `get_eals_lab_pp` | static | no | 4 | investigate |
| `vault_pct` | alias | table_or_config_symbol | declared_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/engines/econ_current.py` | — | static | no | 7 | exclude-config |
| `wa_card` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/wave_time.py` | `wa_reduction_from_snapshot` | runtime | no | 7 | exclude-runtime |
| `wall_current` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_survivability.py` | `_time_to_death` | runtime | no | 7 | exclude-runtime |
| `wall_fort_overheal_ratio` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | static | no | 7 | exclude-config |
| `wall_fortification` | unknown | canonical_contributor_input | consumed_identifier | `tower_sim/loaders/ep_export_loader.py` | — | static | contributor_input | 8 | aligned |
| `wall_health` | target_stat | canonical_target_stat | consumed_identifier | `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, … | `_apply_unique_effects`, `_compile_relic_stat_inputs` | static | target_stat | 10 | aligned |
| `wall_health_data` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/stat_input_compiler.py` | `compile_workshop_values_at_wave` | static | no | 4 | investigate |
| `wall_health_input` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat_stat_derivation.py` | `_wall_ratio_from_ids` | runtime | no | 7 | exclude-runtime |
| `wall_health_lab` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_wall_survivability_aliases`, `compile_workshop_values_at_wave` | static | no | 4 | investigate |
| `wall_health_ratio` | unknown | runtime_state_field | declared_identifier | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py` | `_compile_wall_survivability_aliases`, `_wall_ratio_from_ids`, `compile_workshop_values_at_wave` | mixed | no | 7 | exclude-runtime |
| `wall_health_ratio_input` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_wall_survivability_aliases` | static | no | 4 | investigate |
| `wall_health_regen_mult_x` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py` | `_apply_unique_effects` | static | no | 4 | investigate |
| `wall_hp` | report-only | approved_alias | declared_and_emitted | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/engines/combat/boss_survivability.py`, … | `_apply_unique_effects`, `_build_reaches_stat_input`, `_compile_base_stat_inputs` | mixed | alias->wall_health | 8 | alias-map->wall_health |
| `wall_lab_` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/loaders/wiki/promote_labs_tables.py` | `_discover_lab_sources` | static | no | 4 | investigate |
| `wall_lab_wall_health` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/loaders/wiki/labs.py` | — | static | no | 4 | investigate |
| `wall_lab_wall_regen` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/loaders/wiki/labs.py` | — | static | no | 4 | investigate |
| `wall_max` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_survivability.py` | `_time_to_death` | runtime | no | 7 | exclude-runtime |
| `wall_ratio` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/survivability_pipeline.py` | `_compile_base_stat_inputs` | mixed | no | 4 | investigate |
| `wall_rebuild` | unknown | canonical_contributor_input | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/registry/stat_registry.py` | `_compile_relic_stat_inputs`, `default_registry` | static | contributor_input | 8 | aligned |
| `wall_regen` | target_stat | canonical_target_stat | declared_and_emitted | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/engines/combat/boss_survivability.py`, … | `_apply_unique_effects`, `_build_reaches_stat_input`, `_compile_base_stat_inputs` | mixed | target_stat | 10 | aligned |
| `wall_regen_blocked` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_wall_survivability_aliases`, `compile_workshop_values_at_wave` | static | no | 4 | investigate |
| `wall_regen_data` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/stat_input_compiler.py` | `compile_workshop_values_at_wave` | static | no | 4 | investigate |
| `wall_regen_entry` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_wall_survivability_aliases`, `compile_workshop_values_at_wave` | static | no | 4 | investigate |
| `wall_regen_input` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat_stat_derivation.py` | `_wall_ratio_from_ids` | runtime | no | 7 | exclude-runtime |
| `wall_regen_lab` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_wall_survivability_aliases`, `compile_workshop_values_at_wave` | static | no | 4 | investigate |
| `wall_regen_per_hit` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat/boss_survivability.py` | `_time_to_death` | runtime | no | 7 | exclude-runtime |
| `wall_regen_ratio` | unknown | runtime_state_field | declared_identifier | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, … | `_compile_base_stat_inputs`, `_compile_wall_survivability_aliases`, `_wall_ratio_from_ids` | mixed | no | 7 | exclude-runtime |
| `wall_regen_ratio_input` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_wall_survivability_aliases` | static | no | 4 | investigate |
| `wall_thorns_entry` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/stat_input_compiler.py` | `_compile_wall_survivability_aliases`, `compile_workshop_values_at_wave` | static | no | 4 | investigate |
| `wall_thorns_lvl` | unknown | table_or_config_symbol | consumed_identifier | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | — | static | no | 7 | exclude-config |
| `wall_thorns_mult` | alias | legacy_or_unresolved | emitted_key | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `_compile_wall_survivability_aliases`, `compile_workshop_values_at_wave`, `default_registry` | static | no | 4 | investigate |
| `wave_accel_mastery_lvl` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 7 | exclude-runtime |
| `wave_actual` | unknown | runtime_state_field | declared_identifier | `tower_sim/loaders/bc_heat_loader.py` | `_load_tournament_heat_values`, `value_at` | static | no | 7 | exclude-runtime |
| `wave_attack_index` | runtime | runtime_state_field | emitted_key | `tower_sim/engines/stat_engine.py`, `tower_sim/engines/stat_snapshots.py`, `tower_sim/registry/combat_stat_contract.py`, … | `_append_wave_state_inputs`, `_build_reaches_stat_input`, `_resolve_at_wave_value` | static | no | 7 | exclude-runtime |
| `wave_damage` | unknown | runtime_state_field | declared_and_emitted | `tower_sim/engines/combat/boss_engine.py`, `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/survivability_pipeline.py` | `_missing_inputs`, `_resolve_survivability_verdict`, `resolve_canonical_wave_damage` | runtime | no | 7 | exclude-runtime |
| `wave_damage_error` | unknown | runtime_state_field | emitted_key | `tower_sim/engines/combat_stat_derivation.py` | `resolve_canonical_wave_damage` | runtime | no | 7 | exclude-runtime |
| `wave_damage_strict` | report-only | runtime_state_field | consumed_identifier | `tower_sim/audit/status.py` | `_components` | report | no | 7 | exclude-runtime |
| `wave_damage_table` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | `resolve_canonical_wave_damage`, `resolve_canonical_wave_damage_for_attack_wave` | runtime | no | 7 | exclude-runtime |
| `wave_damage_tier` | unknown | runtime_state_field | declared_and_emitted | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/run/problem_spec.py`, `tower_sim/run/spec_loader.py` | `_parse_scenario`, `resolve_canonical_wave_damage`, `resolve_canonical_wave_damage_for_attack_wave` | runtime | no | 7 | exclude-runtime |
| `wave_damage_wave` | runtime | runtime_state_field | emitted_key | `tower_sim/engines/combat_stat_derivation.py` | `resolve_canonical_wave_damage` | runtime | no | 7 | exclude-runtime |
| `wave_engine` | report-only | runtime_state_field | consumed_identifier | `tower_sim/audit/status.py`, `tower_sim/engines/stat_engine.py` | `_append_wave_state_inputs`, `_components` | report | no | 7 | exclude-runtime |
| `wave_health_index` | runtime | runtime_state_field | emitted_key | `tower_sim/engines/stat_engine.py`, `tower_sim/engines/stat_snapshots.py`, `tower_sim/registry/combat_stat_contract.py`, … | `_append_wave_state_inputs`, `_build_reaches_stat_input`, `_resolve_at_wave_value` | static | no | 7 | exclude-runtime |
| `wave_inputs` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/stat_pipeline.py` | `build_canonical_stat_pipeline_for_problem_spec` | mixed | no | 7 | exclude-runtime |
| `wave_limit` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py` | `compile_workshop_values_at_wave` | static | no | 7 | exclude-runtime |
| `wave_max` | unknown | runtime_state_field | declared_identifier | `tower_sim/loaders/ep_export_loader.py`, `tower_sim/run/problem_spec.py`, `tower_sim/run/spec_loader.py` | `_parse_scenario`, `extract_max_wave_targets` | static | no | 7 | exclude-runtime |
| `wave_probe` | unknown | runtime_state_field | declared_identifier | `tower_sim/run/problem_spec.py`, `tower_sim/run/spec_loader.py` | `_parse_scenario` | mixed | no | 7 | exclude-runtime |
| `wave_raw` | unknown | runtime_state_field | declared_identifier | `tower_sim/loaders/perk_timeline_loader.py` | `_parse_row` | static | no | 7 | exclude-runtime |
| `wave_row` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/stat_pipeline.py` | `resolve_wave_snapshot_for_problem_spec` | mixed | no | 7 | exclude-runtime |
| `wave_rows` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_pipeline.py` | `resolve_wave_snapshot_for_problem_spec` | mixed | no | 7 | exclude-runtime |
| `wave_skip_mastery_lvl` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 7 | exclude-runtime |
| `wave_snapshot` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_pipeline.py` | `resolve_wave_snapshot_for_problem_spec` | mixed | no | 7 | exclude-runtime |
| `wave_snapshot_error` | unknown | runtime_state_field | emitted_key | `tower_sim/engines/stat_pipeline.py` | `resolve_wave_snapshot_for_problem_spec` | mixed | no | 7 | exclude-runtime |
| `wave_snapshot_inputs` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_pipeline.py` | `resolve_wave_snapshot_for_problem_spec` | mixed | no | 7 | exclude-runtime |
| `wave_state` | unknown | runtime_state_field | declared_and_emitted | `tower_sim/engines/stat_pipeline.py`, `tower_sim/engines/stat_snapshots.py`, `tower_sim/engines/survivability_pipeline.py` | `build_at_wave_snapshot`, `build_canonical_stat_pipeline_for_problem_spec`, `build_survivability_report` | mixed | no | 7 | exclude-runtime |
| `wave_state_from_row` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py` | — | runtime | no | 7 | exclude-runtime |
| `wave_tier` | unknown | runtime_state_field | declared_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/survivability_pipeline.py` | `_resolve_wave_damage`, `resolve_canonical_wave_damage`, `resolve_canonical_wave_damage_for_attack_wave` | runtime | no | 7 | exclude-runtime |
| `wave_time` | runtime | runtime_state_field | declared_identifier | `tower_sim/engines/econ_current.py` | `econ_current` | mixed | no | 7 | exclude-runtime |
| `wave_time_boost` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/econ_current.py` | — | mixed | no | 7 | exclude-runtime |
| `waves_required_lab` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/perk_timeline_generator.py` | `load_policy` | mixed | no | 4 | investigate |
| `waves_skipped` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/free_upgrades.py` | `expected_upgrades_per_wave` | mixed | no | 4 | investigate |
| `waves_skipped_per_wave` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/workshop_progression.py` | `simulate_workshop_progression` | mixed | no | 7 | exclude-runtime |
| `waves_to_end` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/workshop_progression.py` | `simulate_workshop_progression` | mixed | no | 4 | investigate |
| `weight_percent` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/loaders/perk_tables.py` | `load_perk_pool_weights` | static | no | 4 | investigate |
| `wmax_wave_relative` | runtime | runtime_state_field | consumed_identifier | `tower_sim/audit/max_wave_ep_parity.py` | `_resolve_wmax_tolerance` | runtime | no | 7 | exclude-runtime |
| `workshop_attack_speed` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_bounce_shot_chance` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/engines/survivability_pipeline.py`, … | `default_registry` | static | no | 4 | investigate |
| `workshop_bounce_shot_range` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_cash_bonus` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/registry/stat_registry.py` | `_apply_card_effects`, `default_registry` | static | no | 4 | investigate |
| `workshop_cash_per_wave` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 7 | exclude-runtime |
| `workshop_coins_per_kill_bonus` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/engines/survivability_pipeline.py`, … | `_apply_card_effects`, `default_registry` | static | no | 4 | investigate |
| `workshop_coins_per_wave` | runtime | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 7 | exclude-runtime |
| `workshop_critical_chance` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/loaders/ep_export_loader.py`, … | `default_registry` | static | no | 4 | investigate |
| `workshop_critical_factor` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_damage` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/loaders/ep_export_loader.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_damage_per_meter` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/loaders/ep_export_loader.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_defense_absolute` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/loaders/ep_export_loader.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_defense_percent` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_enemy_attack_level_skip` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `_parse_workshop_enhancement_multipliers`, `default_registry` | static | no | 7 | exclude-runtime |
| `workshop_enemy_health_level_skip` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `_parse_workshop_enhancement_multipliers`, `default_registry` | static | no | 7 | exclude-runtime |
| `workshop_enemy_level_skip` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 7 | exclude-runtime |
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
| `workshop_rapid_fire_duration` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/loaders/ep_export_loader.py`, … | `default_registry` | static | no | 7 | exclude-runtime |
| `workshop_recovery_packages` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/loaders/ep_export_loader.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_rend_armor_chance` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_rend_armor_mult` | alias | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/loaders/ep_export_loader.py`, … | `default_registry` | static | no | 4 | investigate |
| `workshop_shockwave` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_shockwave_frequency` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 7 | exclude-runtime |
| `workshop_shockwave_size` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 7 | exclude-runtime |
| `workshop_super_crit_chance` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_super_crit_mult` | alias | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_super_crit_mult_alt` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_thorn_damage` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_thorns` | unknown | legacy_or_unresolved | declared_identifier | `tower_sim/engines/survivability_pipeline.py` | `_resolve_thorns_inputs` | mixed | no | 4 | investigate |
| `workshop_wall_fortification` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_wall_health` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, … | `_compile_wall_survivability_aliases`, `_wall_ratio_from_ids`, `compile_workshop_values_at_wave` | mixed | no | 7 | exclude-runtime |
| `workshop_wall_rebuild` | unknown | legacy_or_unresolved | consumed_identifier | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/registry/stat_registry.py` | `default_registry` | static | no | 4 | investigate |
| `workshop_wall_regen` | unknown | runtime_state_field | consumed_identifier | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `_compile_wall_survivability_aliases`, `_wall_ratio_from_ids`, `compile_workshop_values_at_wave` | mixed | no | 7 | exclude-runtime |

## 3. Canonical stat set
- Count: **23**
`attack_speed`, `bounce_shot_chance`, `chain_lightning_chance`, `chain_lightning_quantity`, `coins_per_kill_bonus`, `critical_chance`, `damage`, `damage_per_meter`, `defense_absolute`, `defense_pct`, `health`, `health_regen`, `inner_land_mines_quantity`, `multishot_chance`, `multishot_targets`, `orb_speed`, `package_chance`, `rapid_fire_chance`, `smart_missiles_quantity`, `super_crit_chance`, `super_crit_multiplier`, `wall_health`, `wall_regen`

## 4. Canonical contributor set
- Count: **38**
`attack`, `cash_bonus`, `chain_lightning_damage`, `chrono_field_cooldown`, `chrono_field_duration`, `chrono_field_speed_reduction`, `crit_chance`, `crit_factor`, `damage_reduction`, `death_wave_cooldown`, `death_wave_damage`, `death_wave_quantity`, `defense`, `defense_percent`, `extra_defense`, `free_attack_upgrade`, `free_defense_upgrade`, `golden_tower_cooldown`, `golden_tower_duration`, `golden_tower_multiplier`, `inner_land_mines_cooldown`, `inner_land_mines_damage`, `lab_speed`, `more_bosses`, `orb_resistance`, `poison_swamp_cooldown`, `poison_swamp_damage`, `poison_swamp_duration`, `rapid_fire_duration`, `recovery_package_chance`, `recovery_package_max`, `smart_missiles_cooldown`, `smart_missiles_damage`, `super_crit_mult`, `thorns_resistance`, `ultimate_crit`, `wall_fortification`, `wall_rebuild`

## 5. Derived stat set
- Count: **26**
`boss_survivability`, `boss_survivability_invalid`, `effective_damage`, `effective_damage_per_sec`, `effective_regen`, `effective_regen_per_sec`, `ep_lambda_stat_uw_cl_final_ch`, `ep_lambda_stat_uw_cl_final_dmg`, `ep_lambda_stat_uw_cl_final_qty`, `ep_lambda_stat_uw_dw_final_cd`, `ep_lambda_stat_uw_dw_final_dmg`, `ep_lambda_stat_uw_dw_final_qty`, `ep_lambda_stat_uw_sl_final_angle`, `ep_lambda_stat_uw_sl_final_dmg`, `ep_lambda_stat_uw_sl_final_lr`, `ep_lambda_stat_uw_sm_final_cd`, `ep_lambda_stat_uw_sm_final_cf`, `ep_lambda_stat_uw_sm_final_dmg`, `ep_lambda_stat_uw_sm_final_qty`, `net_damage_per_sec`, `regen_per_sec`, `survivability_loadout_unknown_card`, `survivability_loadout_unsupported_card`, `test_boss_survivability`, `tower_regen_per_sec`, `validate_boss_survivability_spec`

## 6. Phase-1C candidate set
- Inclusion: `canonical_target_stat`, `canonical_contributor_input`, `derived_stat`.
- Candidate count: **87**
`attack`, `attack_speed`, `boss_survivability`, `boss_survivability_invalid`, `bounce_shot_chance`, `cash_bonus`, `chain_lightning_chance`, `chain_lightning_damage`, `chain_lightning_quantity`, `chrono_field_cooldown`, `chrono_field_duration`, `chrono_field_speed_reduction`, `coins_per_kill_bonus`, `crit_chance`, `crit_factor`, `critical_chance`, `damage`, `damage_per_meter`, `damage_reduction`, `death_wave_cooldown`, `death_wave_damage`, `death_wave_quantity`, `defense`, `defense_absolute`, `defense_pct`, `defense_percent`, `effective_damage`, `effective_damage_per_sec`, `effective_regen`, `effective_regen_per_sec`, `ep_lambda_stat_uw_cl_final_ch`, `ep_lambda_stat_uw_cl_final_dmg`, `ep_lambda_stat_uw_cl_final_qty`, `ep_lambda_stat_uw_dw_final_cd`, `ep_lambda_stat_uw_dw_final_dmg`, `ep_lambda_stat_uw_dw_final_qty`, `ep_lambda_stat_uw_sl_final_angle`, `ep_lambda_stat_uw_sl_final_dmg`, `ep_lambda_stat_uw_sl_final_lr`, `ep_lambda_stat_uw_sm_final_cd`, `ep_lambda_stat_uw_sm_final_cf`, `ep_lambda_stat_uw_sm_final_dmg`, `ep_lambda_stat_uw_sm_final_qty`, `extra_defense`, `free_attack_upgrade`, `free_defense_upgrade`, `golden_tower_cooldown`, `golden_tower_duration`, `golden_tower_multiplier`, `health`, `health_regen`, `inner_land_mines_cooldown`, `inner_land_mines_damage`, `inner_land_mines_quantity`, `lab_speed`, `more_bosses`, `multishot_chance`, `multishot_targets`, `net_damage_per_sec`, `orb_resistance`, `orb_speed`, `package_chance`, `poison_swamp_cooldown`, `poison_swamp_damage`, `poison_swamp_duration`, `rapid_fire_chance`, `rapid_fire_duration`, `recovery_package_chance`, `recovery_package_max`, `regen_per_sec`, `smart_missiles_cooldown`, `smart_missiles_damage`, `smart_missiles_quantity`, `super_crit_chance`, `super_crit_mult`, `super_crit_multiplier`, `survivability_loadout_unknown_card`, `survivability_loadout_unsupported_card`, `test_boss_survivability`, `thorns_resistance`, `tower_regen_per_sec`, `ultimate_crit`, `validate_boss_survivability_spec`, `wall_fortification`, `wall_health`, `wall_rebuild`, `wall_regen`

## 7. Remaining unresolved identifiers
- Count: **202**
| repo_name | why classification failed |
|---|---|
| `absolute_chance_subtract` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `assist_mult` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `assist_multiplier` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `bh_coin_bonus_lvl` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `bonus_multiplier` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `bot_amplify_range` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `bot_attribute_unmapped` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `bot_attributes` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `bot_flame_range` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `bot_golden_range` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `bot_level_invalid` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `bot_level_missing` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `bot_range` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `bot_range_bonus_m` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `bot_thunder_linger` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `bot_thunder_range` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `bot_tracks` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `bot_unmapped` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `bot_values` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `card_canonical` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `card_id` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `card_mastery` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `card_unmapped` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `cards_common` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `cards_epic` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `cards_inventory` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `coin_actions_not_implemented` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `coins_bonus` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `coins_card` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `coins_mastery_lvl` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `coins_per_kill_bonus_lvl` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `coins_per_kill_mult` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `compute_edamage_outputs` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `crit_multiplier` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `death_ray_damage_mult` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `delta_mult` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `dw_coin_bonus_lvl` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `eals_pct` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `eals_ramp` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `edamage` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `ehls_pct` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `ehls_ramp` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `epd_crit_chance` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `epd_critical` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `equipped_cards` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `extra_orb_mastery_lvl` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `free_attack_upgrade_rate` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `generator_module` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `has_coins_perk` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `has_module` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `has_more_bosses` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `hpregen` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `knockback_mult` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `knockback_multiplier` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `lab_health` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `lab_health_regen` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `lab_multiplier` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `lab_pct` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `lab_recovery_package_chance` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `locked_uws` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `mastery_mult` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `max_rend_mult` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `missing_cards` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `module_blocks` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `module_id` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `module_layer_gaps` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `module_preset_unmapped` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `module_rules` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `module_summary` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `module_unmapped` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `modules_inventory` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `multiplier_cap` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `multiplier_efficiency` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `multiplier_level` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `next_percent` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `next_uw_plus_unlock_cost` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `next_uw_unlock_cost` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `orb_damage_mult` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `percent_points` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `percent_string` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `perk_multiplier` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `plasma_cannon_damage_mult` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `raw_multiplier` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `spotlight_coin_bonus_lvl` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `spotlight_multiplier` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `stone_pct` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `thorns_mult` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `tower_attack_speed` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `tower_crit_chance` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `tower_crit_factor` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `tower_crit_multiplier` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `ultimate_damage` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `upgrade_mult` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_alias` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_alias_pairs` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_behavior` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_black_hole_consume` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_black_hole_size` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_canonical` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_chain_lightning_chance` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_chain_lightning_damage` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_chain_lightning_quantity` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_chain_lightning_smite` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_chrono_field_chrono_loop` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_chrono_field_speed_reduction` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_cost_stats` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_golden_tower_golden_combo` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_golden_tower_multiplier` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_ids` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_inner_land_mines_charged_mines` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_inner_land_mines_damage` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_inner_land_mines_quantity` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_level_missing` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_locked` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_mapping` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_name` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_plus` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_plus_locked` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_plus_track_upgrade` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_plus_tracks` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_plus_unlock` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_plus_unlock_cost` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_plus_unlock_count` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_plus_unlocked_count` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_poison_swamp_damage` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_poison_swamp_death_creep` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_scalar` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_section` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_smart_missiles_cover_fire` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_smart_missiles_damage` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_smart_missiles_quantity` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_spotlight_angle` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_spotlight_light_range` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_spotlight_multiplier` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_spotlight_quantity` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_track_upgrade` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_tracks` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_unlock` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_unlock_cost` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_unlock_count` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_unlocked_count` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `uw_unmapped` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `value_percent_points` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `wall_health_data` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `wall_health_lab` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `wall_health_ratio_input` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `wall_health_regen_mult_x` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `wall_lab_` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `wall_lab_wall_health` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `wall_lab_wall_regen` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `wall_ratio` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `wall_regen_blocked` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `wall_regen_data` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `wall_regen_entry` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `wall_regen_lab` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `wall_regen_ratio_input` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `wall_thorns_entry` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `wall_thorns_mult` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `waves_required_lab` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `waves_skipped` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `waves_to_end` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `weight_percent` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `workshop_attack_speed` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `workshop_bounce_shot_chance` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `workshop_bounce_shot_range` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `workshop_cash_bonus` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `workshop_coins_per_kill_bonus` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `workshop_critical_chance` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `workshop_critical_factor` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `workshop_damage` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `workshop_damage_per_meter` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `workshop_defense_absolute` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `workshop_defense_percent` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `workshop_free_attack_upgrade` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `workshop_free_defense_upgrade` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `workshop_health` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `workshop_health_regen` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `workshop_knockback_chance` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `workshop_land_mine` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |
| `workshop_land_mine_chance` | Ambiguous semantic ownership; not in ledger target/contributor sets; lacks deterministic runtime/report/table markers. |

- Additional unresolved identifiers not listed inline: 22.

## 8. Risk assessment
| rank | surface | normalization-risk identifiers |
|---:|---|---:|
| 1 | `tower_sim/engines/stat_input_compiler.py` | 137 |
| 2 | `tower_sim/registry/stat_registry.py` | 63 |
| 3 | `tower_sim/engines/survivability_pipeline.py` | 59 |
| 4 | `tower_sim/engines/stat_pipeline.py` | 28 |
| 5 | `tower_sim/run/optimizer_engine.py` | 22 |
| 6 | `tower_sim/loaders/ep_export_loader.py` | 18 |
| 7 | `tower_sim/engines/econ_current.py` | 17 |
| 8 | `tower_sim/engines/tier_rule_apply.py` | 11 |
| 9 | `tower_sim/engines/edamage_pipeline.py` | 11 |
| 10 | `tower_sim/registry/naming_contract.py` | 10 |
| 11 | `tower_sim/loaders/wiki/labs.py` | 5 |
| 12 | `tower_sim/engines/combat/boss_survivability.py` | 4 |

- Stop/continue recommendation: **Continue with caution**. Phase 1C can proceed on the reduced candidate set only; unresolved identifiers require another conservative normalization pass before full ownership assertions.
