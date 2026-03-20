# Guardian System

Status: expanded with verified chip baselines and upgrade surfaces.

## Core structure
The Guardian unlocks for 200 bits and starts with 1 chip slot plus the base chips Attack and Ally. Additional chip families represented in the KB are Bounty, Fetch, Scout, and Summon.

## Runtime model
Guardian belongs in `mechanic_params`, not `canonical_stats`. Its chips are cooldown-driven discrete mechanics with target counts and effect-specific parameters.

## Verified quantitative surfaces now present
- `wiki_guardian_chip_baselines_expanded.csv`
- `wiki_guardian_attack_levels_full.csv`
- `wiki_guardian_ally_levels_1_31_slice.csv`

## Interpretation

### Attack
Attack is an execute-style chip because it deals a percentage of missing health. That makes it synergy-sensitive with percent-HP and boss-chunk tools.

### Ally
Ally is a sustain-extending chip, not a pure healing stat. It produces a distinct recovery-package mechanic that can push recovery above the basic max recovery line.

### Bounty
Bounty is a conditional economy chip. Its value depends on enemy type mix and all active coin multipliers at kill time.

### Fetch
Fetch is a meta-economy chip, not a run-DPS or run-coin chip. It changes off-run resource flow.

### Scout
Scout is a geometry and damage-model chip because it alters effective distance for damage calculations during its active window.

### Summon
Summon is a weird little goblin. It increases enemy count during its window while adding cash bonus. It should be evaluated through whether extra enemies are net-positive or just extra pressure.


## Normalization result
Guardian now has normalized entity, track, contributor-routing, and runtime-proof surfaces for material simulator use.
