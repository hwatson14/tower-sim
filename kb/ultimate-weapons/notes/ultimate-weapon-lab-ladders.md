# UW Lab Ladders

Status: expanded with stronger verified quantitative surfaces.

This file is the KB bridge between raw lab tables and reasoning. It focuses on the Ultimate Weapons (UWs) where exact lab ladders materially affect economy or survivability choices.

## Verified exact ladders now present in quant_tables

### Golden Tower
- `wiki_gt_bonus_levels_full.csv`
- `wiki_gt_duration_levels_full.csv`

Reasoning note: Golden Tower is one of the cleanest examples of a lab pair where both ladders are easy to model directly. Bonus scales additively by +0.15 per lab level to a total of +3.75, and duration scales +1 second per level to a total of +20 seconds. These ladders matter because Golden Tower value is not just raw multiplier. It is overlap-weighted by BH, SL, DW, and Golden Bot timing.

### Black Hole
- `wiki_bh_coin_bonus_levels_1_17_verified.csv`

Reasoning note: Black Hole Coin Bonus is a high-leverage economy ladder because it multiplies kills inside BH rather than Black Hole-only kills. The current KB stores a verified slice through level 17, which is already enough to model the steep early and mid ladder correctly.

### Spotlight
- `wiki_spotlight_coin_bonus_levels_full.csv`

Reasoning note: Spotlight Coin Bonus should never be valued as a flat multiplier. It is a coverage-weighted multiplier. Angle, count, rotation and overlap with GT/Black Hole windows determine realised value.

### Death Wave
- `wiki_dw_health_levels_full.csv`
- `wiki_dw_coin_bonus_levels_full.csv`
- `wiki_dw_cell_bonus_levels_full.csv`

Reasoning note: DW is not one ladder. It is three different optimisation ladders living under one weapon: survivability through health gain, coin economy, and lab economy through cells. These need to be separated in reasoning.

## KB strategy rules

1. **Economy ladders are effective-value ladders**
   Golden Tower, Black Hole, Spotlight and Death Wave coin labs must be evaluated through realised uptime, realised tagging, and overlap.

2. **Survivability ladders are breakpoint ladders**
   Death Wave Health and GT Duration are not smooth value curves in practice. They can push specific run states over key thresholds.

3. **Partial is better than fake completeness**
   The KB now stores exact ladders where verified. Missing ladders should remain partial until extracted cleanly.
