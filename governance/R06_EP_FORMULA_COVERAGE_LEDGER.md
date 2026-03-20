# R06 EP Formula Coverage Ledger

This ledger answers three different questions separately:

- Is an EP formula/extract entry present inside the calculator KB?
- Is there high-confidence evidence that the calculator implements or actively compares that formula?
- Is there evidence that the formula is wired to a current calculator output or EP compare row?

This pass is deliberately conservative. A formula is marked `compare_mapped` only when there is a high-confidence destination mapping into the current `output/ep_oracle_compare.json` surface set. Everything else remains `kb_registry_only` unless stronger wiring evidence is found.

## Totals

- EP mechanics entries inventoried: **91**
- High-confidence compare-mapped mechanics: **11**
- Registry-present but not proven implemented/wired mechanics: **80**
- Stat/helper definition entries inventoried: **22**

## Direct answer

- The calculator does **not** currently have proof that all EP formulas are implemented.
- The calculator does **not** currently have proof that all EP formulas are wired into emitted outputs.
- What is proven is narrower: the fresher EP mechanics registry is present in the calculator KB, and a bounded subset of EP formulas are actively used in current compare rows.

## High-confidence compare-mapped mechanics

- `EPD_ASPD` -> `canonical_stat::tower_attack_speed`
- `EPD_BSC` -> `canonical_stat::tower_bounce_shot_chance_pct`
- `EPD_BST` -> `canonical_stat::tower_bounce_shot_targets`
- `EPD_DPM` -> `canonical_stat::tower_damage_per_meter_multiplier`
- `EPD_RANGE` -> `canonical_stat::tower_range_m`
- `EPD_RFC` -> `canonical_stat::tower_rapid_fire_chance_pct`
- `EPD_RFD` -> `canonical_stat::tower_rapid_fire_duration_seconds`
- `EPC_CPK` -> `canonical_stat::coin_kill_multiplier`
- `EPH_HEALTH` -> `canonical_stat::tower_hp`
- `EPH_MAX_RCVR` -> `canonical_stat::max_recovery_multiplier`
- `EPH_REGEN` -> `canonical_stat::tower_regen`

## Interpretation

- Presence in the copied-forward EP registry supports enrichment and verification.
- Compare-mapped entries show active calculator use or active EP validation wiring.
- Registry-only entries should be treated as **known EP knowledge not yet proven calculator-implemented or calculator-wired**.
