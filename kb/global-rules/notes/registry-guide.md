# Registry Guide

This folder defines the live object model for the Tower GPT KB and any future TowerSim-facing ingestion.

## Active registry classes

### 1. canonical_stats.yaml
Stable evaluator-facing resolved values.

Examples:
- `tower_hp`
- `tower_regen`
- `tower_damage`
- `wall_hp`
- `coin_kill_multiplier`

These are the values optimisation, survivability, and wave-death evaluators should read.

### 2. mechanic_params.yaml
Runtime mechanic parameters that are not general target stats.

Examples:
- `uw.black_hole.duration_seconds`
- `uw.golden_tower.cooldown_seconds`
- `guardian.attack.cooldown_seconds`
- `module.orbital_augment.electron_count`

### 3. environment_params.yaml
Run-context modifiers.

Examples:
- `tier.enemy_hp_multiplier`
- `bc.enemy_attack_speed_pct`
- `bc.more_enemies_pct`
- `tournament.wave_cooldown_multiplier`

### 4. capabilities.yaml
Boolean or enum unlock / feature-presence switches.

Examples:
- `capability.wall.enabled`
- `capability.uw.black_hole.enabled`
- `capability.guardian.fetch.enabled`

### 5. contributors.yaml
Schema contract for source rows.
Contributor IDs use `source__entity__attribute__measure`.

### 6. aliases.yaml
External labels and wiki/UI names that resolve to a destination object.

### 7. resolvers.yaml
Declared combination rules for each destination object class.

## Live mapping file

`contributor_mappings_full.yaml` is the active routing layer.
It is the consolidated source-to-object placement file for the KB.

## Design rules

- Do not use contributor IDs as engine-facing stat IDs.
- Do not put run-state variables in these registries.
- Do not mix environment modifiers into permanent tower stats.
- Promote to `canonical_stats` only if evaluators need the resolved value directly.
- Promote to `mechanic_params` if the runtime consumes the value as a mechanic knob.
- Use `capabilities` for unlocks and feature-presence, not fake numeric placeholders.
