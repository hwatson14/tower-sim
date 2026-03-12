# Phase 1C.E Blocker Reduction and Clearance Re-Run (Analysis Only)

## 1. Files inspected
- `audit/phase_1c_d_clearance_evidence.md`
- `audit/phase_1c_c_split_contracts.md`
- `audit/phase_1c_b_blocker_resolution.md`
- `audit/phase_1c_a_staged_ownership_audit.md`
- `audit/phase_1b_normalized_namespace.md`
- `audit/reference/tower_sim_3_handover/towersim_static_ledger_latest.csv`
- `audit/reference/tower_sim_3_handover/towersim_static_ledger_naming_contract_v1_10.md`
- `audit/reference/tower_sim_3_handover/towersim_v1_handover_pack.md`
- `CODEX_HANDOFF_V1_FULL.md`, `STATUS_V1.yaml`, `CONTRACT.md`

## 2. Focused blocker-reduction actions
### 2.1 Mixed-stage overlap contracts
- `attack`: static owner contract defined (static compile ownership only); runtime/report layers remain consumer-only.
- `damage`: static owner contract defined (static compile ownership only); runtime/report layers remain consumer-only.
- `health`: static owner contract defined (static compile ownership only); runtime/report layers remain consumer-only.
- `wall_regen`: static owner contract defined (static compile ownership only); runtime/report layers remain consumer-only.

### 2.2 Ambiguous semantic splits
- `defense_pct`: canonical target stat retained as ratio-style defense percent state.
- `defense_percent`: treated as alias label to canonical `defense_pct` (not separate canonical owner token).
- `package_chance`: canonical target stat retained; generic package labels must not be treated as owner aliases without mapping proof.
- `rapid_fire_duration`: treated as alias label requiring mapping to canonical `rapid_fire_duration_seconds`.

### 2.3 Diagnostic/test exclusions (kept excluded)
- `survivability_loadout_unknown_card` remains excluded from ownership promotion scope.
- `survivability_loadout_unsupported_card` remains excluded from ownership promotion scope.
- `test_boss_survivability` remains excluded from ownership promotion scope.

## 3. Clearance gate re-run (same deterministic gate)
| repo_name | ledger_target_match | reduction_action | static_hits | runtime_hits | report_hits | clearance_status | gate_reason | promotion |
|---|---|---|---:|---:|---:|---|---|---|
| `attack` | no | mixed-stage overlap contract defined: static owner required; runtime/report are consumer-only | 2 | 7 | 0 | blocked | runtime_overlap_present | no |
| `damage` | yes | mixed-stage overlap contract defined: static owner required; runtime/report are consumer-only | 4 | 9 | 1 | blocked | runtime_overlap_present | no |
| `health` | yes | mixed-stage overlap contract defined: static owner required; runtime/report are consumer-only | 3 | 4 | 2 | blocked | runtime_overlap_present | no |
| `wall_regen` | yes | mixed-stage overlap contract defined: static owner required; runtime/report are consumer-only | 4 | 5 | 1 | blocked | runtime_overlap_present | no |
| `defense_pct` | yes | semantic clarified: canonical target_stat for defense percentage ratio state | 0 | 4 | 0 | blocked | no_static_owner_signal; runtime_overlap_present | no |
| `defense_percent` | alias->defense_pct | semantic split defined: treat as alias to `defense_pct` (percent label vs canonical pct stat) | 2 | 0 | 1 | blocked | requires alias normalization implementation before ownership promotion | no |
| `package_chance` | yes | semantic clarified: canonical target_stat `package_chance`; no fallback to generic package labels | 0 | 2 | 0 | blocked | no_static_owner_signal; runtime_overlap_present | no |
| `rapid_fire_duration` | alias->rapid_fire_duration_seconds | semantic split defined: map name to canonical duration target `rapid_fire_duration_seconds` | 1 | 0 | 0 | blocked | requires alias normalization implementation before ownership promotion | no |

## 4. Re-run outcome summary
- Focused identifiers assessed: **8**
- Promoted after deterministic re-run: **0**
- Still blocked: **8**
- Remaining blocker `alias_dependency`: 2
- Remaining blocker `mixed_stage`: 4
- Remaining blocker `runtime_leakage`: 2

## 5. Exact files changed
- `audit/phase_1c_e_blocker_reduction.md`

## 6. Stop/continue recommendation
- Continue blocker reduction in Phase 1C.F; no ownership promotion is safe yet because runtime overlap and alias-dependency blockers remain.
