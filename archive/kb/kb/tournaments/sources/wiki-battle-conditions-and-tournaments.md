# Wiki Battle Conditions and Tournaments Baselines

Status: wiki-backed baseline summary
Confidence: high for page-level facts copied here; not a complete battle-condition magnitude corpus

## Tournament structure
- Tournament leagues use tier-plus difficulty rather than matching the normal tier directly.
- Tournament difficulty differs from normal tiers by faster enemy stat scaling and the presence of Heat (battle conditions).
- League difficulty scales between normal tiers; for example, Copper is harder than Tier 1 but easier than Tier 2, while Champion is between Tier 11 and Tier 12.

## Tier battle conditions
- Tiers 14 and above have static battle conditions.
- The tier page lists example static BC categories including Death Ray Resistance, Thorns Resistance, Enemy Attack Speed, Knockback Resistance, Plasma Cannon Resistance, More Enemies, and Orb Resistance.

## Battle Condition Reduction lab
- Unlock: T18 W1000
- Applies to active battle conditions
- Explicit exception: does not apply to the Ultimate Weapon Duration battle condition
- Levels: 10
- Values extracted into `wiki_battle_condition_reduction_verified.csv`

## Battle Condition reduction groups
- Group 1: Resistances. Unlock T19 W100. 20 levels.
- Group 2: Enemy/Spawn Buffs.
- Group 3: Enemy Ultimates. Unlock T19 W500. 10 levels.
- Group 4: Durations/Reductions. Unlock T21 W1000. 10 levels.

## Notes for KB use
- This file is for baseline rules and unlock structure.
- Exact tournament BC magnitude ladders are still not treated as complete in the KB.
- Keep using explicit uncertainty until all magnitude tables are verified.
