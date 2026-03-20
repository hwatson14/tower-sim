# R28 route-now acquisition plan

This pass keeps the blocked route-now defects honest. It does not bind rows without a packaged value surface.\n
## Summary

- needs_formula_or_ladder: 1
- needs_lab_ladder_and_registry: 23
- needs_policy_and_registry: 1

## Decision rule

- Only bind now when the package already has both a target plane and a defensible value surface.
- If the target plane is clear but the lab ladder is missing, acquire the ladder first.
- If the surface is binary/capability-like, confirm the package policy before binding.
- If the surface is environment/runtime, confirm the destination plane before adding ladders.

## Row-by-row acquisition plan

### LAB_ROUTE_001 — Battle Condition Reduction
- Expected target: `environment_param::bc.reduction.generic_pct`
- Bucket: `needs_formula_or_ladder`
- Required artifacts: target-plane confirmation; lab-application-registry row; lab-track-summary row; numeric ladder or accepted package formula
- Notes: Environment plane is plausible, but there is no packaged value surface yet.

### LAB_ROUTE_003 — Black Hole Damage
- Expected target: `mechanic_param::uw.black_hole.damage_pct`
- Bucket: `needs_lab_ladder_and_registry`
- Required artifacts: lab-application-registry row; lab-track-summary row; lab-values ladder or accepted package formula
- Notes: Target plane is already clear from the expected target; numeric surface is the blocker.

### LAB_ROUTE_004 — Black Hole Disable Ranged Enemies
- Expected target: `capability::capability.uw.black_hole.disable_ranged`
- Bucket: `needs_policy_and_registry`
- Required artifacts: target-plane policy confirmation; lab-application-registry row; boolean unlock/value rule
- Notes: Binary capability surfaces need explicit package policy for when level>0 becomes enabled.

### LAB_ROUTE_005 — Chain Lightning Shock
- Expected target: `mechanic_param::uw.chain_lightning.shock_enabled`
- Bucket: `needs_lab_ladder_and_registry`
- Required artifacts: lab-application-registry row; lab-track-summary row; lab-values ladder or accepted package formula
- Notes: Target plane is already clear from the expected target; numeric surface is the blocker.

### LAB_ROUTE_006 — Chain Thunder
- Expected target: `mechanic_param::uw.chain_lightning.chain_count`
- Bucket: `needs_lab_ladder_and_registry`
- Required artifacts: lab-application-registry row; lab-track-summary row; lab-values ladder or accepted package formula
- Notes: Target plane is already clear from the expected target; numeric surface is the blocker.

### LAB_ROUTE_007 — Chrono Field Damage Reduction
- Expected target: `mechanic_param::uw.chrono_field.damage_reduction_pct`
- Bucket: `needs_lab_ladder_and_registry`
- Required artifacts: lab-application-registry row; lab-track-summary row; lab-values ladder or accepted package formula
- Notes: Target plane is already clear from the expected target; numeric surface is the blocker.

### LAB_ROUTE_008 — Chrono Field Range
- Expected target: `mechanic_param::uw.chrono_field.range_m`
- Bucket: `needs_lab_ladder_and_registry`
- Required artifacts: lab-application-registry row; lab-track-summary row; lab-values ladder or accepted package formula
- Notes: Target plane is already clear from the expected target; numeric surface is the blocker.

### LAB_ROUTE_009 — Chrono Field Reduction %
- Expected target: `mechanic_param::uw.chrono_field.slow_pct`
- Bucket: `needs_lab_ladder_and_registry`
- Required artifacts: lab-application-registry row; lab-track-summary row; lab-values ladder or accepted package formula
- Notes: Target plane is already clear from the expected target; numeric surface is the blocker.

### LAB_ROUTE_010 — Death Wave Armor Stripping
- Expected target: `mechanic_param::uw.death_wave.armor_stripping_pct`
- Bucket: `needs_lab_ladder_and_registry`
- Required artifacts: lab-application-registry row; lab-track-summary row; lab-values ladder or accepted package formula
- Notes: Target plane is already clear from the expected target; numeric surface is the blocker.

### LAB_ROUTE_011 — Death Wave Cells Bonus
- Expected target: `mechanic_param::uw.death_wave.cells_bonus_multiplier`
- Bucket: `needs_lab_ladder_and_registry`
- Required artifacts: lab-application-registry row; lab-track-summary row; lab-values ladder or accepted package formula
- Notes: Target plane is already clear from the expected target; numeric surface is the blocker.

### LAB_ROUTE_013 — Death Wave Damage Amplifier
- Expected target: `mechanic_param::uw.death_wave.damage_amplifier_multiplier`
- Bucket: `needs_lab_ladder_and_registry`
- Required artifacts: lab-application-registry row; lab-track-summary row; lab-values ladder or accepted package formula
- Notes: Target plane is already clear from the expected target; numeric surface is the blocker.

### LAB_ROUTE_015 — Extra Black Hole
- Expected target: `mechanic_param::uw.black_hole.extra_black_hole_count`
- Bucket: `needs_lab_ladder_and_registry`
- Required artifacts: lab-application-registry row; lab-track-summary row; lab-values ladder or accepted package formula
- Notes: Target plane is already clear from the expected target; numeric surface is the blocker.

### LAB_ROUTE_016 — Golden Tower Bonus
- Expected target: `mechanic_param::uw.golden_tower.bonus_multiplier`
- Bucket: `needs_lab_ladder_and_registry`
- Required artifacts: lab-application-registry row; lab-track-summary row; lab-values ladder or accepted package formula
- Notes: Target plane is already clear from the expected target; numeric surface is the blocker.

### LAB_ROUTE_017 — Golden Tower Duration
- Expected target: `mechanic_param::uw.golden_tower.duration_seconds`
- Bucket: `needs_lab_ladder_and_registry`
- Required artifacts: lab-application-registry row; lab-track-summary row; lab-values ladder or accepted package formula
- Notes: Target plane is already clear from the expected target; numeric surface is the blocker.

### LAB_ROUTE_018 — Missile Amplifier
- Expected target: `mechanic_param::uw.smart_missiles.amplifier_multiplier`
- Bucket: `needs_lab_ladder_and_registry`
- Required artifacts: lab-application-registry row; lab-track-summary row; lab-values ladder or accepted package formula
- Notes: Target plane is already clear from the expected target; numeric surface is the blocker.

### LAB_ROUTE_019 — Missile Despawn Time
- Expected target: `mechanic_param::uw.smart_missiles.despawn_time_seconds`
- Bucket: `needs_lab_ladder_and_registry`
- Required artifacts: lab-application-registry row; lab-track-summary row; lab-values ladder or accepted package formula
- Notes: Target plane is already clear from the expected target; numeric surface is the blocker.

### LAB_ROUTE_020 — Missiles Explosion
- Expected target: `mechanic_param::uw.smart_missiles.explosion_radius_m`
- Bucket: `needs_lab_ladder_and_registry`
- Required artifacts: lab-application-registry row; lab-track-summary row; lab-values ladder or accepted package formula
- Notes: Target plane is already clear from the expected target; numeric surface is the blocker.

### LAB_ROUTE_021 — Shock Chance
- Expected target: `mechanic_param::shock.chance_pct`
- Bucket: `needs_lab_ladder_and_registry`
- Required artifacts: lab-application-registry row; lab-track-summary row; lab-values ladder or accepted package formula
- Notes: Target plane is already clear from the expected target; numeric surface is the blocker.

### LAB_ROUTE_022 — Shock Multiplier
- Expected target: `mechanic_param::shock.multiplier`
- Bucket: `needs_lab_ladder_and_registry`
- Required artifacts: lab-application-registry row; lab-track-summary row; lab-values ladder or accepted package formula
- Notes: Target plane is already clear from the expected target; numeric surface is the blocker.

### LAB_ROUTE_024 — Spotlight Missiles
- Expected target: `mechanic_param::uw.spotlight.missiles_enabled`
- Bucket: `needs_lab_ladder_and_registry`
- Required artifacts: lab-application-registry row; lab-track-summary row; lab-values ladder or accepted package formula
- Notes: Target plane is already clear from the expected target; numeric surface is the blocker.

### LAB_ROUTE_025 — Swamp Radius
- Expected target: `mechanic_param::uw.poison_swamp.radius_multiplier`
- Bucket: `needs_lab_ladder_and_registry`
- Required artifacts: lab-application-registry row; lab-track-summary row; lab-values ladder or accepted package formula
- Notes: Target plane is already clear from the expected target; numeric surface is the blocker.

### LAB_ROUTE_026 — Swamp Stun
- Expected target: `mechanic_param::uw.poison_swamp.stun_enabled`
- Bucket: `needs_lab_ladder_and_registry`
- Required artifacts: lab-application-registry row; lab-track-summary row; lab-values ladder or accepted package formula
- Notes: Target plane is already clear from the expected target; numeric surface is the blocker.

### LAB_ROUTE_027 — Swamp Stun Chance
- Expected target: `mechanic_param::uw.poison_swamp.stun_chance_pct`
- Bucket: `needs_lab_ladder_and_registry`
- Required artifacts: lab-application-registry row; lab-track-summary row; lab-values ladder or accepted package formula
- Notes: Target plane is already clear from the expected target; numeric surface is the blocker.

### LAB_ROUTE_028 — Swamp Stun Time
- Expected target: `mechanic_param::uw.poison_swamp.stun_duration_seconds`
- Bucket: `needs_lab_ladder_and_registry`
- Required artifacts: lab-application-registry row; lab-track-summary row; lab-values ladder or accepted package formula
- Notes: Target plane is already clear from the expected target; numeric surface is the blocker.

### LAB_ROUTE_035 — Cash / Wave
- Expected target: `canonical_stat::cash_per_wave`
- Bucket: `needs_lab_ladder_and_registry`
- Required artifacts: lab-application-registry row; lab-track-summary row; lab-values ladder
- Notes: Canonical stat target already exists elsewhere; only the lab track is missing.

## Execution order

1. Add/verify missing lab registry and ladder surfaces for mechanic params whose target plane is already settled.
2. Resolve capability policy rows.
3. Resolve environment/runtime policy rows.
4. Rebuild and verify raw rows are eliminated without changing unrelated outputs.
