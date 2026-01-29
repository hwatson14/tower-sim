# TowerSim Canonical Tables

This directory contains canonical CSV tables used by TowerSim. Each table must
include provenance notes (reference sheet or wiki citation) per the project
rules in `AGENTS.md`. This placeholder ensures the directory exists even when
tables have not yet been added.

## Table provenance
- `labs_values_v1.csv`: Promoted from audited wiki cache tables (see `tower_sim/loaders/wiki/promote_labs_tables.py`).
- `tier14_21_battle_conditions.csv`: Tier 14–21 farming battle condition magnitudes
  promoted from the Step1 part2 data dump
  (`reference/step1_dump_docs/part2_data/tier14_21_battle_conditions.csv`), with the
  original Notion extract provenance documented in
  `reference/step1_dump_docs/part3_refs_tests_docs/docs/BC_HEAT_PROVENANCE.md`.
- `battle_condition_magnitudes.csv`: Step1 part2 data dump
  (`reference/step1_dump_docs/part2_data/battle_condition_magnitudes.csv`).
- `tier_wave_damage.csv`: Step1 part2 data dump
  (`reference/step1_dump_docs/part2_data/tier_wave_damage.csv`).
- `tournament_wave_damage.csv`: Step1 part2 data dump
  (`reference/step1_dump_docs/part2_data/tournament_wave_damage.csv`).
- `tournament_more_bosses_static.csv`: Step1 part2 data dump
  (`reference/step1_dump_docs/part2_data/tournament_more_bosses_static.csv`).
- `dag.json`: Step1 part2 data dump
  (`reference/step1_dump_docs/part2_data/dag.json`).
- `bot_upgrades_v1.csv`: DVT_Bot sheet from `reference/effective_paths/copy_of_bots_v2_2.xlsx`.
- `guardian_upgrades_v1.csv`: DVT_Guardians sheet from
  `reference/effective_paths/copy_of_guardians_v2_2_5.xlsx`.
