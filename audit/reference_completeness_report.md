# Reference Completeness Report

This report inventories required runtime tables and classifies them as:
- **runtime**: present outside `tables/` and test fixtures.
- **step1-only**: present only under `tables/step1_dump_docs/...`.
- **missing**: not present anywhere in the repo.

## Manifest (machine-readable)

```yaml
required_tables:
  bc_heat:
    status: missing
    runtime_paths:
    - tower_sim/tables/battle_condition_magnitudes.csv
    - tower_sim/tables/tier_battle_conditions.csv
    step1_only_paths: []
    missing_paths:
    - battle_conditions.csv
    - heat.csv
    - heat_wave_scalar.csv
  wave_damage:
    status: runtime
    runtime_paths:
    - tower_sim/tables/tier_wave_damage.csv
    - tower_sim/tables/tournament_wave_damage.csv
    step1_only_paths: []
    missing_paths: []
  tournament_boss_freq:
    status: runtime
    runtime_paths:
    - tower_sim/tables/tournament_more_bosses_static.csv
    step1_only_paths: []
    missing_paths: []
  dag_inputs:
    status: missing
    runtime_paths:
    - tower_sim/tables/dag.json
    step1_only_paths: []
    missing_paths:
    - tiers.csv
```
