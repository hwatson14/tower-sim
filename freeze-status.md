# Freeze Status

## Current baseline
This package is the current **pre-merge cleaned baseline** derived from `tower_stat_calc_r37_final.zip`.

## Freeze intent
Freeze the baseline package shape, authority claims, and onboarding surfaces before merging new work.

## Frozen truths
- `python run_stats.py` is the canonical rebuild path.
- `out/` is the canonical shipped output bundle.
- The package contains KB + calculator + perk timeline + progression foundation + downstream optimizer support.
- Progression foundation is merge-ready.
- Final scenario-runtime closure is still open.

## Safe cleanup applied
- Added missing control-plane entry files referenced by `manifest.json` and `readme.md`.
- Corrected package description surfaces to reflect actual scope.
- Preserved runtime/code behavior.

## Not changed in this cleanup
- No calculator formulas changed.
- No engine behavior changed.
- No package directories were moved.
- No docs were rewritten to overstate completion.
