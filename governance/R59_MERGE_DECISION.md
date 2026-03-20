# R59 Merge Decision

Accepted slices:
- scenario/timing ownership split (`engine/scenario_engine.py`, `engine/timing_engine.py`)
- boss-wave runtime contract consumption rewiring
- optimizer timing-owner consumption update
- supporting docs, governance notes, and targeted tests
- retirement of legacy `engine/scenario_invariant_engine.py` and its test

Rejected / excluded:
- `__pycache__` artifacts
- `.pytest_cache` artifacts
- generated outputs bundled in intake

Verification performed:
- targeted scenario/timing/progression test tranche
- canonical rebuild via `python run_stats.py --state-mode max_progression --out out`

Open items:
- combat runtime gaps intentionally still open per tranche notes: orb cadence, OA electron cadence, boss contact timing.
