# Enemy Scaling Model

Status: raw-table-first canonical surface.

## Canonical numeric source in this KB
- `kb/enemies/tables/enemy-damage-table.csv`
- `kb/enemies/tables/enemy-health-table.csv`
- expanded long forms:
  - `kb/enemies/tables/enemy-damage-scaling-long.csv`
  - `kb/enemies/tables/enemy-health-scaling-long.csv`

## Practical model
- Enemy HP and enemy damage should be read from the raw anchor tables first.
- Between anchor waves, the bundled runtime model uses log-linear interpolation (linear in ln(value)).
- Above the maximum anchor, the repo runtime model clamps to the max-anchor value.
- Tier and league labels are separate surfaces in the same raw tables; do not collapse them into a single "tier multiplier" concept.

## Interpretation rule
Use prose curve descriptions only as explanatory scaffolding. For simulation or quantitative reasoning, prefer the raw tables and their interpolation policy.
