# Perk effect application contract

This contract normalizes perk effects into simulator-facing rows without inventing hidden formulas.

Rules:
- `perk-entity-registry.csv` owns perk identity, category, and stack-count semantics.
- `perk-effect-registry.csv` decomposes each perk into one or more structured stat effects when the existing perk surface already names those effects.
- `perks.csv` owns UW-perk eligibility through `required_uw`; every `ultimate_weapon` perk row must name the UW that gates it.
- Multi-effect trade-off perks must be read as multiple rows, not a single prose blob.
- If a perk effect remains named but not fully formula-expanded, it is still valid as a structured modifier row and must not be silently embellished beyond the named effect.
- Random UW unlock remains a special unlock event and is not a scalar stat modifier.
- Pool weighting remains owned by `perk-pool-weights.csv`.
