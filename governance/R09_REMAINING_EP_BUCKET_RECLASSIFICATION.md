# R09 remaining EP bucket reclassification
This iteration reclassified the remaining R07/R08 `no_current_calculator_surface_or_out_of_scope` EP mechanics into more truthful buckets.
## Outcome
- Helper formulas retained deliberately: 12
- Calculator destination defined but not emitted on current baseline: 3
## Reclassified formulas
- **EPC_BHCB** -> `calculator_destination_defined_not_emitted`. Evidence: statbook destination definition: uw.black_hole.coin_bonus_multiplier. Calculator has a destination definition for Black Hole coin bonus multiplier, but no current emitted publishable row on this baseline.
- **EPC_CARD_COINS** -> `retained_helper_formula`. Evidence: card coin multiplier helper. Economy helper for card coin multiplier; useful for optimizer/strategy/helper outputs even without a standalone canonical row.
- **EPC_CARD_EOM** -> `retained_helper_formula`. Evidence: enemy-balance/end-of-match card helper. Economy helper formula; useful for helper/strategy layer, not required as current canonical output.
- **EPC_CARD_WS** -> `retained_helper_formula`. Evidence: wave-skip card helper around runtime skip behavior. Wave-skip helper/aggregate formula; keep as helper even though only wave skip chance is currently surfaced.
- **EPC_DWCB** -> `calculator_destination_defined_not_emitted`. Evidence: statbook destination definition: uw.death_wave.coin_bonus_multiplier. Calculator has a destination definition for Death Wave coin bonus multiplier, but no current emitted publishable row on this baseline.
- **EPC_GCOMP** -> `retained_helper_formula`. Evidence: galaxy compressor package-time helper. Generator-helper formula for package timing/compression effects; useful for optimizer/helper layer, not current canonical output.
- **EPC_GTGC** -> `retained_helper_formula`. Evidence: related surface present: mechanic_param::uw_plus.golden_tower.golden_combo. Golden Combo economy helper built from GT duration and kill rate; retain as helper rather than a canonical stat.
- **EPC_MVN** -> `retained_helper_formula`. Evidence: related cooldown surfaces present; MVN folding not separately surfaced. Multiverse Nexus helper for cooldown folding/sync calculations; useful for optimizer/helper layer.
- **EPC_SLCB** -> `calculator_destination_defined_not_emitted`. Evidence: statbook destination definition: uw.spotlight.coin_bonus_multiplier. Calculator has a destination definition for Spotlight coin bonus multiplier, but no current emitted publishable row on this baseline.
- **EPD_AOE_CARD_BOOST** -> `retained_helper_formula`. Evidence: card-derived AoE boost helper only. Card-derived helper multiplier; useful for helper/strategy layer rather than core canonical output.
- **EPD_RANGEDPM** -> `retained_helper_formula`. Evidence: canonical_stat::tower_range_m + canonical_stat::tower_damage_per_meter_multiplier. Derived helper from range and DPM inputs; useful for optimizer/strategy but not a required standalone canonical output.
- **EPD_SUPERTOWER_BONUS** -> `retained_helper_formula`. Evidence: super tower card/lab effect helper. Super Tower helper formula; retain for helper plane/optimizer use rather than forcing a canonical stat surface.
- **EPD_SUPERTOWER_COOLDOWN** -> `retained_helper_formula`. Evidence: super tower cooldown helper. Super Tower cooldown helper; retain for helper plane/optimizer use rather than forcing a canonical stat surface.
- **EPD_UWCRITICAL** -> `retained_helper_formula`. Evidence: related crit inputs present; no standalone uw crit surface. Derived helper for ultimate-weapon crit modeling; useful for damage modeling but not a current standalone canonical output.
- **EPH_ARMOR** -> `retained_helper_formula`. Evidence: armor module factor already used in survivability compare work. Armor-assist/helper factor, not a standalone canonical stat surface; retain for compare/helper modeling.

## Interpretation
- The remaining bucket was not mostly “missing mechanics.” It split into a larger retained-helper set and a smaller destination-defined-but-not-emitted set.
- The three coin-bonus formulas (BHCB, DWCB, SLCB) are the clearest candidates for future helper/output exposure because calculator destination definitions already exist.
- The other formulas are useful helper/strategy/optimizer formulas and should stay in the calculator knowledge/helper plane rather than being forced into the canonical published stat plane.
