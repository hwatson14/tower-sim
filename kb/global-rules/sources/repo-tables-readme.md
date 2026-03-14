# TowerSim Tables Layout

This directory contains deterministic table assets with explicit provenance. Runtime loaders must resolve canonical tables from `tables/inputs/**` through the table resolver (`tower_sim/loaders/table_paths.py`) and fail closed when required entries are missing.

## Folder policy
- `inputs/`: canonical runtime tables.
  - `inputs/combat/`
  - `inputs/tournament/`
  - `inputs/economy/`
  - `inputs/modules/`
  - `inputs/uw/`
  - `inputs/perks/`
  - `inputs/cards/`
- `cache/wiki/`: scraped wiki cache tables used for promotion/audits only.
- `derived/`: generated snapshots/artifacts (for example `dag.json`).
- `meta/schemas/`: schemas.
- `meta/registry/`: registry metadata and formula libraries.
- `legacy/`: deprecated non-runtime tables (`tier_wave_damage.csv`, `tournament_wave_damage.csv`).

## Runtime policy
- Canonical runtime tables must not be loaded from `cache/` or `legacy/`.
- Missing canonical table paths are explicit errors (fail-closed).
- Table provenance notes remain in each table's own `source`/`provenance` columns and in registry metadata.
