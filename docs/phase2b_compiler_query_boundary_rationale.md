# Phase 2B — Compiler/query boundary rationale

## Change classification

- **Routing correction**: moved Query Engine-owned state-mode policy, perk query semantics, and query-routing registry loaders out of `compilers/stat_input_compiler.py` and into canonical Query Engine owner modules.
- **Test correction**: added targeted regressions that prove the compatibility entrypoint still delegates to the new owners without changing runtime results.

## Updated boundary

`compilers/stat_input_compiler.py` remains the compatibility entrypoint that assembles `StatInput` rows from IDS/account inputs. It still owns row creation, account-state decoding, preset selection, and value materialization.

The Query Engine now owns the parts of the seam that govern which compiled rows are publishable and how query-facing surfaces are prepared:

- `engine/query_state_mode_policy.py` owns state-mode contract loading, alias normalization, support metadata, and the final row filter used to publish only surfaces allowed for a requested state mode.
- `engine/query_perk_compiler.py` owns perk-selection semantics, perk-lab scaling policy, and operation-to-value typing for run-selected perk surfaces.
- `engine/query_routing.py` owns the query-routing registries used to turn card effects, lab application targets, and theme-song helper surfaces into published destinations.

## What did not move

To stay inside the approved tranche boundary, this extraction does **not** redesign `StatInput`, rewrite perk formulas, or refactor unrelated family compilation sections. `compile_stat_inputs()` still calls the same compatibility path and still emits the same runtime rows for the covered behaviors.

## Regression anchors

The moved behaviors remain anchored by targeted regressions in:

- `tests/test_state_mode_contracts.py`
- `tests/test_perk_scaling.py`
- `tests/test_r86_completion.py`
