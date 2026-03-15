# Perk System

## Core structure
Perks are run-earned advantages unlocked through labs. They are selected during a run and include standard perks, ultimate-weapon-related perks, trade-off perks, and perk-lab governance surfaces.

## Canonical surfaces
- `kb/perks/tables/perks.csv`
- `kb/perks/tables/perk-pool-weights.csv`

## Verified semantics
- perks are unlocked through labs
- perks start appearing at wave 200
- waves required increases after 20, 30 and 40 selected perks
- waves required is modified by the Waves Required lab and the Perk Wave Requirement perk

## Structured representation
Perks have normalized entity and decomposed effect registries so multi-effect trade-off perks can be consumed as structured rows rather than prose.
