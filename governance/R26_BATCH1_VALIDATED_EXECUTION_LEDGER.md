# R26 Batch 1 validated execution ledger

Purpose: convert the harness bug master report into a package-grounded execution list for hard route-now defects only.

This pass validates each defect against the current calculator package and splits work into safe implementation buckets rather than patching blind.

## Outcome summary

- Hard route-now defects reviewed: 33
- route_bind_now: 4
- alias_only: 4
- semantic_retarget: 1
- route_bind_needs_ladder_or_formula: 24

## What is safely patchable immediately

- LAB_ROUTE_002 | Black Hole Coin Bonus | route_bind_now | target `mechanic_param::uw.black_hole.coin_bonus_multiplier` | ladder `exact_label`
- LAB_ROUTE_012 | Death Wave Coin Bonus | route_bind_now | target `mechanic_param::uw.death_wave.coin_bonus_multiplier` | ladder `exact_label`
- LAB_ROUTE_023 | Spotlight Coin Bonus | route_bind_now | target `mechanic_param::uw.spotlight.coin_bonus_multiplier` | ladder `exact_label`
- LAB_ROUTE_029 | Coins / Wave | route_bind_now | target `canonical_stat::coins_per_wave` | ladder `alias_label`
- VAULT_ALIAS_030 | Cash / Wave | alias_only | target `canonical_stat::cash_per_wave` | ladder `n/a`
- VAULT_ALIAS_031 | Coins / Kill | alias_only | target `canonical_stat::coin_kill_multiplier` | ladder `n/a`
- VAULT_ALIAS_032 | Coins / Wave | alias_only | target `canonical_stat::coins_per_wave` | ladder `n/a`
- VAULT_ALIAS_033 | Interest / Wave | alias_only | target `canonical_stat::interest_per_wave_pct` | ladder `n/a`
- LAB_ROUTE_014 | Death Wave Health | semantic_retarget | target `mechanic_param::uw.death_wave.health_bonus_multiplier` | ladder `missing_ladder`

## What is blocked from safe patching in this pass

These rows are structurally real, but the bundled package does not currently expose a directly usable ladder/value surface under the exact routed label. They should not be force-bound until the numeric source surface is added or an approved formula fallback is defined.

- LAB_ROUTE_001 | Battle Condition Reduction -> `environment_param::bc.reduction.generic_pct`
- LAB_ROUTE_003 | Black Hole Damage -> `mechanic_param::uw.black_hole.damage_pct`
- LAB_ROUTE_004 | Black Hole Disable Ranged Enemies -> `capability::capability.uw.black_hole.disable_ranged`
- LAB_ROUTE_005 | Chain Lightning Shock -> `capability::capability.uw.chain_lightning.shock`
- LAB_ROUTE_006 | Chain Thunder -> `mechanic_param::uw.chain_lightning.chain_thunder_pct`
- LAB_ROUTE_007 | Chrono Field Damage Reduction -> `capability::capability.uw.chrono_field.damage_reduction.enabled`
- LAB_ROUTE_008 | Chrono Field Range -> `mechanic_param::uw.chrono_field.range_m`
- LAB_ROUTE_009 | Chrono Field Reduction % -> `mechanic_param::uw.chrono_field.damage_reduction_pct`
- LAB_ROUTE_010 | Death Wave Armor Stripping -> `mechanic_param::uw.death_wave.armor_stripping_pct`
- LAB_ROUTE_011 | Death Wave Cells Bonus -> `mechanic_param::uw.death_wave.cell_bonus_multiplier`
- LAB_ROUTE_013 | Death Wave Damage Amplifier -> `mechanic_param::uw.death_wave.damage_multiplier`
- LAB_ROUTE_015 | Extra Black Hole -> `capability::capability.uw.black_hole.extra_black_hole`
- LAB_ROUTE_016 | Golden Tower Bonus -> `mechanic_param::uw.golden_tower.bonus_multiplier`
- LAB_ROUTE_017 | Golden Tower Duration -> `mechanic_param::uw.golden_tower.duration_seconds`
- LAB_ROUTE_018 | Missile Amplifier -> `mechanic_param::uw.smart_missiles.amplifier_multiplier`
- LAB_ROUTE_019 | Missile Despawn Time -> `mechanic_param::uw.smart_missiles.despawn_time_seconds`
- LAB_ROUTE_020 | Missiles Explosion -> `capability::capability.uw.smart_missiles.explosion`
- LAB_ROUTE_021 | Shock Chance -> `mechanic_param::uw.chain_lightning.shock_chance_pct`
- LAB_ROUTE_022 | Shock Multiplier -> `mechanic_param::uw.chain_lightning.shock_multiplier`
- LAB_ROUTE_024 | Spotlight Missiles -> `mechanic_param::uw.spotlight.missiles_interval_seconds`
- LAB_ROUTE_025 | Swamp Radius -> `mechanic_param::uw.poison_swamp.radius_m`
- LAB_ROUTE_026 | Swamp Stun -> `capability::capability.uw.poison_swamp.stun`
- LAB_ROUTE_027 | Swamp Stun Chance -> `mechanic_param::uw.poison_swamp.stun_chance_pct`
- LAB_ROUTE_028 | Swamp Stun Time -> `mechanic_param::uw.poison_swamp.stun_duration_seconds`

## Notes

- Several harness defects point at destination IDs that already exist in the package. In those cases the bug is likely source-label routing or missing lab application registry rows, not destination absence.
- `Coins / Wave` is a label-normalisation issue against bundled `Coins/Wave` lab surfaces.
- `Death Wave Health` is a semantic mismatch: current package routes it to `canonical_stat::tower_hp`, while the harness expects a dedicated mechanic param.
## Validation correction after executable rerun

A rebuild against the working package showed that four of the previously listed safe items were already functionally present before this patch pass:

- Black Hole Coin Bonus already emitted to `runtime_mechanic_param::uw.black_hole.coin_bonus_multiplier`
- Death Wave Coin Bonus already emitted to `runtime_mechanic_param::uw.death_wave.coin_bonus_multiplier`
- Spotlight Coin Bonus already emitted to `runtime_mechanic_param::uw.spotlight.coin_bonus_multiplier`
- Death Wave Health already emitted to `canonical_stat::tower_hp` under the current package semantic model

This means the real executable Batch 1 closure scope for this pass is the alias/normalization layer:

- Lab label normalization for `Coins / Wave` against `Coins/Wave`
- Vault alias normalization for `Cash / Wave`, `Coins / Kill`, `Coins / Wave`, `Interest / Wave`

`Death Wave Health` remains a semantic-retarget decision, not a missing-route bug.
