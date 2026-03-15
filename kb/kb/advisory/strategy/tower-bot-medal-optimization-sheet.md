# Tower Bot Medal Optimisation Sheet

Objective:
Determine optimal medal allocation between Golden Bot and Flame Bot.

## Flame Bot metrics
- Cooldown
- Damage Reduction
- Range

Core formulas:
activations_per_minute = 60 / cooldown
effective_damage = 1 − DR
survival_multiplier = 1 / effective_damage

## Golden Bot metrics
- Cooldown
- Duration
- Range
- Coin multiplier

Core proxy:
coverage ∝ range²
GB_coin_gain ∝ uptime × bonus × coverage

## Medal strategy frame
1. Ensure survivability floor is adequate
2. Increase Flame Bot enough that runs do not collapse
3. Allocate remaining medals to Golden Bot for coins/hour

## Warning
Any medal optimisation without a clear run-length model can overvalue GB and undervalue FB.
