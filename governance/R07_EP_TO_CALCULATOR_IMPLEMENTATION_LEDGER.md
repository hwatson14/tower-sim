# R07 EP-to-calculator implementation ledger

This ledger classifies the **R06 registry-only EP mechanics** into conservative implementation buckets against the calculator baseline.

## Verdict

This is still **not** full EP implementation coverage. It is a fail-closed classification of what appears implemented under calculator surfaces, what is helper-only, and what has no current calculator surface evidence.

## Summary

- calculator_equivalent_present_uncompared: 35
- cross_section_duplicate_reference: 13
- needs_manual_classification: 2
- no_current_calculator_surface_or_out_of_scope: 15
- verification_only_helper_or_aggregate: 15

## Bucket meanings

- `calculator_equivalent_present_uncompared`: a clear calculator surface exists, but this EP formula is not yet proven as a one-to-one compared implementation row.

- `verification_only_helper_or_aggregate`: workbook helper or aggregate; useful for comparison/enrichment, not necessarily required as a standalone calculator output.

- `cross_section_duplicate_reference`: repeated helper/final-stat reference in another EP section; avoid double-counting implementation coverage.

- `no_current_calculator_surface_or_out_of_scope`: no clear current calculator output or current-scope implementation evidence.

- `needs_manual_classification`: conservative fallback where heuristics were insufficient.


## Key result

A meaningful subset of registry-only EP mechanics do have **clear calculator-equivalent surfaces**. But the majority remain either workbook-helper style formulas or have no current high-confidence calculator output/scope evidence. That means the calculator is **closer than the raw R06 ledger suggested**, but it is still not honest to call EP fully implemented or fully wired.
