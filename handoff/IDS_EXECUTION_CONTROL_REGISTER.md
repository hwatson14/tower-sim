# IDS Execution Control Register

Purpose: Codex-facing execution control plane derived from the normalized master bug register and raw discovery ledger.

Canonical preset contract:
- Tourney
- Farming
- Milestone
- Preset 4
- Preset 5

Primary evidence:
- `ids_pipeline_bug_ledger_v19.md`
- `ids_pipeline_normalized_master_register.md`

## Operating rules

1. Fix root causes in dependency order. Do not jump ahead to downstream cleanup.
2. No new local truth tables for presets, section specs, or runtime mode maps.
3. No fail-open fallbacks for missing/invalid preset-family state unless the tranche explicitly defines that behavior.
4. No synthetic namespaces in canonical artifacts.
5. Partial/selected-context artifacts must be explicitly labeled as partial.
6. Tests and fixtures must follow the canonical five-preset contract unless explicitly marked as transient-runtime tests.

## Status key

- **Decision required**
- **Schema required**
- **Codex-ready after dependency**
- **Codex-ready**
- **Post-contract cleanup**
- **Blocked**
- **Closed** = implementation complete in repo truth; merge may still be gated by required review.

## Tranche dependency spine

1. `TRANCHE_IDS_C1_CONTRACT_REGISTRY`
2. `TRANCHE_IDS_C5_STATE_SEMANTICS`
3. `TRANCHE_IDS_C2_RUNTIME_FIVE_PRESET`
4. `TRANCHE_IDS_C11_PERK_PRESET_CONTRACT`
5. `TRANCHE_IDS_C12_NAMESPACE_HYGIENE`
6. `TRANCHE_IDS_C10_CLEAN_SECTION_INGESTION`
7. `TRANCHE_IDS_C7_WSPLUS_TYPED_MODEL`
8. `TRANCHE_IDS_C8_UW_TYPED_TRACKS`
9. `TRANCHE_IDS_C9_BOT_TYPED_STATE`
10. `TRANCHE_IDS_C13_AUDIT_SURFACE_CONTRACTS`
11. `TRANCHE_IDS_C14_ARTIFACT_OUTPUT_CONTRACTS`
12. `TRANCHE_IDS_C15_VERIFICATION_REALIGNMENT`
13. `TRANCHE_IDS_C16_COMPLETENESS_MATRIX`

## Register

| Cluster | Tranche ID | Title | Hard deps | Soft deps | Execution status | Decision payload required | Primary fix layer | Do-not-fix-here | Acceptance artifacts | Closure scope | Merge gate | Non-goals | Burndown state |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C1 | TRANCHE_IDS_C1_CONTRACT_REGISTRY | Canonical preset and schema registry | none | none | Closed | canonical registry shape, canonical preset names, section-schema ownership model | contract layer | do not patch debug UI first | `registry/preset_contract.yaml`; `registry/section_layout_contract.yaml`; `tests/test_preset_contract_registry.py` | contract + tests | human review required | optimizer redesign; artifact cleanup | implemented_pending_review |
| C5 | TRANCHE_IDS_C5_STATE_SEMANTICS | Missing/empty/invalid state semantics | C1 | C2 | Closed | exact semantics for missing vs empty vs zero vs invalid vs synthetic | binding/validation layer | do not add more fallbacks | `docs/state_semantics.md`; `tests/test_state_semantics.py`; identity diff fixture proving missing != empty != zero | implementation + tests | human review required | UI polish | implemented_pending_review |
| C2 | TRANCHE_IDS_C2_RUNTIME_FIVE_PRESET | Runtime and progression five-preset support | C1, C5 | none | Closed | none once C1/C5 settled | runtime/progression | do not solve only in tests | `engine/progression_state.py`; `tests/test_progression_state.py`; runtime acceptance matrix artifact for all 5 presets | implementation + tests + artifact | human review required | compare cleanup | implemented_pending_review |
| C11 | TRANCHE_IDS_C11_PERK_PRESET_CONTRACT | Perk preset contract normalization | C1, C5 | C2 | Closed | resolved: transient non-canonical perk namespaces are allowed only when explicitly typed as `preset_namespace_class: transient` and remain runtime-only | perk config + binding layer | do not preserve `default` as hidden sixth preset | `compilers/account_state_compiler.py`; `engine/query_perk_compiler.py`; `tests/test_perk_preset_contract.py`; `kb/perks/contracts/perk-namespace-policy.md` | implementation + tests | human review required | timeline math changes | implemented_pending_review |
| C12 | TRANCHE_IDS_C12_NAMESPACE_HYGIENE | Synthetic namespace quarantine and hygiene | C1, C5, C11 | C2 | Closed | resolved: transient namespaces remain runtime-only and canonical artifacts/identity sanitize them back to canonical preset context | namespace hygiene boundary + artifact writers | do not just rename strings in reports | `kb/perks/contracts/namespace-hygiene.md`; `tests/test_namespace_hygiene.py`; regenerated artifacts proving no synthetic names in canonical outputs | implementation + tests + regenerated artifacts | human review required | compare-score tuning | implemented_pending_review |
| C10 | TRANCHE_IDS_C10_CLEAN_SECTION_INGESTION | Relics/Vault fact-only compiler ingestion | C1 | C5 | Closed | none | compiler | do not rely on downstream blacklists | `compilers/account_state_compiler.py`; `tests/test_relics_vault_fact_ingestion.py` | implementation + tests | PR review | UI category display | implemented_pending_review |
| C7 | TRANCHE_IDS_C7_WSPLUS_TYPED_MODEL | WS+ typed model and QE routing | C1, C5 | C13 | Closed | exact WS+ typed schema incl preset-indexed fields and extra columns | compiler + QE | do not keep first-parseable-float heuristics | typed WS+ model file/contract; `tests/test_wsplus_typed_model.py`; QE artifact showing preset-sensitive rows | implementation + tests + artifact | human review required | generic preview cosmetics | implemented_pending_review |
| C8 | TRANCHE_IDS_C8_UW_TYPED_TRACKS | UW explicit track identity | C1 | C5 | Closed | none | compiler/UW model | do not keep positional zipping | `tests/test_uw_typed_tracks.py`; export rows contain attribute names | implementation + tests | PR review | compare policy changes | implemented_pending_review |
| C9 | TRANCHE_IDS_C9_BOT_TYPED_STATE | Bot typed compiled state | C1 | C5 | Closed | none | compiler/bot model | do not leave export meaning implicit | `tests/test_bot_typed_state.py`; compiled/exported rows show level + resolved value + unit | implementation + tests | PR review | bot balancing | implemented_pending_review |
| C13 | TRANCHE_IDS_C13_AUDIT_SURFACE_CONTRACTS | Full vs partial audit surface contracts | C1, C5 | C12 | Closed | which surfaces are canonical/full vs partial/selected-context | output contract layer | do not fix by adding more hidden truncation | `docs/audit_surface_contracts.md`; `tests/test_audit_surface_contracts.py`; one full completeness artifact exists | design + implementation + tests | human review required | theme/styling | implemented_pending_review |
| C14 | TRANCHE_IDS_C14_ARTIFACT_OUTPUT_CONTRACTS | Artifact classes and provenance | C1, C5, C12, C13 | C2 | Closed | artifact class taxonomy | run_stats/output writers | do not leave provenance implicit | `docs/artifact_contracts.md`; `tests/test_artifact_contracts.py`; regenerated artifact set with class/provenance fields | implementation + tests + regenerated artifacts | human review required | optimizer math | implemented_pending_review |
| C15 | TRANCHE_IDS_C15_VERIFICATION_REALIGNMENT | Tests, fixtures, and false-green cleanup | C1, C2, C5, C11, C12, C13, C14 | C16 | Closed | fixture refresh policy | test/fixture layer | do not update tests before contracts settle | refreshed golden fixtures; `tests/test_five_preset_completeness.py`; removed stale/synthetic expectations from canonical tests | implementation + tests + fixture refresh | human review required | new feature tests | implemented_pending_review |
| C16 | TRANCHE_IDS_C16_COMPLETENESS_MATRIX | Full family completeness artifact and CI gate | C1, C5, C13, C14 | C15 | Closed | exact matrix schema | audit/verification artifact layer | do not infer completeness from partial views | `out/family_completeness_matrix.json`; `tests/test_family_completeness_matrix.py`; CI gate | implementation + tests + CI | human review required | unrelated dashboards | implemented_pending_review |
| C3 | TRANCHE_IDS_C3_POSITIONAL_SCHEMA_REMOVAL | Remove hard-coded positional schema | C1 | C7, C8, C9, C10 | Closed | none | compiler/parser cleanup | do not patch positions in every consumer separately | `tests/test_schema_header_driven_parsing.py` | implementation + tests | PR review | UI-only refactors | implemented_pending_review |
| C4 | TRANCHE_IDS_C4_RAW_TABLE_TYPE_UPLIFT | Replace raw-table deferred interpretation | C1 | C7, C10 | Closed | typed family boundary policy | compiler/account-state normalization | do not keep reparsing in QE/UI | `tests/test_typed_family_models.py` | implementation + tests | PR review | historical archive formats | implemented_pending_review |
| C6 | TRANCHE_IDS_C6_BOUND_PRESET_FAMILY_OBJECT | Bound preset-family execution object | C1, C5, C11 | C2, C12 | Closed | hybrid-state policy | state binding / request construction | do not continue independent family fallback binding | `tests/test_bound_preset_family_object.py` | implementation + tests | human review required | execution scheduler changes | implemented_pending_review |

## Notes on tranche usage

- `C1`, `C5`, `C11`, `C13` contain policy/schema decisions and should not be merged until the decision payloads are explicitly answered.
- `C15` should remain blocked from closure until earlier contract tranches are stable.
- `C16` is the global close-out proof tranche.

## Current tranche notes

- `TRANCHE_IDS_C1_CONTRACT_REGISTRY`: decision payload resolved. Canonical preset names are `Tourney`, `Farming`, `Milestone`, `Preset 4`, and `Preset 5`. Raw aliases normalize only at ingestion: `Preset 3 -> Milestone`, `Testing -> Milestone`, `Placeholder 4th preset -> Preset 4`, `Placeholder 5th preset -> Preset 5`. After ingestion, non-canonical names are invalid.
- `TRANCHE_IDS_C5_STATE_SEMANTICS`: decision payload resolved. `missing` is invalid in canonical flows and fails closed; `empty` is valid and explicit; `zero` is a valid numeric zero distinct from missing/empty; `invalid` fails closed; `synthetic` is transient non-canonical runtime/compare state and must be explicitly typed/quarantined. No fail-open behavior is allowed in canonical flows.
- `TRANCHE_IDS_C1_CONTRACT_REGISTRY`: closed in implementation. Canonical preset/schema registry now owns the active parser and debug-ui preset truth used by executable consumers.
- `TRANCHE_IDS_C5_STATE_SEMANTICS`: closed in implementation. Missing vs empty vs zero semantics are now tested through parser and identity behavior, and non-canonical perk preset names fail closed in canonical flows unless explicitly typed as transient.
- `TRANCHE_IDS_C2_RUNTIME_FIVE_PRESET`: closed in implementation. Progression/runtime now accepts all five canonical presets and the five-preset acceptance artifact has been regenerated at `out/runtime_acceptance_matrix.json`.
- `TRANCHE_IDS_C10_CLEAN_SECTION_INGESTION`: closed in implementation. Relics and Vault compilation now emits fact rows only, and downstream blacklist cleanup dependence has been reduced to upstream-correct ingestion.
- `TRANCHE_IDS_C11_PERK_PRESET_CONTRACT`: decision payload resolved and closed in implementation. Canonical perk flows now select exactly one preset, transient non-canonical perk sets require explicit `preset_namespace_class: transient` typing, and the hidden multi-key/default merge path is removed.
- `TRANCHE_IDS_C12_NAMESPACE_HYGIENE`: decision payload resolved and closed in implementation. Canonical artifacts and state identity now quarantine transient perk namespaces so projected-max, timeline, and audit-only names do not leak into canonical preset identity or publishable outputs.
- `TRANCHE_IDS_C8_UW_TYPED_TRACKS`: closed in implementation. UW tracks now preserve explicit attribute identity in compiled account state and stat-input emission without positional/order reconstruction.
- `TRANCHE_IDS_C9_BOT_TYPED_STATE`: closed in implementation. Bot compiled state and emitted rows now carry explicit level, resolved value, and resolved unit metadata.
- `TRANCHE_IDS_C3_POSITIONAL_SCHEMA_REMOVAL`: closed in implementation. UW/Bot/Guardian compilation now resolves field positions via section-layout contract columns instead of hard-coded positional extraction in canonical compiler paths.
- `TRANCHE_IDS_C4_RAW_TABLE_TYPE_UPLIFT`: closed in implementation. Guardian rows are now compiled to typed family tracks and consumed directly by stat-input compilation instead of deferred raw-table reparsing.
- `TRANCHE_IDS_C6_BOUND_PRESET_FAMILY_OBJECT`: closed in implementation. Preset-family request binding is now explicit and fail-closed: card/module lanes are bound to the selected preset in canonical flows, canonical perk lane mismatches are rejected, and transient perk lane mismatches remain explicitly typed.
- `TRANCHE_IDS_C7_WSPLUS_TYPED_MODEL`: closed in implementation. WS+ now compiles as typed preset-indexed tracks and stat-input emission resolves selected preset lanes directly instead of first-parseable-float heuristics.
- `TRANCHE_IDS_C13_AUDIT_SURFACE_CONTRACTS`: closed in implementation. Audit surfaces now declare full vs partial contracts explicitly, and canonical preset-lane completeness (including explicit empty lanes) is emitted in `out/audit_surface_manifest.json`.
- `input/_IDS.csv` did not change during the C1/C5/C2/C10 tranche set; implementation and artifact changes were derived from existing source-state only.
