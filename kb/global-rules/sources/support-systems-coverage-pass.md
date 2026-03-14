# Support Systems Coverage Pass

This pass imported additional normalized repo tables into `domain tables/` so the KB contains support-system surfaces that were previously only present in the repo.

## Newly embedded surfaces
- Perks: `perks.csv`, `perk-pool-weights.csv`
- Boss hit interval: `boss-hit-interval.csv`
- Tournament heat scaffolds: `heat-battle-condition-registry.csv`, `heat-scale-long.csv`, `tournament-heat-steps.csv`, `tournament-more-bosses-intervals.csv`
- Assist systems: `assist-stone-levels.csv`, `assist-efficiency-upgrade-costs.csv`, `assist-slot-unlock-costs.csv`, `assist-unique-rarity-upgrade-costs.csv`
- Module normalized support tables: `module-main-effect-bases.csv`, `module-main-effect-bands.csv`, `module-substats.csv`
- Economy/support: `lab-values.csv`, `card-masteries.csv`

## Notes
- `vault_stats_v1.csv` exists in the repo but is empty, so it was not promoted as a useful quantitative surface.
- `boss-hit-interval.csv` is explicitly an assumption surface in the repo, not a wiki-verified mechanic.
- Heat/tournament tables are quantitative and useful but still depend on the repo's normalization logic; keep provenance visible.
