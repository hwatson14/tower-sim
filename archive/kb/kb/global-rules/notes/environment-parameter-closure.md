# Environment parameter closure notes

## Closed now

- `tournament.wave_time_seconds` is treated as the total x1 wave duration in tournaments:
  - normal wave length = 26.0 seconds
  - normal cooldown = 9.0 seconds
  - tournament cooldown = 4.5 seconds
  - tournament total wave time = 30.5 seconds

This surface is now active because the public gameplay page explicitly states the base wave timers and that tournament wave cooldown is halved.

## Retired synthetic environment globals

The following synthetic globals are no longer treated as active KB truth surfaces:

- `tier.enemy_speed_multiplier`
- `enemy.base_spawn_rate_multiplier`
- `enemy.attack_speed_multiplier`
- `boss.hp_multiplier`

They may still appear as modeling conveniences inside simulator work, but the KB does not treat them as public-source-closed standalone environment parameters.
