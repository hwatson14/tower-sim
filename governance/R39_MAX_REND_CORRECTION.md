# R39 Max Rend correction

## Scope
Correct the Max Rend Mult semantic defect left in R38 without changing the accepted Free Upgrades or Bounce Shot Targets fixes.

## Correction
R38 incorrectly used workshop `Rend Armor Mult` inside the final `max_rend_mult` formula.

R39 corrects the canonical final formula to:

- `(8 + lab_bonus + 8 x module_substat_pct_bonus) x Rend Armor enhancement multiplier`

## Why
EP target for this package is `x9.68`.
Current account state shows:

- base max rend cap = `x8`
- Rend Armor enhancement multiplier = `x1.21`
- lab contribution = `0`
- module max-rend contribution = `0`

So:

- `8 x 1.21 = 9.68`

This proves workshop `Rend Armor Mult` is not the semantic owner of the final Max Rend cap surface.

## Implementation details
- Removed workshop dual-routing into `canonical_stat::max_rend_mult`
- Dual-routed `Rend Armor Mult +` enhancement into `canonical_stat::max_rend_mult`
- Converted `Max Rend Armor Multiplier` lab from raw `level` to resolved additive contribution `0.25 x level`
- Kept module-substat contribution as pct bonus applied to the 8x base cap before enhancement

## Verification
- Targeted test passes for the corrected formula
- Regenerated max progression output publishes:
  - `canonical_stat::max_rend_mult = 9.68`
- Contributor trace now shows explicit resolved contributors:
  - lab `Max Rend Armor Multiplier = 0.0`
  - enhancement `Rend Armor Mult + = 1.21`

## Known unrelated issue
`tests/test_perk_scaling.py::test_farming_survivability_compare_respects_perk_bans` remains an unrelated pre-existing preset-name mismatch and was not changed in this patch.
