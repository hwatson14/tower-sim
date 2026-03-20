# Formula-First Storage Policy

Canonical storage rule:

1. Prefer a **formula/generator surface** when the source-backed rule is exact and reproduces the full ladder without ambiguity.
2. Retain explicit row tables as **materialized audit views** when they are useful for human browsing, row-by-row verification, or when the source only publishes rows/checkpoints.
3. Keep explicit tables as canonical only when the surface is irregular, nonlinear, conflict-ridden, or source-published purely as rows.
4. Never replace a table with a generator unless the generator exactly reproduces the verified values.

Canonical storage locations:
- `kb/formulas/tables/canonical-formula-registry.csv` = master registry of exact generators
- `kb/formulas/tables/formula-derived-surface-registry.csv` = mapping from generator to retained materialized view
- domain tables remain in place for audit/human browse unless explicitly deprecated


## Derived view location

When an explicit row table is no longer primary canon, move it under `kb/<domain>/derived/materialized/`. Keep domain-local discoverability, but make the canonical/derived distinction visually obvious.
