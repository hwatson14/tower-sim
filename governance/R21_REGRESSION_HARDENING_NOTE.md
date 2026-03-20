# R21 Regression Hardening

## Purpose
Hardening pass over the integrated v100 baseline focused on possible regressions introduced during R20 integration.

## Exact regression candidate addressed
- Restored `contributor_consumption` extraction and emission in `run_stats.py` line-by-line verification generation.

## Why restored
Raw v100 carried generator logic to parse notes like `Consumed X/Y contributors` and attach structured metadata. R20 had dropped that logic. The metadata was not visible in the shipped output snapshot, but the code-path capability itself was a real regression risk.

## Result after restore
- `output/line_by_line_verification.json` now emits `contributor_consumption` on 32 rows.
- Rows with partial consumption automatically add `unconsumed_contributor_present` to issues.

## Example emitted row
- `canonical_stat::tower_range_m` -> consumed 2/2 contributors

## What was not changed in this pass
- no new calculator mechanic formulas
- no EP registry or helper-plane changes
- no optimiser contract widening
- no package cleanup/handover hygiene fixes yet

## Current position
The integration still inherits raw v100 packaging defects and canonical-path confusion. This pass hardens the integration against a narrow metadata regression only.
