# R36 Master Merge — Scenario + Progression + Economy + Capability

## Merge composition

This merge integrates 4 branches onto the R32 baseline:

| Source | Content | Lines changed |
|--------|---------|---------------|
| R32 baseline | Starting point — stat calculator + KB | — |
| Scenario invariant engine | 46-surface scenario-adjusted effects engine | +586 engine, +511 tests |
| R34 capability/environment tranche | 6 bool capability lab routes + BC reduction | ~30 compiler |
| R36 non-UW economy tranche | 5 economy lab routes + interest resolver + legacy CSV | ~50 compiler + ~20 engine + ~20 run_stats |
| Progression engine (r11/r5) | Boss-wave v1, workshop progression, recalc bridge | +1,490 engine (8 modules), +718 tests, +16 docs |

## Final stats

- Resolved canonical stats: 207 (up from 200 at R32)
- EP compare: 22 matched (14 exact + 8 close), 0 true mismatches
- Lab mapping: 58/212 (27.4%, up from 22.2% at R32)
- Total stat inputs: 541
- Statbook rows: 373
- Scenario engine surfaces: 46
- Progression engine modules: 8

## New lab routes added (R34 + R36)

### R34 — Capability/environment
- Extra Black Hole → capability.uw.black_hole.extra_black_hole
- Black Hole Disable Ranged Enemies → capability.uw.black_hole.disable_ranged
- Chain Lightning Shock → capability.uw.chain_lightning.shock
- Swamp Stun → capability.uw.poison_swamp.stun
- Missiles Explosion → capability.uw.smart_missiles.explosion
- Battle Condition Reduction → environment_param::bc.reduction.generic_pct
- Package After Boss → capability.recovery_package.after_boss

### R36 — Economy
- Cash / Wave → canonical_stat::cash_per_wave
- Interest / Wave → canonical_stat::interest_per_wave_pct
- Recovery Package Amount → canonical_stat::recovery_amount_pct
- Recovery Package Max → canonical_stat::max_recovery_multiplier

## Progression engine merge notes

Merged as **foundation** per MERGE_NOTES_FOR_AI.md constraints:
- Cherry-picked 8 new engine modules only
- Did NOT merge progression branch's stat_engine.py or stat_input_compiler.py (older than R32, missing perk fixes, integrality policy, R32 mechanic_param routes)
- Progression recalc bridge delegates to our R36 stat engine pipeline
- 27/28 progression tests pass (1 requires pytest tmp_path fixture)

## Test results

- 59/59 scenario invariant engine tests: PASS
- 2/2 R32 semantics tests: PASS
- 10/10 key smoke tests: PASS
- 27/28 progression engine tests: PASS (1 pytest-only)
- Full pipeline rebuild: CLEAN

## Still open (NOT in this merge)

- Workshop defects: free upgrades, bounce shot targets, max rend mult (separate thread)
- UW lab routing: 23 wiki-verified tables need registry pipeline binding (separate thread)
- Scope-tagging: 153 non-calculator-scope labs need diagnostic exclusion (separate thread)
- Scenario→Progression integration: wire scenario surfaces into boss_wave_engine (follow-on)
