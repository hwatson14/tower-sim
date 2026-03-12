# Phase 1C.F Runtime-Consumer Proof and Alias Finalization (Analysis Only)

## 1. Files inspected
- `audit/phase_1c_e_blocker_reduction.md`
- `audit/phase_1c_d_clearance_evidence.md`
- `audit/phase_1c_c_split_contracts.md`
- `audit/reference/tower_sim_3_handover/towersim_static_ledger_latest.csv`
- `audit/reference/tower_sim_3_handover/towersim_static_ledger_naming_contract_v1_10.md`
- `audit/reference/tower_sim_3_handover/towersim_v1_handover_pack.md`
- `CODEX_HANDOFF_V1_FULL.md`, `STATUS_V1.yaml`, `CONTRACT.md`
- Runtime evidence surfaces: `tower_sim/engines/{combat,combat_stat_derivation,stat_pipeline,survivability_pipeline,edamage_pipeline}`, `tower_sim/evaluators`, `tower_sim/run`.
- Static owner surfaces: `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py`, `tower_sim/loaders/ep_export_loader.py`.

## 2. Mixed-stage runtime consumer-only proof
Runtime overlap was re-evaluated with read/write separation. `runtime_write_refs` > 0 blocks promotion; read-only runtime references are treated as consumer evidence.

## 3. Alias-normalization finalization decisions
- `defense_percent` -> `defense_pct` (canonical target).
- `rapid_fire_duration` -> `rapid_fire_duration_seconds` (canonical target).
- Both aliases are treated as non-owning labels in ownership audits; canonical ownership remains with target stat identifiers.

## 4. Clearance gate re-run (same deterministic criteria)
| repo_name | ledger_target_match | reduction_action | static_owner_signals | runtime_files | runtime_read_refs | runtime_write_refs | report_test_hits | clearance_status | gate_reason | promotion |
|---|---|---|---:|---:|---:|---:|---:|---|---|---|
| `attack` | no | mixed-stage contract rechecked using read/write evidence | 2 | 7 | 8 | 3 | 12 | blocked | runtime_write_overlap_present; insufficient_ledger_support | no |
| `damage` | yes | mixed-stage contract rechecked using read/write evidence | 3 | 8 | 18 | 2 | 8 | blocked | runtime_write_overlap_present | no |
| `health` | yes | mixed-stage contract rechecked using read/write evidence | 3 | 3 | 3 | 0 | 6 | cleared | none | yes |
| `wall_regen` | yes | mixed-stage contract rechecked using read/write evidence | 3 | 4 | 14 | 5 | 22 | blocked | runtime_write_overlap_present | no |
| `defense_percent` | alias->defense_pct | alias finalized: `defense_percent` -> `defense_pct` (non-owning alias) | 2 | 0 | 0 | 0 | 3 | cleared | none | no |
| `rapid_fire_duration` | alias->rapid_fire_duration_seconds | alias finalized: `rapid_fire_duration` -> `rapid_fire_duration_seconds` (non-owning alias) | 1 | 0 | 0 | 0 | 1 | cleared | none | no |

## 5. Re-run outcome summary
- Focused identifiers assessed: **6**
- Promoted after deterministic re-run: **1**
- Still blocked (or non-owning aliases): **5**
- Promoted: `health`

## 6. Exact files changed
- `audit/phase_1c_f_runtime_alias_clearance.md`

## 7. Stop/continue recommendation
- Continue with a minimal ownership amendment for promoted mixed-stage identifiers only; keep aliases non-owning and excluded from promotion.
