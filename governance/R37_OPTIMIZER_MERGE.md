# R37 Optimizer Merge

## What was merged
- `optimizer/scorer.py` — v3 composite score functions (eHP, eDamage, eEcon)
- `optimizer/path_ranker.py` — greedy lab path ranker
- `optimizer/ACCURACY.md` — EP comparison methodology and accuracy report
- `tests/test_optimizer.py` — 15 tests, all passing
- Integration: `run_stats.py` imports scorer and writes `out/optimizer_scores.json`

## v3 expansions over original v2

### eHP (unchanged — EP-verified)
Formula: `(tower_hp * (wall_ratio*wall_fort + max_recovery*recovery_mult) + def_abs) * def_pct * cf * pbh`
Score: 200.12q. Lab path matches EP 14/15 steps.

### eDamage (expanded from v2)
- Added: shock expected-value multiplier (chance × multiplier from resolved mechanic_params)
- Score: 5.86q → 6.23q
- Still missing: UW additive damage channels (DW, CL, SM, ILM) which require boss-specific scaling models

### eEcon (expanded from v2)
- Added: Spotlight coin bonus, Death Wave coin bonus, Critical Coin card bonus, Wave Skip chance
- Score: 392.84M → 1.12B (2.85× increase from 4 new terms)
- Still missing: kill-source attribution weighting for SL/DW/BH channels

## Test results
- 15/15 optimizer tests pass
- 116/119 full suite pass (3 pre-existing test_smoke authoring failures)
- Pipeline rebuild: clean

## Architecture notes
- Scorer reads statbook rows via `_get()` helper — pure function, no side effects
- Path ranker accepts a `run_pipeline` callback — can work with any stat engine pipeline
- Optimizer is output-only in run_stats.py — does not affect statbook or EP compare
