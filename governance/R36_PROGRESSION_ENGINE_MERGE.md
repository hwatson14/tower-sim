# R36 + Progression Engine Merge

## Merge summary

This merge integrates three branches into the R32+scenario baseline:

### R34 capability/environment tranche (from R36 bundle)
- Bool operation_type support for lab-application-registry enable/set_bool rows
- 6 capability/environment lab routes: Extra Black Hole, BH Disable Ranged, CL Shock, Swamp Stun, Missiles Explosion, BC Reduction

### R36 non-UW economy tranche
- 5 economy lab routes: Cash/Wave, Interest, Package After Boss, Recovery Amount, Recovery Max
- Interest-per-wave destination-specific resolver in stat_engine
- Legacy FINAL_ALL_CALCULATED_STATS CSV/JSON export mirrors

### Progression engine (prog_r5 → r11 bundle)
- 8 new engine modules (1,490 lines): boss_wave_engine, progression_state, progression_recalc_bridge, perk_timeline_state, workshop_progression_policy, wave_progression_policy, free_upgrade_generation_policy, scenario_runtime_inputs
- 8 new test files (718 lines), all passing
- 16 docs files covering architecture, formulas, gap ledger, readiness audit
- Deliberately did NOT merge prog's stat_engine.py or stat_input_compiler.py — those were older than R32 and lacked perk orb fix, integer_count_stat rounding, SPB integrality policy, slug fallbacks, and R32 mechanic_param lab routes

## Merge decisions

| Decision | Rationale |
|----------|-----------|
| R36 stat_input_compiler over prog's | R36 has R32 fixes + R34 bool support + R36 economy routes; prog's compiler predates R32 |
| R36 stat_engine over prog's | R36 has integer_count_stat rounding + interest resolver; prog's engine lacks these |
| Keep scenario_invariant_engine.py | Already merged in prior session; progression engine's scenario_runtime_inputs.py consumes its output |
| Progression recalc_bridge delegates to stat engine | Correct architecture: progression mutates workshop state, stat engine owns all formula resolution |

## Test results after merge
- 28/28 progression engine tests: PASS
- 59/59 scenario engine tests: PASS
- 2/2 R32 semantics tests: PASS
- 12/12 runnable smoke tests: PASS (3 pre-existing test authoring failures unrelated to merge)
- Full pipeline rebuild: CLEAN
- EP compare: 0 true mismatches, 14 exact + 8 close matches

## Baseline metrics
- Resolved stats: 207
- Total inputs: 541
- Lab mapping: 58/212 (27.4%)
- All other families: 97.5-100%
- Engine modules: 10 files, 3,174 lines
- Test files: 13 files, 3,052 lines
