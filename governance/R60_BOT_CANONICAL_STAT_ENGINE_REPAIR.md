# R60 Bot canonical stat-engine repair

## Intent
Make bot runtime stats behave like workshop and UW canonicals:
- compile into `mechanic_param::bot.*` surfaces
- use canonical names distinct from raw IDS bot input labels
- include all routed contributors in the stat engine
- update scenario/timing consumers to use the canonical bot surfaces

## What changed
- Bot medal-track inputs now bind through KB contributor mappings into `mechanic_param::bot.*`.
- Bot lab rows now resolve to numeric contributions and feed the same canonicals:
  - cooldown labs as negative seconds
  - duration labs as positive seconds
  - Thunder Bot Linger Time lab as positive linger duration seconds
- Bot range relic/vault contributions are promoted into:
  - `mechanic_param::bot.global.range_bonus_m`
  - each named bot range canonical
- Scenario and timing engines now consume canonical bot mechanic surfaces.

## Current canonical outputs
- `mechanic_param::bot.golden.duration_seconds = 27.5`
- `mechanic_param::bot.golden.cooldown_seconds = 90.0`
- `mechanic_param::bot.golden.range_m = 59.0`
- `mechanic_param::bot.golden.bonus_multiplier = 5.6`
- `mechanic_param::bot.flame.cooldown_seconds = 8.0`
- `mechanic_param::bot.flame.damage_multiplier = 50.0`
- `mechanic_param::bot.flame.damage_reduction_pct = 0.47`
- `mechanic_param::bot.flame.range_m = 63.0`
- `mechanic_param::bot.amplify.duration_seconds = 20.0`
- `mechanic_param::bot.amplify.cooldown_seconds = 120.0`
- `mechanic_param::bot.amplify.range_m = 34.0`
- `mechanic_param::bot.amplify.bonus_multiplier = 3.5`
- `mechanic_param::bot.thunder.duration_seconds = 5.0`
- `mechanic_param::bot.thunder.cooldown_seconds = 120.0`
- `mechanic_param::bot.thunder.range_m = 34.0`
- `mechanic_param::bot.thunder.linger_slow_pct = 0.2`
- `mechanic_param::bot.thunder.linger_duration_seconds = 0.0`
- `mechanic_param::bot.global.range_bonus_m = 9.0`

## Remaining note
`runtime_mechanic_param::bot.flame_bot.lab_burn_stack` remains outside the canonical bot runtime tranche because there is no active canonical contract surface for it in this repo yet.
