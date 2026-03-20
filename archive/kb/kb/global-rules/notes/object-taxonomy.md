# Tower KB / TowerSim Object Taxonomy v1

## Purpose

This taxonomy separates engine-facing objects into distinct classes so the KB and TowerSim do not collapse target stats, runtime mechanic parameters, environment modifiers, capabilities, and source contributors into one mixed namespace.

## Core rule

The engine should never need to inspect raw source-family names such as `lab__...` or `card__...` during evaluation.

The engine should read only resolved registries:
- canonical target stats
- runtime mechanic parameters
- environment parameters
- capabilities
- derived run-state variables

## Object classes

### 1. Canonical target stats
Stable resolved values used directly by evaluators.

Examples:
- `tower_hp`
- `tower_regen`
- `tower_damage`
- `wall_hp`
- `coin_kill_multiplier`

### 2. Runtime mechanic parameters
Direct parameters for specific mechanics.

Examples:
- `uw.black_hole.duration_seconds`
- `uw.golden_tower.cooldown_seconds`
- `bot.flame.damage_reduction_pct`
- `guardian.bounty.coin_multiplier`

### 3. Environment parameters
Run-context modifiers that come from tier, battle conditions, tournaments, heat, and enemy rules.

Examples:
- `tier.enemy_hp_multiplier`
- `bc.enemy_attack_speed_pct`
- `tournament.wave_cooldown_multiplier`
- `heat.enemy_damage_multiplier`

### 4. Capabilities
Booleans or enums that enable branches in runtime logic.

Examples:
- `capability.wall.enabled`
- `capability.death_ray.enabled`
- `capability.guardian.bounty.enabled`

### 5. Contributors
Source-side rows with provenance.

Examples:
- `workshop__tower__health__flat`
- `lab__tower__health__pct`
- `card__extra_orb__count__count`
- `module__armor__wall_health__pct`

### 6. Aliases
External names that resolve to one of the above objects.

Examples:
- `Health` -> `tower_hp`
- `Golden Tower Duration` -> `uw.golden_tower.duration_seconds`



### 8. Account resources and profile context
Persistent account-side values that matter for planning, progression, or feature gating but are not direct run-time combat stats.

Examples:
- `account_resource.stones`
- `account_resource.gems`
- `account_resource.lifetime_coins`
- `account_context.farming_tier`
- `account_context.tournament_league`
- `account_context.best_wave.tier_14`

### 9. Cosmetic bonuses
Passive bonuses originating from cosmetics and media ownership rather than ordinary combat/economy upgrade systems.

Examples:
- `cosmetic_bonus.theme_song_coin_multiplier`

### 10. Account flags
Booleans or enum-like account-side unlocks that affect menus, automation, or premium access but are not combat capabilities.

Examples:
- `account_flag.disable_ads`
- `account_flag.workshop_presets_unlocked`
- `account_flag.premium_pack_owned`

### 7. Resolvers
Declared combination rules for assembling resolved objects from contributors.

Examples:
- `standard_scalar_stat`
- `pct_capped_scalar_stat`
- `uw_duration_param`
- `bc_effective_value`

## What belongs where

### Keep narrow in canonical target stats
Only stable evaluator-facing values belong here.

### Put mechanic-specific knobs in runtime mechanic params
Do not promote every cooldown, angle, duration, count, or special effect into canonical target stats.

### Keep battle conditions and tier modifiers in environment params
They are contextual run modifiers, not permanent tower stats.

### Keep `source__entity__attribute__measure` for contributors only
That grammar is ideal for provenance rows, not for all engine-facing objects.

## State split

The overall system should preserve three state planes:

### Account / loadout state
Persistent inputs such as workshop levels, lab levels, unlocked Ultimate Weapons (UWs), equipped modules, cards, guardians, relics.

### Environment state
Tier, battle conditions, tournament modifiers, heat, enemy schedule.

### Run state
Current HP, current wall HP, cooldown timers, active effects, current wave, enemy count on screen.

## decision

The authoritative registries for v1 are:
- `canonical_stats.yaml`
- `mechanic_params.yaml`
- `environment_params.yaml`
- `capabilities.yaml`
- `contributors.yaml`
- `aliases.yaml`
- `resolvers.yaml`

Derived run-state variables remain evaluator-owned and should not be back-propagated into contributor definitions.

_IDS section routing may terminate in canonical target stats, runtime mechanic parameters, environment parameters, capabilities, account resources/context, cosmetic bonuses, or account flags. That keeps every uploaded _IDS section in an explicit destination class even when the row is not a direct combat contributor.
