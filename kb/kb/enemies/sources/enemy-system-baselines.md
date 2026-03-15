# Enemy system baselines

## Structural facts
- Bosses appear every 10 waves by default.
- Enemy HP and damage scaling are owned by the enemy domain base tables.
- Enemy-type special behavior such as fleets, elites, bosses and protectors should be layered as modifiers or exception semantics, not baked into base HP/damage anchors.

## Quantitative source choice
Use `enemy-health-table.csv`, `enemy-damage-table.csv`, and their expanded long-form tables as the canonical base numeric surfaces in this KB.
