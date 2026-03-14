# Phase 1C.A Staged Ownership Audit (Clean Subset Only)

## 1. Files inspected
- `audit/phase_1b_normalized_namespace.md`
- `audit/reference/tower_sim_3_handover/towersim_static_ledger_latest.csv`
- `audit/reference/tower_sim_3_handover/towersim_static_ledger_naming_contract_v1_10.md`
- `audit/reference/tower_sim_3_handover/towersim_v1_handover_pack.md`
- `legacy/governance_handoff/CODEX_HANDOFF_V1_FULL.md`
- `legacy/governance_handoff/STATUS_V1.yaml`
- `CONTRACT.md`
- Repo surfaces scanned for ownership evidence: `tower_sim/**`, `tables/meta/registry/**`.

## 2. Candidate gating summary
- Total normalized candidates reviewed: **87**
- Clean candidates admitted: **70**
- Gated candidates excluded: **17**

## 3. Gated candidates table
| repo_name | normalized_bucket | reason_excluded | blocker_type | recommended_next_step |
|---|---|---|---|---|
| `attack` | canonical_contributor_input | mixed static/runtime/report stage presence | mixed_stage | split static owner from runtime/report layers before ownership assertion |
| `boss_survivability` | derived_stat | runtime-state semantic in identifier | runtime_leakage | keep gated until runtime/static separation is explicit |
| `boss_survivability_invalid` | derived_stat | runtime-state semantic in identifier | runtime_leakage | keep gated until runtime/static separation is explicit |
| `damage` | canonical_target_stat | mixed static/runtime/report stage presence | mixed_stage | split static owner from runtime/report layers before ownership assertion |
| `death_wave_cooldown` | canonical_contributor_input | runtime-state semantic in identifier | runtime_leakage | keep gated until runtime/static separation is explicit |
| `death_wave_damage` | canonical_contributor_input | runtime-state semantic in identifier | runtime_leakage | keep gated until runtime/static separation is explicit |
| `death_wave_quantity` | canonical_contributor_input | runtime-state semantic in identifier | runtime_leakage | keep gated until runtime/static separation is explicit |
| `defense_pct` | canonical_target_stat | known ambiguous semantic overloaded identifier | ambiguous_semantics | decompose meaning and reclassify before ownership |
| `defense_percent` | canonical_contributor_input | known ambiguous semantic overloaded identifier | ambiguous_semantics | decompose meaning and reclassify before ownership |
| `health` | canonical_target_stat | mixed static/runtime/report stage presence | mixed_stage | split static owner from runtime/report layers before ownership assertion |
| `package_chance` | canonical_target_stat | known ambiguous semantic overloaded identifier | ambiguous_semantics | decompose meaning and reclassify before ownership |
| `rapid_fire_duration` | canonical_contributor_input | known ambiguous semantic overloaded identifier | ambiguous_semantics | decompose meaning and reclassify before ownership |
| `survivability_loadout_unknown_card` | derived_stat | test/report diagnostic leakage | report_only_leakage | exclude from canonical ownership set |
| `survivability_loadout_unsupported_card` | derived_stat | test/report diagnostic leakage | report_only_leakage | exclude from canonical ownership set |
| `test_boss_survivability` | derived_stat | runtime-state semantic in identifier | runtime_leakage | keep gated until runtime/static separation is explicit |
| `validate_boss_survivability_spec` | derived_stat | runtime-state semantic in identifier | runtime_leakage | keep gated until runtime/static separation is explicit |
| `wall_regen` | canonical_target_stat | mixed static/runtime/report stage presence | mixed_stage | split static owner from runtime/report layers before ownership assertion |

## 4. Clean candidate ownership table
| repo_name | normalized_bucket | canonical_source_surface | canonical_owner_function | upstream_inputs | downstream_consumers | emitted_outputs | confidence (0-10) | ownership_status |
|---|---|---|---|---|---|---|---:|---|
| `attack_speed` | canonical_target_stat | `tower_sim/engines/stat_input_compiler.py` | `_apply_card_effects` | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/loaders/ep_export_loader.py` | `tower_sim/engines/edamage_pipeline.py`, `tower_sim/engines/survivability_pipeline.py` | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py` | 7 | multiple_owners_conflict |
| `bounce_shot_chance` | canonical_target_stat | `tower_sim/loaders/ep_export_loader.py` | — | `tower_sim/loaders/ep_export_loader.py` | — | — | 9 | clear_owner |
| `cash_bonus` | canonical_contributor_input | `tower_sim/engines/stat_input_compiler.py` | `_compile_relic_stat_inputs` | `tower_sim/registry/stat_registry.py` | `tower_sim/engines/survivability_pipeline.py` | `tower_sim/engines/stat_input_compiler.py` | 7 | multiple_owners_conflict |
| `chain_lightning_chance` | canonical_target_stat | `tower_sim/engines/stat_input_compiler.py` | — | — | `tower_sim/engines/survivability_pipeline.py` | `tower_sim/engines/stat_input_compiler.py` | 7 | multiple_owners_conflict |
| `chain_lightning_damage` | canonical_contributor_input | `tower_sim/engines/stat_input_compiler.py` | `_apply_slot_main_effect` | — | `tower_sim/engines/survivability_pipeline.py` | `tower_sim/engines/stat_input_compiler.py` | 7 | multiple_owners_conflict |
| `chain_lightning_quantity` | canonical_target_stat | `tower_sim/engines/stat_input_compiler.py` | — | — | `tower_sim/engines/survivability_pipeline.py` | `tower_sim/engines/stat_input_compiler.py` | 7 | multiple_owners_conflict |
| `chrono_field_cooldown` | canonical_contributor_input | `tower_sim/engines/stat_input_compiler.py` | — | — | `tower_sim/engines/survivability_pipeline.py`, `tower_sim/evaluators/max_wave.py` | `tower_sim/engines/stat_input_compiler.py` | 7 | multiple_owners_conflict |
| `chrono_field_duration` | canonical_contributor_input | `tower_sim/engines/stat_input_compiler.py` | — | — | `tower_sim/engines/survivability_pipeline.py`, `tower_sim/evaluators/max_wave.py` | `tower_sim/engines/stat_input_compiler.py` | 7 | multiple_owners_conflict |
| `chrono_field_speed_reduction` | canonical_contributor_input | `tower_sim/engines/stat_input_compiler.py` | — | — | `tower_sim/engines/survivability_pipeline.py` | `tower_sim/engines/stat_input_compiler.py` | 7 | multiple_owners_conflict |
| `coins_per_kill_bonus` | canonical_target_stat | `tower_sim/loaders/ep_export_loader.py` | — | `tower_sim/loaders/ep_export_loader.py` | — | — | 9 | clear_owner |
| `crit_chance` | canonical_contributor_input | `tower_sim/engines/stat_input_compiler.py` | `_compile_relic_stat_inputs` | `tower_sim/loaders/ep_export_loader.py` | `tower_sim/engines/edamage_pipeline.py` | `tower_sim/engines/stat_input_compiler.py` | 9 | clear_owner |
| `crit_factor` | canonical_contributor_input | `tower_sim/engines/stat_input_compiler.py` | `_compile_relic_stat_inputs` | `tower_sim/loaders/ep_export_loader.py` | `tower_sim/engines/edamage_pipeline.py` | `tower_sim/engines/stat_input_compiler.py` | 9 | clear_owner |
| `critical_chance` | canonical_target_stat | `tower_sim/engines/stat_input_compiler.py` | `_apply_card_effects` | — | `tower_sim/engines/survivability_pipeline.py` | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py` | 7 | multiple_owners_conflict |
| `damage_per_meter` | canonical_target_stat | `tower_sim/engines/stat_input_compiler.py` | `_compile_relic_stat_inputs` | `tower_sim/loaders/ep_export_loader.py`, `tower_sim/registry/stat_registry.py` | `tower_sim/engines/survivability_pipeline.py` | `tower_sim/engines/stat_input_compiler.py` | 7 | multiple_owners_conflict |
| `damage_reduction` | canonical_contributor_input | `tower_sim/engines/combat_stat_derivation.py` | `_read_profile_from_snapshot` | — | `tower_sim/evaluators/max_wave.py` | `tower_sim/engines/combat/boss_engine.py`, `tower_sim/engines/combat_stat_derivation.py` | 9 | clear_owner |
| `defense` | canonical_contributor_input | `tower_sim/engines/stat_input_compiler.py` | `_free_upgrade_chances` | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/loaders/wiki/abbreviations.py`, `tower_sim/loaders/wiki/enemy_level_skip.py`, `tower_sim/loaders/wiki/labs_formula.py` | `tower_sim/run/spec_loader.py` | `tower_sim/engines/stat_input_compiler.py` | 9 | clear_owner |
| `defense_absolute` | canonical_target_stat | `tower_sim/engines/stat_input_compiler.py` | `_apply_card_effects` | `tower_sim/loaders/ep_export_loader.py`, `tower_sim/registry/stat_registry.py` | `tower_sim/engines/survivability_pipeline.py` | `tower_sim/engines/stat_input_compiler.py` | 7 | multiple_owners_conflict |
| `effective_damage` | derived_stat | `tower_sim/engines/combat/boss_engine.py` | `evaluate` | — | — | `tower_sim/engines/combat/boss_engine.py` | 8 | clear_owner |
| `effective_damage_per_sec` | derived_stat | `tower_sim/engines/combat/boss_engine.py` | — | — | — | `tower_sim/engines/combat/boss_engine.py` | 8 | clear_owner |
| `effective_regen` | derived_stat | `tower_sim/engines/combat/boss_engine.py` | `evaluate` | — | — | `tower_sim/engines/combat/boss_engine.py` | 8 | clear_owner |
| `effective_regen_per_sec` | derived_stat | `tower_sim/engines/combat/boss_engine.py` | — | — | — | `tower_sim/engines/combat/boss_engine.py` | 8 | clear_owner |
| `ep_lambda_stat_uw_cl_final_ch` | derived_stat | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | — | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | — | 8 | clear_owner |
| `ep_lambda_stat_uw_cl_final_dmg` | derived_stat | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | — | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | — | 8 | clear_owner |
| `ep_lambda_stat_uw_cl_final_qty` | derived_stat | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | — | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | — | 8 | clear_owner |
| `ep_lambda_stat_uw_dw_final_cd` | derived_stat | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | — | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | — | 8 | clear_owner |
| `ep_lambda_stat_uw_dw_final_dmg` | derived_stat | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | — | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | — | 8 | clear_owner |
| `ep_lambda_stat_uw_dw_final_qty` | derived_stat | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | — | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | — | 8 | clear_owner |
| `ep_lambda_stat_uw_sl_final_angle` | derived_stat | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | — | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | — | 8 | clear_owner |
| `ep_lambda_stat_uw_sl_final_dmg` | derived_stat | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | — | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | — | 8 | clear_owner |
| `ep_lambda_stat_uw_sl_final_lr` | derived_stat | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | — | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | — | 8 | clear_owner |
| `ep_lambda_stat_uw_sm_final_cd` | derived_stat | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | — | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | — | 8 | clear_owner |
| `ep_lambda_stat_uw_sm_final_cf` | derived_stat | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | — | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | — | 8 | clear_owner |
| `ep_lambda_stat_uw_sm_final_dmg` | derived_stat | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | — | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | — | 8 | clear_owner |
| `ep_lambda_stat_uw_sm_final_qty` | derived_stat | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | — | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | — | 8 | clear_owner |
| `extra_defense` | canonical_contributor_input | `tower_sim/engines/stat_input_compiler.py` | `_apply_card_effects` | — | `tower_sim/engines/survivability_pipeline.py` | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py` | 7 | multiple_owners_conflict |
| `free_attack_upgrade` | canonical_contributor_input | `tower_sim/engines/stat_input_compiler.py` | `_compile_relic_stat_inputs` | `tower_sim/loaders/ep_export_loader.py`, `tower_sim/registry/stat_registry.py` | `tower_sim/engines/survivability_pipeline.py` | `tower_sim/engines/stat_input_compiler.py` | 7 | multiple_owners_conflict |
| `free_defense_upgrade` | canonical_contributor_input | `tower_sim/engines/stat_input_compiler.py` | `_compile_relic_stat_inputs` | `tower_sim/loaders/ep_export_loader.py`, `tower_sim/registry/stat_registry.py` | `tower_sim/engines/survivability_pipeline.py` | `tower_sim/engines/stat_input_compiler.py` | 7 | multiple_owners_conflict |
| `golden_tower_cooldown` | canonical_contributor_input | `tower_sim/engines/stat_input_compiler.py` | — | — | `tower_sim/engines/survivability_pipeline.py`, `tower_sim/evaluators/max_wave.py` | `tower_sim/engines/stat_input_compiler.py` | 7 | multiple_owners_conflict |
| `golden_tower_duration` | canonical_contributor_input | `tower_sim/engines/stat_input_compiler.py` | — | — | `tower_sim/engines/survivability_pipeline.py`, `tower_sim/evaluators/max_wave.py` | `tower_sim/engines/stat_input_compiler.py` | 7 | multiple_owners_conflict |
| `golden_tower_multiplier` | canonical_contributor_input | `tower_sim/engines/stat_input_compiler.py` | — | — | `tower_sim/engines/survivability_pipeline.py`, `tower_sim/evaluators/max_wave.py` | `tower_sim/engines/stat_input_compiler.py` | 7 | multiple_owners_conflict |
| `health_regen` | canonical_target_stat | `tower_sim/engines/stat_input_compiler.py` | `_apply_card_effects` | `tower_sim/loaders/ep_export_loader.py` | `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/engines/survivability_pipeline.py` | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py` | 7 | multiple_owners_conflict |
| `inner_land_mines_cooldown` | canonical_contributor_input | `tower_sim/engines/stat_input_compiler.py` | — | — | `tower_sim/engines/survivability_pipeline.py`, `tower_sim/evaluators/max_wave.py` | `tower_sim/engines/stat_input_compiler.py` | 7 | multiple_owners_conflict |
| `inner_land_mines_damage` | canonical_contributor_input | `tower_sim/engines/stat_input_compiler.py` | `_apply_slot_main_effect` | — | `tower_sim/engines/survivability_pipeline.py` | `tower_sim/engines/stat_input_compiler.py` | 7 | multiple_owners_conflict |
| `inner_land_mines_quantity` | canonical_target_stat | `tower_sim/engines/stat_input_compiler.py` | — | — | `tower_sim/engines/survivability_pipeline.py` | `tower_sim/engines/stat_input_compiler.py` | 7 | multiple_owners_conflict |
| `lab_speed` | canonical_contributor_input | `tower_sim/engines/stat_input_compiler.py` | `_compile_relic_stat_inputs` | `tower_sim/registry/stat_registry.py` | — | `tower_sim/engines/stat_input_compiler.py` | 9 | clear_owner |
| `more_bosses` | canonical_contributor_input | `tower_sim/engines/tier_rule_apply.py` | `_apply_condition` | `tower_sim/loaders/bc_heat_loader.py`, `tower_sim/loaders/tournament_bc_selection.py` | — | — | 9 | clear_owner |
| `multishot_chance` | canonical_target_stat | `tower_sim/loaders/ep_export_loader.py` | — | `tower_sim/loaders/ep_export_loader.py` | — | — | 9 | clear_owner |
| `multishot_targets` | canonical_target_stat | `tower_sim/loaders/ep_export_loader.py` | — | `tower_sim/loaders/ep_export_loader.py` | — | — | 9 | clear_owner |
| `net_damage_per_sec` | derived_stat | `tower_sim/engines/combat/boss_engine.py` | — | — | — | `tower_sim/engines/combat/boss_engine.py` | 8 | clear_owner |
| `orb_resistance` | canonical_contributor_input | `tower_sim/engines/survivability_pipeline.py` | `_apply_condition` | `tower_sim/loaders/tournament_bc_enrichment.py` | — | — | 9 | clear_owner |
| `orb_speed` | canonical_target_stat | `tower_sim/engines/stat_input_compiler.py` | `_compile_relic_stat_inputs` | `tower_sim/registry/stat_registry.py` | `tower_sim/engines/survivability_pipeline.py` | `tower_sim/engines/stat_input_compiler.py` | 7 | multiple_owners_conflict |
| `poison_swamp_cooldown` | canonical_contributor_input | `tower_sim/engines/stat_input_compiler.py` | — | — | `tower_sim/engines/survivability_pipeline.py` | `tower_sim/engines/stat_input_compiler.py` | 7 | multiple_owners_conflict |
| `poison_swamp_damage` | canonical_contributor_input | `tower_sim/engines/stat_input_compiler.py` | `_apply_slot_main_effect` | — | `tower_sim/engines/survivability_pipeline.py` | `tower_sim/engines/stat_input_compiler.py` | 7 | multiple_owners_conflict |
| `poison_swamp_duration` | canonical_contributor_input | `tower_sim/engines/stat_input_compiler.py` | — | — | `tower_sim/engines/survivability_pipeline.py` | `tower_sim/engines/stat_input_compiler.py` | 7 | multiple_owners_conflict |
| `rapid_fire_chance` | canonical_target_stat | `tower_sim/loaders/ep_export_loader.py` | — | `tower_sim/loaders/ep_export_loader.py` | — | — | 9 | clear_owner |
| `recovery_package_chance` | canonical_contributor_input | `tower_sim/engines/stat_input_compiler.py` | `_apply_card_effects` | `tower_sim/loaders/ep_export_loader.py` | `tower_sim/engines/survivability_pipeline.py` | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py` | 7 | multiple_owners_conflict |
| `recovery_package_max` | canonical_contributor_input | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | — | — | 9 | clear_owner |
| `regen_per_sec` | derived_stat | `tower_sim/engines/combat_stat_derivation.py` | `_parse_tower_defense` | — | `tower_sim/engines/survivability_pipeline.py`, `tower_sim/evaluators/max_wave.py`, `tower_sim/run/problem_spec.py`, `tower_sim/run/spec_loader.py` | `tower_sim/engines/combat_stat_derivation.py` | 8 | clear_owner |
| `smart_missiles_cooldown` | canonical_contributor_input | `tower_sim/engines/stat_input_compiler.py` | — | — | `tower_sim/engines/survivability_pipeline.py`, `tower_sim/evaluators/max_wave.py` | `tower_sim/engines/stat_input_compiler.py` | 7 | multiple_owners_conflict |
| `smart_missiles_damage` | canonical_contributor_input | `tower_sim/engines/stat_input_compiler.py` | `_apply_slot_main_effect` | — | `tower_sim/engines/survivability_pipeline.py` | `tower_sim/engines/stat_input_compiler.py` | 7 | multiple_owners_conflict |
| `smart_missiles_quantity` | canonical_target_stat | `tower_sim/engines/stat_input_compiler.py` | — | — | `tower_sim/engines/survivability_pipeline.py` | `tower_sim/engines/stat_input_compiler.py` | 7 | multiple_owners_conflict |
| `super_crit_chance` | canonical_target_stat | `tower_sim/engines/stat_input_compiler.py` | `_compile_relic_stat_inputs` | `tower_sim/loaders/ep_export_loader.py`, `tower_sim/registry/stat_registry.py` | `tower_sim/engines/edamage_pipeline.py`, `tower_sim/engines/survivability_pipeline.py` | `tower_sim/engines/stat_input_compiler.py` | 7 | multiple_owners_conflict |
| `super_crit_mult` | canonical_contributor_input | `tower_sim/engines/stat_input_compiler.py` | `_compile_relic_stat_inputs` | `tower_sim/registry/stat_registry.py` | `tower_sim/engines/edamage_pipeline.py`, `tower_sim/engines/survivability_pipeline.py` | `tower_sim/engines/stat_input_compiler.py` | 7 | multiple_owners_conflict |
| `super_crit_multiplier` | canonical_target_stat | `tower_sim/loaders/ep_export_loader.py` | — | `tower_sim/loaders/ep_export_loader.py` | — | — | 9 | clear_owner |
| `thorns_resistance` | canonical_contributor_input | `tower_sim/engines/survivability_pipeline.py` | `_apply_condition` | `tower_sim/loaders/tournament_bc_enrichment.py` | — | — | 9 | clear_owner |
| `tower_regen_per_sec` | derived_stat | `tower_sim/engines/combat_stat_derivation.py` | `validate_boss_survivability_spec` | — | — | `tower_sim/engines/combat_stat_derivation.py` | 8 | clear_owner |
| `ultimate_crit` | canonical_contributor_input | `tower_sim/engines/stat_input_compiler.py` | `_apply_card_effects` | — | `tower_sim/engines/survivability_pipeline.py` | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/engines/stat_pipeline.py` | 7 | multiple_owners_conflict |
| `wall_fortification` | canonical_contributor_input | `tower_sim/loaders/ep_export_loader.py` | — | `tower_sim/loaders/ep_export_loader.py` | — | — | 9 | clear_owner |
| `wall_health` | canonical_target_stat | `tower_sim/engines/stat_input_compiler.py` | `_apply_unique_effects` | `tower_sim/loaders/ep_export_loader.py` | `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/engines/survivability_pipeline.py` | `tower_sim/engines/stat_input_compiler.py` | 7 | multiple_owners_conflict |
| `wall_rebuild` | canonical_contributor_input | `tower_sim/engines/stat_input_compiler.py` | `_compile_relic_stat_inputs` | `tower_sim/registry/stat_registry.py` | `tower_sim/engines/survivability_pipeline.py` | `tower_sim/engines/stat_input_compiler.py` | 7 | multiple_owners_conflict |

## 5. Ownership conflict report
- `attack_speed` shows potential duplicated authority across compiler/pipeline surfaces; canonical vs alternate compile paths need explicit demotion.
- `cash_bonus` shows potential duplicated authority across compiler/pipeline surfaces; canonical vs alternate compile paths need explicit demotion.
- `chain_lightning_chance` shows potential duplicated authority across compiler/pipeline surfaces; canonical vs alternate compile paths need explicit demotion.
- `chain_lightning_damage` shows potential duplicated authority across compiler/pipeline surfaces; canonical vs alternate compile paths need explicit demotion.
- `chain_lightning_quantity` shows potential duplicated authority across compiler/pipeline surfaces; canonical vs alternate compile paths need explicit demotion.
- `chrono_field_cooldown` shows potential duplicated authority across compiler/pipeline surfaces; canonical vs alternate compile paths need explicit demotion.
- `chrono_field_duration` shows potential duplicated authority across compiler/pipeline surfaces; canonical vs alternate compile paths need explicit demotion.
- `chrono_field_speed_reduction` shows potential duplicated authority across compiler/pipeline surfaces; canonical vs alternate compile paths need explicit demotion.
- `critical_chance` shows potential duplicated authority across compiler/pipeline surfaces; canonical vs alternate compile paths need explicit demotion.
- `damage_per_meter` shows potential duplicated authority across compiler/pipeline surfaces; canonical vs alternate compile paths need explicit demotion.
- `defense_absolute` shows potential duplicated authority across compiler/pipeline surfaces; canonical vs alternate compile paths need explicit demotion.
- `extra_defense` shows potential duplicated authority across compiler/pipeline surfaces; canonical vs alternate compile paths need explicit demotion.
- `free_attack_upgrade` shows potential duplicated authority across compiler/pipeline surfaces; canonical vs alternate compile paths need explicit demotion.
- `free_defense_upgrade` shows potential duplicated authority across compiler/pipeline surfaces; canonical vs alternate compile paths need explicit demotion.
- `golden_tower_cooldown` shows potential duplicated authority across compiler/pipeline surfaces; canonical vs alternate compile paths need explicit demotion.
- `golden_tower_duration` shows potential duplicated authority across compiler/pipeline surfaces; canonical vs alternate compile paths need explicit demotion.
- `golden_tower_multiplier` shows potential duplicated authority across compiler/pipeline surfaces; canonical vs alternate compile paths need explicit demotion.
- `health_regen` shows potential duplicated authority across compiler/pipeline surfaces; canonical vs alternate compile paths need explicit demotion.
- `inner_land_mines_cooldown` shows potential duplicated authority across compiler/pipeline surfaces; canonical vs alternate compile paths need explicit demotion.
- `inner_land_mines_damage` shows potential duplicated authority across compiler/pipeline surfaces; canonical vs alternate compile paths need explicit demotion.
- `inner_land_mines_quantity` shows potential duplicated authority across compiler/pipeline surfaces; canonical vs alternate compile paths need explicit demotion.
- `orb_speed` shows potential duplicated authority across compiler/pipeline surfaces; canonical vs alternate compile paths need explicit demotion.
- `poison_swamp_cooldown` shows potential duplicated authority across compiler/pipeline surfaces; canonical vs alternate compile paths need explicit demotion.
- `poison_swamp_damage` shows potential duplicated authority across compiler/pipeline surfaces; canonical vs alternate compile paths need explicit demotion.
- `poison_swamp_duration` shows potential duplicated authority across compiler/pipeline surfaces; canonical vs alternate compile paths need explicit demotion.
- `recovery_package_chance` shows potential duplicated authority across compiler/pipeline surfaces; canonical vs alternate compile paths need explicit demotion.
- `smart_missiles_cooldown` shows potential duplicated authority across compiler/pipeline surfaces; canonical vs alternate compile paths need explicit demotion.
- `smart_missiles_damage` shows potential duplicated authority across compiler/pipeline surfaces; canonical vs alternate compile paths need explicit demotion.
- `smart_missiles_quantity` shows potential duplicated authority across compiler/pipeline surfaces; canonical vs alternate compile paths need explicit demotion.
- `super_crit_chance` shows potential duplicated authority across compiler/pipeline surfaces; canonical vs alternate compile paths need explicit demotion.
- `super_crit_mult` shows potential duplicated authority across compiler/pipeline surfaces; canonical vs alternate compile paths need explicit demotion.
- `ultimate_crit` shows potential duplicated authority across compiler/pipeline surfaces; canonical vs alternate compile paths need explicit demotion.
- `wall_health` shows potential duplicated authority across compiler/pipeline surfaces; canonical vs alternate compile paths need explicit demotion.
- `wall_rebuild` shows potential duplicated authority across compiler/pipeline surfaces; canonical vs alternate compile paths need explicit demotion.

## 6. Ownership-ready subset
- Count: **36**
| repo_name | canonical_source_surface | ownership_status | confidence |
|---|---|---|---:|
| `bounce_shot_chance` | `tower_sim/loaders/ep_export_loader.py` | clear_owner | 9 |
| `coins_per_kill_bonus` | `tower_sim/loaders/ep_export_loader.py` | clear_owner | 9 |
| `crit_chance` | `tower_sim/engines/stat_input_compiler.py` | clear_owner | 9 |
| `crit_factor` | `tower_sim/engines/stat_input_compiler.py` | clear_owner | 9 |
| `damage_reduction` | `tower_sim/engines/combat_stat_derivation.py` | clear_owner | 9 |
| `defense` | `tower_sim/engines/stat_input_compiler.py` | clear_owner | 9 |
| `effective_damage` | `tower_sim/engines/combat/boss_engine.py` | clear_owner | 8 |
| `effective_damage_per_sec` | `tower_sim/engines/combat/boss_engine.py` | clear_owner | 8 |
| `effective_regen` | `tower_sim/engines/combat/boss_engine.py` | clear_owner | 8 |
| `effective_regen_per_sec` | `tower_sim/engines/combat/boss_engine.py` | clear_owner | 8 |
| `ep_lambda_stat_uw_cl_final_ch` | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | clear_owner | 8 |
| `ep_lambda_stat_uw_cl_final_dmg` | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | clear_owner | 8 |
| `ep_lambda_stat_uw_cl_final_qty` | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | clear_owner | 8 |
| `ep_lambda_stat_uw_dw_final_cd` | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | clear_owner | 8 |
| `ep_lambda_stat_uw_dw_final_dmg` | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | clear_owner | 8 |
| `ep_lambda_stat_uw_dw_final_qty` | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | clear_owner | 8 |
| `ep_lambda_stat_uw_sl_final_angle` | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | clear_owner | 8 |
| `ep_lambda_stat_uw_sl_final_dmg` | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | clear_owner | 8 |
| `ep_lambda_stat_uw_sl_final_lr` | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | clear_owner | 8 |
| `ep_lambda_stat_uw_sm_final_cd` | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | clear_owner | 8 |
| `ep_lambda_stat_uw_sm_final_cf` | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | clear_owner | 8 |
| `ep_lambda_stat_uw_sm_final_dmg` | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | clear_owner | 8 |
| `ep_lambda_stat_uw_sm_final_qty` | `tables/meta/registry/ep_formulas/mechanics_library.yaml` | clear_owner | 8 |
| `lab_speed` | `tower_sim/engines/stat_input_compiler.py` | clear_owner | 9 |
| `more_bosses` | `tower_sim/engines/tier_rule_apply.py` | clear_owner | 9 |
| `multishot_chance` | `tower_sim/loaders/ep_export_loader.py` | clear_owner | 9 |
| `multishot_targets` | `tower_sim/loaders/ep_export_loader.py` | clear_owner | 9 |
| `net_damage_per_sec` | `tower_sim/engines/combat/boss_engine.py` | clear_owner | 8 |
| `orb_resistance` | `tower_sim/engines/survivability_pipeline.py` | clear_owner | 9 |
| `rapid_fire_chance` | `tower_sim/loaders/ep_export_loader.py` | clear_owner | 9 |
| `recovery_package_max` | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml` | clear_owner | 9 |
| `regen_per_sec` | `tower_sim/engines/combat_stat_derivation.py` | clear_owner | 8 |
| `super_crit_multiplier` | `tower_sim/loaders/ep_export_loader.py` | clear_owner | 9 |
| `thorns_resistance` | `tower_sim/engines/survivability_pipeline.py` | clear_owner | 9 |
| `tower_regen_per_sec` | `tower_sim/engines/combat_stat_derivation.py` | clear_owner | 8 |
| `wall_fortification` | `tower_sim/loaders/ep_export_loader.py` | clear_owner | 9 |

## 7. Phase 1C.B blockers
- `ambiguous_semantics`: 4
- `mixed_stage`: 4
- `report_only_leakage`: 2
- `runtime_leakage`: 7
- Primary blocker pattern: mixed-stage and ambiguous semantics around broad labels (e.g., `damage`, `defense_pct`, `attack`, `package_chance`).

## 8. Exact files changed
- `audit/phase_1c_a_staged_ownership_audit.md`

## 9. Stop/continue recommendation
- **Continue** with Phase 1C.B only for gated-resolution workflow; keep implementation changes blocked until mixed-stage and alias/runtime leak blockers are resolved.
