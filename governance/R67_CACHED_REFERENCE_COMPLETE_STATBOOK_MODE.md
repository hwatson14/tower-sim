# R67 Cached Reference Complete StatBook Mode

## Purpose
Add a guarded bridge mode that can return a complete statbook without calling full-safe `resolve_stats(...)` on eligible closed-subset paths, by overlaying parity-proven candidate rows onto a caller-supplied cached full reference statbook.

## Scope
- New bridge mode: `incremental_cached_publish_guarded`
- Cache validation limited to non-mutated workshop-level equality for provided cached reference context
- No new formula logic
- No broader runtime publication beyond existing skip outputs

## Safety contract
- Fail closed to `full_safe` if cache is missing or invalid
- Only use existing `IncrementalSubsetExecutor` candidate rows
- Preserve non-mutated surfaces from cached full reference statbook
- Keep unsupported mutations on ordinary fallback path

## Limitation
This tranche does not prove cache validity beyond workshop-level continuity for non-mutated keys supplied in the request. Stronger cache fingerprinting remains future work.
