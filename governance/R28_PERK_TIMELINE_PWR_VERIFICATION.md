# R28 perk timeline PWR verification

Confirmed: the perk timeline engine models PWR internally and recalculates later perk waves when a PWR pick is taken.

## Evidence from code

- `tower_sim/engines/perk_timeline_generator.py` computes `ideal = _ideal_wave(next_perk_number, pwr_stacks, ...)` before each next perk.
- When a PWR perk is taken, `pwr_stacks += 1` occurs immediately.
- The next loop iteration uses the updated `pwr_stacks`, so the next perk wave is recomputed from the reduced requirement.
- If the retroactive recomputation places the next perk at or before the current wave, the engine awards it immediately via `retroactive_burst`.
- `run_stats.py` builds a runtime policy from IDS-backed controls (`Waves Required`, `Standard Perks Bonus`, `Perk Option Quantity`, ban capacity) and generates a static timeline file plus final state file.

## Static ownership conclusion

Given the runtime policy JSON plus seed, the engine fully owns perk timing generation for max progression. It does not require an external precomputed timing table.

## Regression coverage already present

- `tests/test_perk_tables.py` contains explicit retroactive PWR tests, including burst behavior after multiple PWR picks.
- It also checks the engine reports `pwr_model = retroactive_linear_additive`.
