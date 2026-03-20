# UW Economy and Sync Models

This file records the economy reasoning layer added in KB v9.

## Golden Tower
- Multiplies both coins and cash during activation.
- Primary axes: bonus, duration, cooldown.

## Black Hole
- Coin bonus applies when enemies die inside Black Hole.
- Relevant axes: size, duration, cooldown, coin bonus, damage.

## Core farming overlap
Primary target:
- Golden Tower
- Black Hole
- Spotlight

Conceptual model:
coin_multiplier = GT_multiplier × BH_multiplier × Spotlight_related_effects

## Sync principle
Cooldown synchronization increases overlap frequency and overlap quality.
