# Tower Economy Mechanics Reference (v3)

Purpose:
Provide a mechanics-level reference for economy-related systems used in modelling and optimisation.

## Core economy stack
Typical high-income stack:
- Golden Tower (GT)
- Death Wave (DW)
- Black Hole (BH)
- Golden Bot (GB)

Secondary influences:
- Flame Bot (FB)
- Guardian: Summon
- Card masteries affecting coin sources

## Golden Tower
Effect:
Multiplies coins of enemies killed while active.

## Death Wave
Effect:
Adds additional coin multiplier to enemies killed during its coin-relevant effect window.

## Black Hole
Effect:
Clusters enemies, raising kill density inside multiplier windows.

## Golden Bot
Effect:
Enemies destroyed inside the bot’s range receive increased coin multiplier.

Key upgrade tracks:
- Cooldown
- Duration
- Range
- Bonus

Important modelling note:
Range determines area coverage, so first-order proxy often uses coverage ∝ range².

## Flame Bot
Effect:
Applies a persistent damage reduction debuff to enemies once hit.

Implication:
The main question is whether an enemy gets tagged before it reaches the tower.

## Summon
Effect:
Spawns additional enemies while active.

Economy implication:
Raises enemy supply that may die during GT/DW/GB windows.
