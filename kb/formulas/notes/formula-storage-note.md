# Formula-first storage note

This note explains the package decision to keep exact formulas and generators in structured surfaces while retaining selective row tables only where they add real value.

## Summary
- formula surfaces are preferred where a mechanic is linear, exact, or compactly representable
- row tables are retained where the source is irregular, checkpoint-based, or easier to consume as explicit rows
- materialized row views are secondary to exact formula surfaces unless the package explicitly promotes them

## Design intent
- reduce row bloat
- make exact linear ladders easier to inspect
- keep explicit tables where the source is irregular or checkpoint-only
- separate canonical formulas from browse-oriented materialized views

## Additional exact-rule surfaces
The package also includes exact-rule formula surfaces for cases where a direct formula is cleaner than a long ladder and better matches ChatGPT retrieval.
