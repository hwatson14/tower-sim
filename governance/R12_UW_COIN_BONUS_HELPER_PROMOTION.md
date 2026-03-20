# R12 UW Coin Bonus Helper Promotion

Promote and expose resolved helper/runtime surfaces for the three UW coin bonus lab multipliers.

## Added/updated
- Added exact ladder rows to `kb/labs/tables/lab-values.csv` for Black Hole, Spotlight, and Death Wave Coin Bonus labs.
- Added lab application registry rows for these three labs.
- Routed these labs to `runtime_mechanic_param` destinations in `compilers/stat_input_compiler.py`.
- Added `helper_formula` destination formula ledger entries for the three emitted rows.

## Emitted helper rows
- `runtime_mechanic_param::uw.black_hole.coin_bonus_multiplier` = x11 (final_value=11.0)
- `runtime_mechanic_param::uw.death_wave.coin_bonus_multiplier` = x2.5 (final_value=2.5)
- `runtime_mechanic_param::uw.spotlight.coin_bonus_multiplier` = x3 (final_value=3.0)

## Design note
These rows are emitted in the runtime/helper plane, not promoted into the core canonical stat plane. They are persistent lab multipliers that are directly useful for optimizer/econ analysis and for later helper-plane expansion.
