# Ultimate weapon runtime contract

## Baseline semantics
- Ultimate Weapons are bought with Power Stones.
- Each unlocked Ultimate Weapon has 3 upgradeable stats.
- All owned Ultimate Weapons can be active in a round at the same time.
- Ultimate Weapons activate automatically when their cooldown reaches zero.
- The cooldown timer resets immediately even while the weapon remains active.
- Ultimate Weapons can be toggled on and off during a run, and toggling off then on resets cooldown when turned on.
- Toggle count is capped per run.

## Domain ownership
This domain owns UW identity, purchase ladders, base tracks, Ultimate Weapon Plus (UW+) identity, and cross-UW timing/sync semantics.

## Quantitative surfaces
Use domain tables for base tracks, Ultimate Weapon Plus (UW+) ladders, and lab side surfaces. Use this contract for high-level shared runtime semantics.
