# Module main-effect formulas harvested from Effective Paths v5.00.01

These formulas are copied from workbook defined names and interpreted into KB-ready form.

## Workbook-defined lambdas

### MODSTAT_CANNON
`LAMBDA(rarity, level, ROUND((VLOOKUP(SPLIT(rarity, " "), MOD_BASE_STAT_ARRAY, 2, false) + SUMPRODUCT(IF(level>MOD_STEPS_INCREASE_NEXT, MOD_STEPS_INCREASE_NEXT-MOD_STEPS_INCREASE, IF(level<MOD_STEPS_INCREASE, 0, level-MOD_STEPS_INCREASE)), MOD_CANNON_INCREASE_ARRAY)) * IF(RIGHT(rarity, 1) = "*", 1 + MID(rarity, 11, 1) * 0.04, 1) + 1, 3))`

### MODSTAT_ARMOR
`LAMBDA(rarity, level, ROUND((VLOOKUP(SPLIT(rarity, " "), MOD_BASE_STAT_ARRAY, 3, false) + SUMPRODUCT(IF(level>MOD_STEPS_INCREASE_NEXT, MOD_STEPS_INCREASE_NEXT-MOD_STEPS_INCREASE, IF(level<MOD_STEPS_INCREASE, 0, level-MOD_STEPS_INCREASE)), MOD_ARMOR_INCREASE_ARRAY)) * IF(RIGHT(rarity, 1) = "*", 1 + MID(rarity, 11, 1) * 0.04, 1) + 1, 3))`

### MODSTAT_GENERATOR
`LAMBDA(rarity, level, ROUND((VLOOKUP(SPLIT(rarity, " "), MOD_BASE_STAT_ARRAY, 4, false) + SUMPRODUCT(IF(level>MOD_STEPS_INCREASE_NEXT, MOD_STEPS_INCREASE_NEXT-MOD_STEPS_INCREASE, IF(level<MOD_STEPS_INCREASE, 0, level-MOD_STEPS_INCREASE)), MOD_GENERATOR_INCREASE_ARRAY)) * IF(RIGHT(rarity, 1) = "*", 1 + MID(rarity, 11, 1) * 0.04, 1) + 1, 3))`

### MODSTAT_CORE
`LAMBDA(rarity, level, ROUND((VLOOKUP(SPLIT(rarity, " "), MOD_BASE_STAT_ARRAY, 5, false) + SUMPRODUCT(IF(level>MOD_STEPS_INCREASE_NEXT, MOD_STEPS_INCREASE_NEXT-MOD_STEPS_INCREASE, IF(level<MOD_STEPS_INCREASE, 0, level-MOD_STEPS_INCREASE)), MOD_CORE_INCREASE_ARRAY)) * IF(RIGHT(rarity, 1) = "*", 1 + MID(rarity, 11, 1) * 0.04, 1) + 1, 3))`

## KB interpretation

For slot `s` and rarity `r` at module level `L`:

- `base_s(r)` comes from `module_main_effect_base.csv`
- `band_add_s(L)` comes from summing the per-level increment bands
- `star_factor(r) = 1 + 0.04 * stars` for starred Ancestral modules, else `1`
- `total_multiplier_s(r, L) = ROUND((base_s(r_base) + band_add_s(L)) * star_factor(r) + 1, 3)`

Where starred Ancestral rarities use the plain `Ancestral` base row and then apply the star factor.

## Important caveat

This file reflects Effective Paths workbook logic, not a direct developer-published source. It is therefore high-value but still secondary to explicit game tables if those are ever obtained.
