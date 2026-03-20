# Final Audit Summary

This is the current clean working handover summary for the KB + stat calculator baseline.

## Totals
- Calculated stats: 379
- Sanity issues: 0

## Status counts
- resolved: 188
- unmapped: 191

## Verification status counts
- publishable: 188
- trace_only: 191

## KB alignment counts
- None: 379

## EP compare counts
- None: 352
- matched_exact: 14
- non_comparable: 4
- matched_close: 8
- non_numeric_compare: 1

## Cleanup actions
- standardized the shipped canonical artifact path to out/
- removed shipped output/ duplicate artifacts
- removed root clutter, test logs, and __pycache__ directories
- made tests write to temporary output directories instead of the repo root
- switched default run_stats handover behavior to max_progression -> out/
- relativized embedded package paths in shipped output JSON artifacts
- carried forward audit-rail governance and integrated v100 calculator improvements

## Release note
This is a clean working handover baseline for KB and stat-calculator use. Package hygiene is aligned, but broad external numeric validation remains incomplete.
