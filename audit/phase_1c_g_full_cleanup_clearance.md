# Phase 1C.G Full Cleanup Pass (Option 2) — Canonical Ownership Re-Gate

## 1. Files inspected
- `tower_sim/engines/stat_input_compiler.py`
- `tower_sim/engines/survivability_pipeline.py`
- `tower_sim/engines/combat_stat_derivation.py`
- `tower_sim/loaders/ep_export_loader.py`
- `audit/phase_1c_f_runtime_alias_clearance.md`
- `audit/reference/tower_sim_3_handover/towersim_static_ledger_latest.csv`
- `audit/reference/tower_sim_3_handover/towersim_static_ledger_naming_contract_v1_10.md`

## 2. Cleanup actions completed in code
1. Anchored survivability baseline ownership to canonical static compiler surfaces (`compile_baseline_account_stat_inputs`, `compile_baseline_gem_respec_stat_inputs`) instead of local base stat construction.
2. Removed survivability-local base stat constructor path that previously wrote static start-of-run values (including `wall_regen`) in a domain pipeline.
3. Preserved loadout pipeline behavior while making static baseline ownership explicit in one canonical surface.
4. Kept alias normalization non-owning: `defense_percent -> defense_pct`, `rapid_fire_duration -> rapid_fire_duration_seconds` (loader-level aliasing only).

## 3. Deterministic clearance gate re-run (focused set)
Gate criteria used (unchanged):
- no runtime leakage as owner,
- no ambiguity in semantic mapping,
- no unresolved alias dependency,
- canonical static owner visible in `stat_input_compiler.py` path.

| identifier | canonical owner present | runtime owner writes present | alias dependency unresolved | gate result | promotion |
|---|---|---|---|---|---|
| `attack` | no canonical static stat-id owner (runtime/domain term) | yes (runtime combat usage) | no | blocked | no |
| `damage` | partial (`tower_damage` canonical; bare `damage` mixed semantic label) | yes (runtime combat usage) | no | blocked | no |
| `wall_regen` | yes (`stat_input_compiler.py` canonical static write) | no static-owner writes in survivability pipeline after cleanup | no | cleared | yes |
| `defense_percent` | alias only to `defense_pct` | no | no | cleared_non_owning_alias | no |
| `rapid_fire_duration` | alias only to `rapid_fire_duration_seconds` | no | no | cleared_non_owning_alias | no |

## 4. Ownership-ready promotions after re-gate
Promoted in this pass:
- `wall_regen` (canonical owner retained in `stat_input_compiler.py`; survivability runtime path now consumer/loadout-only for this stat input ownership boundary).

Not promoted:
- `attack`, `damage` remain mixed runtime/domain semantics and require explicit split contract before deterministic ownership promotion.
- `defense_percent`, `rapid_fire_duration` remain non-owning aliases by contract.

## 5. Remaining blockers (for next pass)
1. Explicit split contract for bare `attack` (enemy/boss runtime field) vs canonical player-facing static stat names.
2. Explicit split contract for bare `damage` vs canonical `tower_damage` and runtime wave/enemy damage labels.
3. Keep diagnostics/test/report symbols excluded from ownership candidate set.

## 6. Exact files changed
- `tower_sim/engines/survivability_pipeline.py`
- `audit/phase_1c_g_full_cleanup_clearance.md`

## 7. Stop/continue recommendation
Continue to Phase 1C.H only for `attack`/`damage` split-contract finalization; do not promote either identifier until split ownership is encoded and runtime-only labels are formally excluded from canonical ownership scope.
