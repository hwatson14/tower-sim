# Phase 1C.B Blocker Resolution Plan (Analysis Only)

## 1. Inputs inspected
- `audit/phase_1c_a_staged_ownership_audit.md`
- `audit/phase_1b_normalized_namespace.md`
- `audit/reference/tower_sim_3_handover/towersim_static_ledger_latest.csv`
- `audit/reference/tower_sim_3_handover/towersim_static_ledger_naming_contract_v1_10.md`
- `audit/reference/tower_sim_3_handover/towersim_v1_handover_pack.md`
- `legacy/governance_handoff/CODEX_HANDOFF_V1_FULL.md`, `legacy/governance_handoff/STATUS_V1.yaml`, `CONTRACT.md`
- Evidence scan: `tower_sim/**`, `tables/meta/registry/**`.

## 2. Blocker summary
- Gated identifiers reviewed: **17**
- `ambiguous_semantics`: 4
- `mixed_stage`: 4
- `report_only_leakage`: 2
- `runtime_leakage`: 7
- Candidates unblockable now (no runtime ambiguity after recheck): **0**
- Candidates still gated: **17**

## 3. Gated-candidate re-evaluation table
| repo_name | blocker_type | evidence_static | evidence_runtime | evidence_report | can_unblock_now | unblock_reason | confidence | next_phase_action |
|---|---|---|---|---|---|---|---:|---|
| `attack` | mixed_stage | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/registry/stat_registry.py` | `tower_sim/engines/combat/boss_survivability.py`, `tower_sim/engines/combat/combat_engine.py`, `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/survivability_pipeline.py` | — | no | requires explicit static-owner/runtime-consumer split assertion before admission | 8 | phase_1c_b_split_contract |
| `boss_survivability` | runtime_leakage | — | `tower_sim/engines/combat/__init__.py`, `tower_sim/engines/combat/boss_params_loader.py`, `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/survivability_pipeline.py` | `tower_sim/audit/status.py` | no | insufficient deterministic separation evidence | 7 | keep_gated |
| `boss_survivability_invalid` | runtime_leakage | — | `tower_sim/engines/combat_stat_derivation.py` | — | no | insufficient deterministic separation evidence | 7 | keep_gated |
| `damage` | mixed_stage | `tables/meta/registry/ep_formulas/mechanics_library.yaml`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/loaders/ep_export_loader.py`, `tower_sim/registry/stat_registry.py` | `tower_sim/engines/combat/boss_engine.py`, `tower_sim/engines/combat/boss_survivability.py`, `tower_sim/engines/combat/combat_engine.py`, `tower_sim/engines/combat_stat_derivation.py` | `tower_sim/audit/status.py` | no | requires explicit static-owner/runtime-consumer split assertion before admission | 8 | phase_1c_b_split_contract |
| `death_wave_cooldown` | runtime_leakage | `tower_sim/engines/stat_input_compiler.py` | `tower_sim/engines/survivability_pipeline.py`, `tower_sim/evaluators/max_wave.py` | — | no | requires explicit static-owner/runtime-consumer split assertion before admission | 8 | phase_1c_b_split_contract |
| `death_wave_damage` | runtime_leakage | `tower_sim/engines/stat_input_compiler.py` | `tower_sim/engines/survivability_pipeline.py` | — | no | requires explicit static-owner/runtime-consumer split assertion before admission | 8 | phase_1c_b_split_contract |
| `death_wave_quantity` | runtime_leakage | `tower_sim/engines/stat_input_compiler.py` | `tower_sim/engines/survivability_pipeline.py` | — | no | requires explicit static-owner/runtime-consumer split assertion before admission | 8 | phase_1c_b_split_contract |
| `defense_pct` | ambiguous_semantics | — | `tower_sim/engines/combat/boss_engine.py`, `tower_sim/engines/combat/boss_survivability.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/evaluators/max_wave.py` | — | no | semantic overload unresolved (same token implies multiple mechanics) | 8 | needs_semantic_split |
| `defense_percent` | ambiguous_semantics | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/loaders/ep_export_loader.py` | — | `tower_sim/audit/ep_export_final_stats_parity.py` | no | semantic overload unresolved (same token implies multiple mechanics) | 8 | needs_semantic_split |
| `health` | mixed_stage | `tower_sim/engines/stat_input_compiler.py`, `tower_sim/loaders/ep_export_loader.py`, `tower_sim/registry/stat_registry.py` | `tower_sim/engines/combat/combat_engine.py`, `tower_sim/engines/stat_pipeline.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/libs/wave_damage_strict.py` | `tower_sim/audit/ep_export_final_stats_parity.py`, `tower_sim/audit/wiring_health_check.py` | no | requires explicit static-owner/runtime-consumer split assertion before admission | 8 | phase_1c_b_split_contract |
| `package_chance` | ambiguous_semantics | — | `tower_sim/engines/combat/boss_engine.py`, `tower_sim/evaluators/max_wave.py` | — | no | semantic overload unresolved (same token implies multiple mechanics) | 8 | needs_semantic_split |
| `rapid_fire_duration` | ambiguous_semantics | `tower_sim/loaders/ep_export_loader.py` | — | — | no | semantic overload unresolved (same token implies multiple mechanics) | 8 | needs_semantic_split |
| `survivability_loadout_unknown_card` | report_only_leakage | — | `tower_sim/engines/combat_stat_derivation.py` | — | no | blocker persists | 6 | keep_gated |
| `survivability_loadout_unsupported_card` | report_only_leakage | — | `tower_sim/engines/combat_stat_derivation.py` | — | no | blocker persists | 6 | keep_gated |
| `test_boss_survivability` | runtime_leakage | — | — | `tower_sim/audit/status.py` | no | insufficient deterministic separation evidence | 7 | keep_gated |
| `validate_boss_survivability_spec` | runtime_leakage | — | `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/evaluators/max_wave.py` | — | no | insufficient deterministic separation evidence | 7 | keep_gated |
| `wall_regen` | mixed_stage | `tables/meta/registry/ep_formulas/mechanics_library_v0_7.yaml`, `tower_sim/engines/stat_input_compiler.py`, `tower_sim/loaders/ep_export_loader.py`, `tower_sim/registry/stat_registry.py` | `tower_sim/engines/combat/boss_survivability.py`, `tower_sim/engines/combat_stat_derivation.py`, `tower_sim/engines/survivability_pipeline.py`, `tower_sim/evaluators/max_wave.py` | `tower_sim/audit/ep_export_final_stats_parity.py` | no | requires explicit static-owner/runtime-consumer split assertion before admission | 8 | phase_1c_b_split_contract |

## 4. Deterministic blocker-resolution rules
1. For mixed-stage names, require a single static producer in `stat_input_compiler.py` (or registry/table source) plus explicit runtime-consumer-only evidence before admission.
2. For runtime leakage names, require zero authoritative ownership claims in combat/wave/run layers; these layers may consume but not own canonical static identifiers.
3. For ambiguous semantics names (`damage`, `defense_pct`, `package_chance`, etc.), require disambiguated semantic suffixes in planning docs before any ownership assertion.
4. Report/test-only symbols remain permanently excluded from canonical ownership scope.

## 5. Proposed Phase-1C.Amend candidate promotions
- None. All gated identifiers still require explicit split/semantic resolution before safe ownership admission.

## 6. Remaining hard blockers for Phase 1C.C
| repo_name | blocker_type | required_evidence_to_clear |
|---|---|---|
| `attack` | mixed_stage | single static owner + runtime-consumer-only proof |
| `boss_survivability` | runtime_leakage | proof of static ownership and runtime non-ownership |
| `boss_survivability_invalid` | runtime_leakage | proof of static ownership and runtime non-ownership |
| `damage` | mixed_stage | single static owner + runtime-consumer-only proof |
| `death_wave_cooldown` | runtime_leakage | proof of static ownership and runtime non-ownership |
| `death_wave_damage` | runtime_leakage | proof of static ownership and runtime non-ownership |
| `death_wave_quantity` | runtime_leakage | proof of static ownership and runtime non-ownership |
| `defense_pct` | ambiguous_semantics | semantic split plan with non-overlapping canonical names |
| `defense_percent` | ambiguous_semantics | semantic split plan with non-overlapping canonical names |
| `health` | mixed_stage | single static owner + runtime-consumer-only proof |
| `package_chance` | ambiguous_semantics | semantic split plan with non-overlapping canonical names |
| `rapid_fire_duration` | ambiguous_semantics | semantic split plan with non-overlapping canonical names |
| `survivability_loadout_unknown_card` | report_only_leakage | keep excluded; no ownership assertion needed |
| `survivability_loadout_unsupported_card` | report_only_leakage | keep excluded; no ownership assertion needed |
| `test_boss_survivability` | runtime_leakage | proof of static ownership and runtime non-ownership |
| `validate_boss_survivability_spec` | runtime_leakage | proof of static ownership and runtime non-ownership |
| `wall_regen` | mixed_stage | single static owner + runtime-consumer-only proof |

## 7. Exact files changed
- `audit/phase_1c_b_blocker_resolution.md`

## 8. Stop/continue recommendation
- Continue with blocker-resolution only; do not expand ownership assertions until split/semantic blockers are resolved.
