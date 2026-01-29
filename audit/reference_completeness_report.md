# Reference Completeness Report

This report inventories required runtime tables and classifies them as:
- **runtime**: present outside `reference/` and test fixtures.
- **step1-only**: present only under `reference/step1_dump_docs/...`.
- **missing**: not present anywhere in the repo.

## Manifest (machine-readable)

```yaml
required_tables:
  bc_heat:
    status: missing
    runtime_paths: []
    step1_only_paths:
      - reference/step1_dump_docs/part2_data/battle_condition_magnitudes.csv
      - reference/step1_dump_docs/part2_data/tier14_21_battle_conditions.csv
    missing_paths:
      - battle_conditions.csv
      - heat.csv
      - reference/step1_dump_docs/part2_data/heat_wave_scalar.csv
  wave_damage:
    status: step1-only
    runtime_paths: []
    step1_only_paths:
      - reference/step1_dump_docs/part2_data/tier_wave_damage.csv
      - reference/step1_dump_docs/part2_data/tournament_wave_damage.csv
    missing_paths: []
  tournament_boss_freq:
    status: step1-only
    runtime_paths: []
    step1_only_paths:
      - reference/step1_dump_docs/part2_data/tournament_more_bosses_static.csv
    missing_paths: []
  dag_inputs:
    status: missing
    runtime_paths: []
    step1_only_paths:
      - reference/step1_dump_docs/part2_data/dag.json
    missing_paths:
      - tiers.csv
```
