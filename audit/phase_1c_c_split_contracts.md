# Phase 1C.C Split-Contract Definitions for Gated Identifiers

## 1. Inputs inspected
- `audit/phase_1c_b_blocker_resolution.md`
- `audit/phase_1c_a_staged_ownership_audit.md`
- `audit/phase_1b_normalized_namespace.md`
- `audit/reference/tower_sim_3_handover/towersim_static_ledger_latest.csv`
- `audit/reference/tower_sim_3_handover/towersim_static_ledger_naming_contract_v1_10.md`
- `audit/reference/tower_sim_3_handover/towersim_v1_handover_pack.md`
- `legacy/governance_handoff/CODEX_HANDOFF_V1_FULL.md`, `legacy/governance_handoff/STATUS_V1.yaml`, `CONTRACT.md`

## 2. Blocker portfolio summary
- Total gated identifiers: **17**
- `ambiguous_semantics`: 4
- `mixed_stage`: 4
- `report_only_leakage`: 2
- `runtime_leakage`: 7

## 3. Split-contract table
| repo_name | blocker_type | proposed_contract | clearance_criteria | confidence |
|---|---|---|---|---:|
| `attack` | mixed_stage | Static owner must be asserted in canonical static layer; runtime/report surfaces for `attack` are consumers only. | (1) exactly one static producer file, (2) no runtime mutation semantics in owner, (3) explicit consumer-only note for runtime/report paths. | 8 |
| `boss_survivability` | runtime_leakage | `boss_survivability` remains runtime-scoped unless a static ledger-backed contributor/target mapping is explicitly proven. | (1) ledger linkage proof, (2) static owner evidence, (3) runtime symbol renamed or explicitly marked state-only in planning docs. | 7 |
| `boss_survivability_invalid` | runtime_leakage | `boss_survivability_invalid` remains runtime-scoped unless a static ledger-backed contributor/target mapping is explicitly proven. | (1) ledger linkage proof, (2) static owner evidence, (3) runtime symbol renamed or explicitly marked state-only in planning docs. | 7 |
| `damage` | mixed_stage | Static owner must be asserted in canonical static layer; runtime/report surfaces for `damage` are consumers only. | (1) exactly one static producer file, (2) no runtime mutation semantics in owner, (3) explicit consumer-only note for runtime/report paths. | 8 |
| `death_wave_cooldown` | runtime_leakage | `death_wave_cooldown` remains runtime-scoped unless a static ledger-backed contributor/target mapping is explicitly proven. | (1) ledger linkage proof, (2) static owner evidence, (3) runtime symbol renamed or explicitly marked state-only in planning docs. | 8 |
| `death_wave_damage` | runtime_leakage | `death_wave_damage` remains runtime-scoped unless a static ledger-backed contributor/target mapping is explicitly proven. | (1) ledger linkage proof, (2) static owner evidence, (3) runtime symbol renamed or explicitly marked state-only in planning docs. | 8 |
| `death_wave_quantity` | runtime_leakage | `death_wave_quantity` remains runtime-scoped unless a static ledger-backed contributor/target mapping is explicitly proven. | (1) ledger linkage proof, (2) static owner evidence, (3) runtime symbol renamed or explicitly marked state-only in planning docs. | 8 |
| `defense_pct` | ambiguous_semantics | `defense_pct` must be semantically split into non-overlapping concepts before ownership assignment. | (1) concept split spec, (2) ledger mapping per split, (3) migration plan that avoids silent behavior changes. | 8 |
| `defense_percent` | ambiguous_semantics | `defense_percent` must be semantically split into non-overlapping concepts before ownership assignment. | (1) concept split spec, (2) ledger mapping per split, (3) migration plan that avoids silent behavior changes. | 8 |
| `health` | mixed_stage | Static owner must be asserted in canonical static layer; runtime/report surfaces for `health` are consumers only. | (1) exactly one static producer file, (2) no runtime mutation semantics in owner, (3) explicit consumer-only note for runtime/report paths. | 8 |
| `package_chance` | ambiguous_semantics | `package_chance` must be semantically split into non-overlapping concepts before ownership assignment. | (1) concept split spec, (2) ledger mapping per split, (3) migration plan that avoids silent behavior changes. | 8 |
| `rapid_fire_duration` | ambiguous_semantics | `rapid_fire_duration` must be semantically split into non-overlapping concepts before ownership assignment. | (1) concept split spec, (2) ledger mapping per split, (3) migration plan that avoids silent behavior changes. | 8 |
| `survivability_loadout_unknown_card` | report_only_leakage | `survivability_loadout_unknown_card` is excluded from canonical ownership set and remains report/test diagnostic only. | (1) diagnostics-only confirmation, (2) no static ownership assertion. | 6 |
| `survivability_loadout_unsupported_card` | report_only_leakage | `survivability_loadout_unsupported_card` is excluded from canonical ownership set and remains report/test diagnostic only. | (1) diagnostics-only confirmation, (2) no static ownership assertion. | 6 |
| `test_boss_survivability` | runtime_leakage | `test_boss_survivability` remains runtime-scoped unless a static ledger-backed contributor/target mapping is explicitly proven. | (1) ledger linkage proof, (2) static owner evidence, (3) runtime symbol renamed or explicitly marked state-only in planning docs. | 7 |
| `validate_boss_survivability_spec` | runtime_leakage | `validate_boss_survivability_spec` remains runtime-scoped unless a static ledger-backed contributor/target mapping is explicitly proven. | (1) ledger linkage proof, (2) static owner evidence, (3) runtime symbol renamed or explicitly marked state-only in planning docs. | 7 |
| `wall_regen` | mixed_stage | Static owner must be asserted in canonical static layer; runtime/report surfaces for `wall_regen` are consumers only. | (1) exactly one static producer file, (2) no runtime mutation semantics in owner, (3) explicit consumer-only note for runtime/report paths. | 8 |

## 4. Resolution queues
### 4.1 needs_spec_first (8)
- `attack` (mixed_stage)
- `damage` (mixed_stage)
- `defense_pct` (ambiguous_semantics)
- `defense_percent` (ambiguous_semantics)
- `health` (mixed_stage)
- `package_chance` (ambiguous_semantics)
- `rapid_fire_duration` (ambiguous_semantics)
- `wall_regen` (mixed_stage)

### 4.2 needs_runtime_split_proof (7)
- `boss_survivability` (runtime_leakage)
- `boss_survivability_invalid` (runtime_leakage)
- `death_wave_cooldown` (runtime_leakage)
- `death_wave_damage` (runtime_leakage)
- `death_wave_quantity` (runtime_leakage)
- `test_boss_survivability` (runtime_leakage)
- `validate_boss_survivability_spec` (runtime_leakage)

### 4.3 exclude_permanently (2)
- `survivability_loadout_unknown_card` (report_only_leakage)
- `survivability_loadout_unsupported_card` (report_only_leakage)

## 5. Phase 1C.D entry criteria
A gated identifier may enter Phase 1C.D ownership assertion only when its queue-specific clearance criteria are fully met and documented with file-level evidence.
No ownership promotion is allowed by heuristic inference alone.

## 6. Exact files changed
- `audit/phase_1c_c_split_contracts.md`

## 7. Stop/continue recommendation
- Continue to Phase 1C.D only for identifiers that satisfy the split-contract clearance criteria; otherwise keep gated.
