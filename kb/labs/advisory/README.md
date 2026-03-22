# Lab advisory surfaces

These surfaces stay under `kb/labs/advisory/` because they are planner/advisor guidance, not mechanical lab truth.

## Consumer guidance
- Join advisory rows to lab owners via `lab_canonical_id`.
- Treat `ranking_primary` as the default prior.
- Treat `ranking_conditional` as an optional scenario-specific override.
- Preserve `notes` when presenting or explaining recommendations.
- Never let this advisory surface override stronger mechanic or scenario-specific evidence.

## Mapping guidance
The advisory table is catalog-mapped to canonical lab IDs. The only explicit manual alias overrides are already encoded in the table/registry for:
- `Workshop Enhancements` -> `LAB_WORKSHOP_ENHANCEMENT`
- `Enhancement Attack - Coin Discount` -> `LAB_ENHANCEMENT_ATTACK_COIN_DISCOUNT`
- `Enhancement Defense - Coin Discount` -> `LAB_ENHANCEMENT_DEFENSE_COIN_DISCOUNT`
- `Enhancement Utility - Coin Discount` -> `LAB_ENHANCEMENT_UTILITY_COIN_DISCOUNT`
