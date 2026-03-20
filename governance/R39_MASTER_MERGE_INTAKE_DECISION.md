# R39 intake decision: tower_stat_calc_r39_max_rend_fix

## Intake classification
- Class B: verified defect fix
- Class E residues present: alternate outputs, caches, side paths, and package framing regressions

## Accept
- Exact Max Rend correction slice only
- Merge protocol embedded into repo root as `TOWER_MASTER_MERGE_PROTOCOL.md`

## Quarantine
- `governance/R38_WORKSHOP_FINAL_DEFECT_PATCH.md`
- `governance/R39_MAX_REND_CORRECTION.md`
- `out_r38_check/**`, `out_r39_check/**`, `out_r39_check2/**`

## Reject
- Intake manifest/readme framing regressions
- `run_stats.py` regression removing optimizer output
- Free-upgrades changes bundled into this intake but out of scope for the named fix
- Wholesale package replacement

## Accepted files and slices
- `compilers/stat_input_compiler.py`: route Max Rend Armor Multiplier lab to `canonical_stat::max_rend_mult`, add alias support, add resolved-value lab formula, dual-route enhancement to max-rend surface
- `config/destination_formula_ledger.yaml`: add `canonical_stat::max_rend_mult` ledger entry
- `engine/stat_engine.py`: add exact phase-3 max-rend formula application
- `kb/global-rules/contracts/canonical-stats.yaml`: add `max_rend_mult`
- `tests/test_perk_scaling.py`: add focused max-rend formula test

## Verification required
- `pytest -q`
- `python run_stats.py`
- regenerated `out/`

## Notes
This intake was not admissible wholesale. Only the minimal defect-fix slice was merged into the cleaned baseline.
