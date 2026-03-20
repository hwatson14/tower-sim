# Migration Rules v1

## Goal
Move the KB and future sim surfaces toward a strict multi-registry object model without losing provenance.

## Rules

1. Do not add new engine-facing IDs directly into contributor naming.
2. New workshop, lab, card, module, perk, bot, guardian, relic, and UW rows should first be represented as contributors.
3. Promote a field into `canonical_stats.yaml` only if evaluators read it as a stable resolved target value.
4. Promote a field into `mechanic_params.yaml` only if runtime logic needs it directly.
5. Promote a field into `environment_params.yaml` only if it is contextual to tier, heat, enemies, tournaments, or battle conditions.
6. Capabilities must be booleans or enums only. Do not fake them as numbers.
7. Every contributor must resolve to exactly one destination object.
8. Every destination object must declare a resolver.
9. Aliases never define meaning. They only map external names to existing objects.
10. If an object class is ambiguous, fail closed and leave it unclassified until the consumer is clear.

## Immediate migration pattern

### Old pattern
- mixed flat stat naming
- mechanic parameters hidden inside contributor names
- battle conditions mixed with tower stats

### New pattern
- source rows remain provenance-rich
- engine-facing registries stay small and typed
- evaluator inputs are resolved, not raw

## Promotion test

Promote an item only if the answer to this question is yes:

`Would a runtime evaluator reasonably ask for this object directly, independent of where it came from?`

If no:
- keep it as a contributor
- or keep it as alias metadata

## Examples

### Contributor only
- `lab__tower__health__pct`
- `card__coins__kill_bonus__multiplier`
- `module__core__black_hole_size__pct`

### Canonical stat
- `tower_hp`
- `coin_kill_multiplier`
- `wall_regen`

### Mechanic param
- `uw.black_hole.duration_seconds`
- `bot.golden.range_m`

### Environment param
- `bc.enemy_attack_speed_pct`
- `tier.enemy_hp_multiplier`

### Capability
- `capability.wall.enabled`
- `capability.inner_land_mines.enabled`
