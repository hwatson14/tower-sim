# TowerSim Canonical Tables

This directory contains canonical CSV tables used by TowerSim. Each table must
include provenance notes (reference sheet or wiki citation) per the project
rules in `AGENTS.md`.

## Table provenance
- `enemy_damage_table.csv`: Canonical enemy damage anchors keyed by `wave_actual`
  for `Tier 1..21` and tournament leagues. Runtime computes per-wave values via
  **log-linear interpolation (linear in ln(value))** between anchors, with explicit edge behavior:
  below min wave raises, above max wave clamps to the last anchor.
- `enemy_health_table.csv`: Canonical enemy health anchors keyed by
  `wave_actual` for `Tier 1..21` and tournament leagues. Runtime uses the same
  log-linear interpolation (linear in ln(value)) + edge behavior contract as damage.
- `labs_values_v1.csv`: Promoted from audited wiki cache tables
  (see `tower_sim/loaders/wiki/promote_labs_tables.py`).
- `tier_battle_conditions.csv`: Tier 14–21 farming battle condition magnitudes
  (tiers 1–13 have no battle conditions per user-provided clarification).
- `battle_condition_magnitudes.csv`: battle condition magnitudes including
  tournament heat values from the Player & Stuff spreadsheet
  (Battle Conditions sheet, provided by user in prompt).
- `tournament_more_bosses_static.csv`: tournament boss interval table.
- `dag.json`: canonical DAG snapshot used by runtime checks.
- `bot_upgrades_v1.csv`: DVT_Bot sheet from
  `tables/effective_paths/copy_of_bots_v2_2.xlsx`.
- `guardian_upgrades_v1.csv`: DVT_Guardians sheet from
  `tables/effective_paths/copy_of_guardians_v2_2_5.xlsx`.
- `perks_v1.csv`: User-provided wiki excerpt in prompt (perk list, effects,
  max picks, stacking notes).
- `perk_pool_weights_v1.csv`: User-provided wiki excerpt in prompt
  (perk pool weighting).
- `assist_stone_levels_v1.csv`: User-provided wiki excerpt in prompt
  (assist stone efficiency is linear: level 0 = 1% and +1% per level).
- `module_substats_v1.csv`: User-provided wiki excerpt in prompt
  (full sub-module caps by slot/rarity).
- `module_main_effect_bases_v1.csv`: Module Base Stat sheet
  (user-provided in prompt).
- `module_main_effect_bands_v1.csv`: Module Base Stat sheet
  (user-provided in prompt).
- `vault_stats_v1.csv`: Table shell for vault stat multipliers
  (Max Recovery entry still missing from prompt; fail-closed until populated).
- `wse_presets_v1.csv`: Table shell for WSE preset mappings
  (Max Recovery preset values still missing from prompt; fail-closed until populated).
- `uw_purchase_costs_v1.csv`: Effective Paths UWs v2.1.2 sheet
  `All UWs!B5:E14` (Unlock Costs per UW and UW+).
- `uw_track_ladders_v1.csv`: Effective Paths UW ladder token columns
  (`DVT_UW_UG_*`) extracted from Data_Val_Tables snapshot.
- `uw_plus_ladders_v1.csv`: Effective Paths UW+ ladder token columns
  (`DVT_UW_UG_*` plus tracks) extracted from Data_Val_Tables snapshot.
- `assist_slot_unlock_costs_v1.csv`: User-provided rule in prompt
  (assist unlock is Epic unlock cost: 1000 stones).
- `assist_unique_rarity_upgrade_costs_v1.csv`: User-provided wiki table in prompt
  (Epic/Legendary/Mythic/Ancestral rarity upgrade stone costs).
- `assist_efficiency_upgrade_costs_v1.csv`: Effective Paths Modules v5.12
  sheet `DVT_Modules!H2:J71` (`Assist level`, `Cost`, `%`).
- `card_masteries_v1.csv`: Card mastery table pasted from the Tower wiki by the
  user in the prompt (wiki-exact names + level 0–9 values).

## Tournament heat/BC tables (v2 canonical)
- `heat_scale_long.csv`: canonical **stepwise** heat values keyed by `league` +
  `wave_actual` and BC key/variant (`bc_id = "{bc_key}:{bc_variant}"`).
- `heat_bc_registry.csv`: canonical BC registry (includes
  `applies_champion`/`applies_legend`) consumed by tournament BC set
  enumeration.
- `tournament_league_rules.csv`: v2 league scope is Champion + Legend only.

## Deprecated
- `tier_wave_damage.csv` (legacy).
- `tournament_wave_damage.csv` (legacy).
