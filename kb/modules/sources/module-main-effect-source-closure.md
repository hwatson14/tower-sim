# Module main-effect source closure

Status: partially closed for simulator use.

What is source-backed in the active bundle:
- `module-main-effect-bases.csv` provides rarity baselines by slot family.
- `module-main-effect-bands.csv` provides additive level increment bands by slot family.
- `module-main-effect-total-multipliers.csv` is promoted from the Effective Paths structured export and gives the computed total multiplier by rarity, level, and slot.
- The live wiki confirms module types, rarity progression limits, and the fact that leveling improves main stats, but it does not expose the full numeric main-effect ladder directly on the module page.

Boundary:
- Main-effect numerics are now treated as structured simulator canon sourced from the bundled Effective Paths export, not as directly row-verified live-wiki values.
- Unique effects and substats remain separately sourced.
- Module economy and reroll numerics are not implied by this closure note; Pack14 prep keeps those surfaces separately classified so workbook-derived helper ladders are not accidentally promoted into cost canon.
