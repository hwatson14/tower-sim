# R49 — UW Patch 2 Integration Restore and Validation

## Purpose
This patch is the second UW patch in the two-patch finish plan.

Patch 1 added the missing KB/runtime registry surfaces for the remaining unresolved UW rows.
Patch 2 restores the engine/compiler-side UW composition logic that must consume those new surfaces correctly across states.

## Why this patch is required
Patch 1 implemented new KB rows, but its `stat_input_compiler.py` regressed earlier UW fixes from R43/R44:
- Chrono Field duration lab routing reverted from `mechanic_param` back to `runtime_mechanic_param`
- module-substat UW routing reverted from canonical `mechanic_param::uw.*` buckets back to helper/runtime buckets
- perk routing for Golden Tower, Chain Lightning, Death Wave, and Spotlight reverted back to helper/runtime buckets
- IDS current-value preservation for UW tracks was removed, causing track ladders to be used instead of actual current values
- fractional UW IDS values were no longer normalized to percentage points

This patch restores those earlier fixes while retaining the new KB rows from Patch 1.

## Files in scope
- `models/account_state.py`
- `compilers/account_state_compiler.py`
- `compilers/stat_input_compiler.py`
- `engine/stat_engine.py`
- Patch 1 KB files already added in R47 remain part of the integrated state

## What Patch 2 restores
1. Keep new Patch 1 KB destinations for the newly-added UW rows.
2. Preserve IDS current-value routing for owned UW tracks.
3. Preserve fractional-to-pct normalization for UW IDS values.
4. Preserve canonical routing of UW-affecting module substats into `mechanic_param::uw.*`.
5. Preserve canonical routing of UW perk effects into `mechanic_param::uw.*` where those stats are meant to be state-queryable canonicals.
6. Preserve Chrono Field duration lab ownership on the canonical composed path.
7. Preserve state-aware UW resolver families in `engine/stat_engine.py` from R46.

## Acceptance criteria
1. No previously-fixed high-value UW stat should regress back to helper/runtime-only composition.
2. The 10 Patch 1 gap rows remain routed and mapped.
3. The combined patch compiles cleanly.
4. Merge thread must regenerate outputs in the full repo and verify:
   - actual-current UW values still match prior validated rows for GT, BH, CF, CL, DW
   - newly-added Patch 1 UW rows resolve in the final output surface
   - helper/runtime rows are not treated as canonical consumer answers

## Required post-merge validation
- regenerate `FINAL_ALL_CALCULATED_STATS.*`
- diff all `mechanic_param::uw.*` and `runtime_mechanic_param::uw.*` rows
- verify owned-state and no-perk/no-module state queries for the major UW stats
- explicitly verify the new Patch 1 rows are no longer `mapped_not_resolved`

## Specific note for AI merge thread
Do not treat Patch 1 as sufficient by itself. Patch 1 defined the missing KB surfaces, but Patch 2 is required to restore the canonical stateful consumption path. Merge Patch 2 on top of Patch 1 before evaluating UW correctness.
