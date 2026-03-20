# R61 Publishable Subset Expansion: Defense %, Thorn Damage, Orb Speed

## Decision
Promote three additional workshop-mutated canonical paths into the guarded publishable subset:
- `Defense % -> canonical_stat::tower_defense_pct`
- `Thorn Damage -> canonical_stat::tower_thorns_damage_pct`
- `Orb Speed -> canonical_stat::tower_orb_speed_rpm`

## Why these are in scope
These paths are all package-closed on the R54 routed-repairs baseline plus R60 no-override stat engine:
- workshop tracks exist in compiled account state
- contributor routing closure points directly to the canonical stat
- current stat-engine resolution does not require override postprocessing for these surfaces

## Evidence used
### Defense %
- `compilers/stat_input_compiler.py` maps `Defense %` to `workshop__tower__defense_pct__pct`
- `kb/ledgers/tables/contributor-routing-closure.csv` routes workshop/relic/vault rows to `canonical_stat::tower_defense_pct`
- `config/destination_formula_ledger.yaml` marks `canonical_stat::tower_defense_pct` as `generic_validated`

### Thorn Damage
- `compilers/stat_input_compiler.py` maps `Thorn Damage` to `workshop__tower__thorns_damage__pct`
- `kb/ledgers/tables/contributor-routing-closure.csv` routes workshop/relic/vault rows to `canonical_stat::tower_thorns_damage_pct`
- current tranche publishes only `tower_thorns_damage_pct`, not `wall_thorns_damage_pct`, so no cross-stat wall dependency is inferred

### Orb Speed
- `compilers/stat_input_compiler.py` maps `Orb Speed` to `workshop__tower__orb_speed__rpm`
- `kb/ledgers/tables/contributor-routing-closure.csv` routes workshop/lab/relic/vault rows to `canonical_stat::tower_orb_speed_rpm`
- `config/destination_formula_ledger.yaml` already classifies the related surface family as publishable; no override dependence remains in the stat engine core

## Scope boundary
This tranche intentionally does **not** promote:
- `wall_thorns_damage_pct`
- scenario-adjusted thorns resistance surfaces
- any derived combat/runtime consumer surface

Those remain downstream or cross-plane and should not be inferred from these canonical promotions alone.
