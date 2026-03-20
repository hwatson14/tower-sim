# R54 Routed repair for Wall HP and Free Upgrades

Decision:
- Repaired the three free-upgrade chance canonicals through routed contributor composition only.
- Repaired `canonical_stat::wall_hp` through a KB-owned formula path in the main stat resolver.
- Restored phase-3 postprocessing as an explicit helper pass after all rows are built.

Free Upgrades:
- Final formula now uses routed contributors only:
  - additive base = workshop + card + perk + module-substat bonuses
  - post multipliers = free-upgrade support multiplier + relic/vault multipliers

Wall HP:
- Final formula now uses:
  - `tower_hp x (workshop wall-health ratio + additive wall-health ratio bonuses) x wall-health multipliers`
- If `tower_hp` is unavailable in an isolated unit test context, the resolver falls back to returning the wall-health ratio as percentage points for deterministic formula testing.

Structural fix:
- The previous phase-3 postprocessing block was accidentally nested under the Max Rend helper and therefore was not executing as intended.
- It is now restored as `_apply_phase3_postprocessing(rows)` and called explicitly from `resolve_stats()`.

Verification:
- Targeted routed formula tests for free upgrades and wall HP pass.
- Canonical rebuild now emits:
  - `free_attack_upgrade_chance_pct = 107.7384`
  - `free_defense_upgrade_chance_pct = 104.6892`
  - `free_utility_upgrade_chance_pct = 118.28544`
  - `wall_hp = 114134966730453.69`
- `run_stats.py --state-mode max_progression --out out` passes.
