# R18 Objective Family Refactor

Decision locked for downstream optimiser payloads:

- Primary EP-core objectives: `eecon`, `ehp`, `edamage`
- Additional composite objective: `survival`

`survival` is broader than `ehp` and should not replace it.

Current row counts:

- eecon: 22 rows — Primary optimiser family aligned to EP eecon logic family.
- ehp: 5 rows — Primary optimiser family aligned to EP ehp logic family; excludes boss-control helper rows.
- edamage: 4 rows — Primary optimiser family aligned to EP edamage logic family.
- survival: 6 rows — Secondary composite objective broader than ehp; includes boss-control support.

Membership notes:

- `ehp` currently contains HP, regen, DR, and wall-bonus proxy rows from the emitted whitelist.
- `survival` currently equals `ehp` plus boss-control support via Plasma Cannon effect.
- No calculator canon, formula, or routing changes were made in R18.
