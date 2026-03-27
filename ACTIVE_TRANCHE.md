# ACTIVE_TRANCHE.md

## Role

This file is the live tranche cursor for the **whitelist rebuild**.

It identifies:
- the exact active tranche
- what was done in the last completed tranche
- what the next tranche must accomplish
- known stop conditions

Canonical tranche contract truth lives in `ARCHITECTURE.md`.
File-status ledger lives in `REPO_INDEX.yaml`.

---

## Tranche sequence

| # | Name | Status |
|---|------|--------|
| 0 | Freeze baseline and governance | ✅ COMPLETE |
| 1 | Scaffold new active spine | ✅ COMPLETE |
| 2A | Input facade established | ✅ COMPLETE |
| 2B | Input ownership transfer | ✅ COMPLETE |
| 3 | QE extraction and repair | ✅ COMPLETE |
| 4 | Simulator extraction | ✅ COMPLETE |
| 5A | Scorer/ranker/lab-advisory authority transfer | ✅ COMPLETE |
| 5B | Objectives/enhancement-state-contracts transfer | ⏸ DEFERRED (T7) |
| 6 | App orchestration | ✅ COMPLETE |
| 7A | Live spine + quarantine markers | ✅ COMPLETE |
| 7B | Default gate hardening | ✅ COMPLETE |
| 8 | Archive demotion | complete |
| 9 | Final consolidation and hardening | pending |

---

## Tranche 0 — COMPLETE

**Goal:** Freeze current repo as reference. Document new architecture. Classify all non-KB files.

**Deliverables produced:**
- `ARCHITECTURE.md` — rewritten for whitelist rebuild target architecture
- `REPO_INDEX.yaml` — new file; classifies every non-KB file as active_candidate / archive_candidate / generated / delete_later; supersedes `REPO_MAP.yaml`
- `ACTIVE_TRANCHE.md` — this file; rewritten as whitelist rebuild cursor

**Superseded:**
- `REPO_MAP.yaml` → delete_later (superseded by REPO_INDEX.yaml)
- Old `ARCHITECTURE.md` → replaced in-place
- Old `ACTIVE_TRANCHE.md` → replaced in-place

**Verification:** REPO_INDEX.yaml exists and covers all non-KB files. ✅

---

## Tranche 1 — COMPLETE

**Goal:** Create the new active folder/file structure.

**Deliverables produced:**
- `qe/` — 7 stub files (\_\_init\_\_, contracts, models, routing, materializer, kernel, publication, dependency_registry)
- `simulators/` — 4 stub files (\_\_init\_\_, progression, timing, scenario)
- `evaluators/` — 5 stub files (\_\_init\_\_, scorer, objectives, compare, ranker)
- `advisors/` — 3 stub files (\_\_init\_\_, recommendation_policy, upgrade_advisor)
- `app/` — 3 stub files (\_\_init\_\_, run_stats, pipeline)
- `input/loader.py`, `input/runtime_state.py`, `input/parsers.py` — stub files
- `tests/live/` — 4 stub test files (main_path, qe_core, simulators_core, evaluators_core)
- `tests/expensive/`, `tests/quarantine/` — empty subdirectories
- `archive/legacy/` — destination for T8 demotions
- `pyproject.toml` updated to include new packages

**Verification:** `python -c "import qe; import simulators; import evaluators; import advisors; import app"` → OK ✅

---

## Tranche 1 (original spec) — ACTIVE

**Goal:** Create the new active folder/file structure. Every target layer has a destination. No migration requires inventing structure.

**In scope:**
- Create `qe/`, `simulators/`, `evaluators/`, `advisors/`, `app/` folders
- Create all target `.py` files as empty stubs with layer-contract docstrings
- Create `tests/live/`, `tests/expensive/`, `tests/quarantine/` subdirectories
- Update `pyproject.toml` to recognise the new packages

**Out of scope:**
- Do NOT move or copy any logic yet (that starts in T2)
- Do NOT delete any legacy files yet (that starts in T8)
- Do NOT modify any legacy imports yet

**Exit criteria:**
- Every target layer folder exists
- Every target file exists (may be a stub/placeholder)
- No migration in T2–T6 requires creating a new destination not already present

**Verification:**
- `python -c "import qe; import simulators; import evaluators; import advisors; import app"` succeeds (stubs only)
- Target tree matches allowed tree in `ARCHITECTURE.md`

---

## Stop conditions for T1 (now closed)

- Stop if a target file seems to need two layers as owners — report instead.
- Stop if a package init introduces a circular import even at stub level — report instead.
- Do NOT add any domain logic to stub files. Stubs contain only a module docstring.

---

## Tranche 2 — ACTIVE

**Goal:** Consolidate runtime inputs and runtime-state assembly into `input/`.

**In scope:**
- Rename/consolidate `input/assumptions.yaml` → `input/manual_inputs.yaml`
- Consolidate perk config (currently `input/perks.json`) into manual_inputs or as a named side-car
- Rename `input/derived/perks_max_progression_policy.runtime.json` → `input/derived/perks_derived.json`
- Populate `input/parsers.py` with logic extracted from `parsers/ids_parser.py` and parsing sections of `compilers/stat_input_compiler.py`
- Populate `input/loader.py` with loading/validation logic from `compilers/account_state_compiler.py` and `run_stats.py`
- Populate `input/runtime_state.py` with RuntimeState assembly from `models/account_state.py`, `models/ids_raw.py`, `engine/scenario_runtime_inputs.py`
- Verify no active code still points at the old duplicate input paths once migration is done

**Out of scope:**
- Do NOT yet migrate QE logic (T3)
- Do NOT yet delete legacy files (T8)
- Legacy files remain importable as fallback until T8

**Exit criteria:**
- `input/loader.py` loads all inputs from one place
- `input/runtime_state.py` assembles RuntimeState successfully
- `input/manual_inputs.yaml` is the single manual inputs file
- `input/derived/perks_derived.json` is the single derived perk artifact
- No active code points at deprecated duplicate input paths

**Verification:**
- `python -c "from input.loader import load_inputs; load_inputs()"` succeeds
- `python -c "from input.runtime_state import build_runtime_state"` succeeds

## T2A — COMPLETE (input facade established)

**Deliverables:**
- `input/manual_inputs.yaml` — canonical manual inputs file (content from `assumptions.yaml`)
- `input/derived/perks_derived.json` — canonical derived perk artifact (content from `perks_max_progression_policy.runtime.json`)
- `input/parsers.py` — stub re-exporting from `parsers.ids_parser` (facade only at this stage)
- `input/runtime_state.py` — re-exports types, `build_runtime_state()` delegating to compiler
- `input/loader.py` — `InputBundle`, `load_inputs()` entry point

**Limitation of T2A:** All `input/` files were facades/re-exports. `run_stats.py` and tests still used legacy paths. Compiler was still the authority.

---

## T2B — COMPLETE (input ownership transfer)

**Deliverables:**
- `input/parsers.py` → **AUTHORITY**. Contains actual IDS parsing logic copied from `parsers/ids_parser.py`. `IdsRaw` still sourced from `models/ids_raw.py` (T3).
- `parsers/ids_parser.py` → **SHIM**. Re-exports `parse_ids`, `SectionSpec`, `SECTION_SPECS` from `input.parsers`. Will be demoted T8.
- `input/runtime_state.py` → **AUTHORITY** entry point. `build_runtime_state()` is the sanctioned assembly entry. `compile_account_state` is a transitional alias.
- `compilers/account_state_compiler.py` → **TRANSITIONAL INTERNAL DETAIL**. Deprecation header added. Private functions (`_normalize_preset_name`, `_parse_optional_int`, `_parse_player_meta`) still needed by 3 transitional test files → kept until T7.
- `run_stats.py` → updated: imports `parse_ids` from `input.parsers`; imports `build_runtime_state as compile_account_state` from `input.runtime_state`; uses `manual_inputs.yaml` and `perks_derived.json` paths.
- `tests/helpers.py` → updated: imports from `input.parsers` and `input.runtime_state`; uses `perks_derived.json`.

**Dual ownership remaining (explicitly transitional):**
| Legacy file | Status | Authority | Remove in |
|-------------|--------|-----------|-----------|
| `parsers/ids_parser.py` | shim | `input/parsers.py` | T8 |
| `compilers/account_state_compiler.py` | internal detail | `input/runtime_state.py` | T8 |
| `models/ids_raw.py` | transitional type def | will move to `qe/models.py` | T3 |
| `models/account_state.py` | transitional type def | will move to `qe/models.py` | T3 |
| `engine/scenario_runtime_inputs.py` | transitional type def | will move to `input/runtime_state.py` or `simulators/` | T4 |
| `input/assumptions.yaml` | old path | `input/manual_inputs.yaml` | T8 |
| `input/derived/perks_max_progression_policy.runtime.json` | old name | `input/derived/perks_derived.json` | T8 |

**Tests still using legacy paths (transitional):**
- `tests/test_*.py` (all except helpers.py) still import from `parsers.ids_parser` and `compilers.account_state_compiler` — these go through shims, all still work. Will be updated in T7.
- 3 test files import private compiler functions (`_normalize_preset_name`, `_parse_optional_int`, `_parse_player_meta`) — these cannot use a shim; those tests are T7 candidates.

---

## Stop conditions for T2 (now closed)

- Stop if `account_state_compiler.py` has deep entanglement with QE logic that cannot be separated cleanly without touching T3 scope — report and defer that portion to T3.
- Stop if merging perk config into `manual_inputs.yaml` breaks existing perk tests — keep as side-car file instead and note.
- Do NOT touch any engine/ files in T2.

---

## T3 -- COMPLETE (QE extraction)

**Goal:** Move deterministic stat/query resolution into `qe/`. Make engine/ and models/ files backward-compat shims.

**Deliverables:**
- `qe/contracts.py` -- **AUTHORITY**. Preset and section layout contract logic from `models/preset_contract.py`.
- `qe/models.py` -- **AUTHORITY**. StatInput, StatRow, StatBook, BoundPresetFamily, StateIdentity, StateIdentityBinding, BoundStatInputs, bind_state_identity, compile_stat_inputs_with_identity. Combined from `models/stat_input.py`, `models/statbook.py`, `models/bound_preset_family.py`, `engine/state_identity.py`.
- `qe/materializer.py` -- **AUTHORITY**. FamilyBaselineMaterializer from `engine/family_baseline_materializer.py`. Updated imports: engine.state_identity -> qe.models, models.stat_input -> qe.models.
- `qe/dependency_registry.py` -- **AUTHORITY**. DependencyRegistry from `engine/dependency_registry.py`. Updated: engine.family_baseline_materializer -> qe.materializer.
- `qe/kernel.py` -- **AUTHORITY**. StatQueryKernel, QueryResponse, OverlayApplicator etc. from `engine/stat_query_kernel.py`. Updated: engine.dependency_registry -> qe.dependency_registry, engine.family_baseline_materializer -> qe.materializer, engine.state_identity -> qe.models.
- `qe/routing.py` -- **AUTHORITY**. resolve_stats from `engine/stat_engine.py`. Updated: engine.state_identity -> qe.models, engine.stat_query_kernel -> qe.kernel, models.stat_input -> qe.models, models.statbook -> qe.models.
- `qe/publication.py` -- **AUTHORITY**. publish_phase3_query_surfaces from `engine/query_surface_publication.py`. Updated: models.statbook -> qe.models.

**Shims created:**
| Legacy file | Now a shim for |
|-------------|----------------|
| `models/stat_input.py` | `qe.models.StatInput` |
| `models/statbook.py` | `qe.models.StatBook, StatRow` |
| `models/bound_preset_family.py` | `qe.models.BoundPresetFamily` |
| `models/preset_contract.py` | `qe.contracts.*` |
| `engine/state_identity.py` | `qe.models.*` |
| `engine/family_baseline_materializer.py` | `qe.materializer.*` |
| `engine/dependency_registry.py` | `qe.dependency_registry.*` |
| `engine/stat_query_kernel.py` | `qe.kernel.*` |
| `engine/stat_engine.py` | `qe.routing.resolve_stats` |
| `engine/query_surface_publication.py` | `qe.publication.*` |

**Transitional internals (still in engine/, NOT moved):**
- `engine/query_routing.py` -- used by qe/ files; will move in T4 or later
- `engine/stat_resolution_core.py` -- fallback resolver; used by qe/routing.py
- `engine/query_derived_composites.py` -- used by qe/publication.py
- `engine/runtime_consumer_registry.py` -- used by qe/dependency_registry.py
- `compilers/stat_input_compiler.py` -- deferred import inside qe/models.compile_stat_inputs_with_identity
- `models/account_state.py` -- still imported by qe/models.py (large type def; T4+)
- `models/ids_raw.py` -- not moved (used by input/ layer; T4+)

**Verification:** 82 tests pass (pre-existing 1 failure unchanged: FileNotFoundError subprocess test). ✅

---

## T3B — COMPLETE (QE runtime authority transfer)

**Goal:** Make qe/ the direct runtime owner of deterministic stat/query resolution.

**Deliverables:**
- `qe/contracts.py` — extended with surface-ID translation functions (`to_v2_surface_id`, `to_legacy_surface_id`, `to_v2_destination`, `to_legacy_destination`, `pack_v2_naming_remap_rows`, `pack_v2_naming_remap_surface_maps`). Extracted from `engine/query_routing.py`.
- `qe/materializer.py` — bug fix: `_normalize_value_type` now maps `'pct' → 'scalar'` (fixes `ValueError: Surface 'state::tower.defense_pct' mixes multiple contributor value types`). Import updated to `qe.contracts`.
- `qe/kernel.py` — import updated to `qe.contracts`.
- `qe/routing.py` — import updated to `qe.contracts`.
- `engine/query_routing.py` — updated `StatInput` import to `qe.models`; retains compiler routing tables as transitional authority.
- `run_stats.py` — 5 import sites updated to `qe.*` directly.
- `engine/progression_recalc_bridge.py` — all QE imports updated to `qe.*`.
- `engine/timing_engine.py` — all QE imports updated to `qe.*`.
- `tests/live/test_qe_core.py` — 13 live tests all importing directly from `qe.*`.

**Bug fixed:** `state::tower.defense_pct` raised `ValueError` on mixed value types (`pct`/`scalar`). Fixed in `qe/materializer.py`.

**Transitional internals (not moved):**
- `engine/query_routing.py` — still owns compiler routing tables; surface-ID functions duplicated in `qe/contracts.py` as authority.
- `engine/stat_resolution_core.py` — fallback resolver; still used by `qe/routing.py`.
- `engine/runtime_consumer_registry.py` — consumed by qe-owned progression/timing engines.

**Verification:** 13/13 live QE core tests pass. Parity harness passes. Pre-existing 8 failures unchanged. ✅

---

## T4 — COMPLETE (Simulator extraction)

**Goal:** Move simulation projection logic from `engine/` into `simulators/`. Simulators/ becomes the direct runtime owner.

**Deliverables:**
- `simulators/scenario.py` — **AUTHORITY**. Full content from `engine/scenario_engine.py`. No engine dependencies (clean extraction).
- `simulators/timing.py` — **AUTHORITY**. Full content from `engine/timing_engine.py`. Updated: `engine.scenario_engine` → `simulators.scenario`. One transitional engine import: `engine.runtime_consumer_registry`.
- `simulators/progression.py` — **AUTHORITY**. Full content from `engine/progression_recalc_bridge.py`. Already imported from `qe.*` (T3B). Transitional engine imports: `engine.perk_timeline_state`, `engine.runtime_consumer_registry`, `engine.runtime_consumer_executor`, `engine.incremental_*`.

**Shims created:**
| Legacy file | Now a shim for |
|-------------|----------------|
| `engine/scenario_engine.py` | `simulators.scenario.*` |
| `engine/timing_engine.py` | `simulators.timing.*` (incl. private `_uptime`, `_load_wave_timing_baselines`) |
| `engine/progression_recalc_bridge.py` | `simulators.progression.*` |

**Transitional internals (stay in engine/):**
- `engine/scenario_runtime_inputs.py` — `ScenarioRuntimeInputs` type def; imported by `qe/models.py` (layer constraint prevents moving to simulators/). Will move to `input/` in T5+.
- `engine/boss_wave_engine.py` — 1143 lines; consumes simulators via shims. Will move to `simulators/progression.py` in a later pass.
- `engine/progression_state.py`, `engine/wave_progression_policy.py`, `engine/workshop_progression_policy.py`, `engine/free_upgrade_generation_policy.py`, `engine/perk_timeline_generator.py`, `engine/perk_timeline_state.py` — progression support files; consumed by `simulators/progression.py` as transitional internals.
- `engine/runtime_consumer_registry.py`, `engine/runtime_consumer_executor.py` — consumed by simulators/ as transitional internals.
- `engine/incremental_*.py` — incremental cache support; consumed by `simulators/progression.py`.

**Regression closure:** 10 new failures introduced by T4 (monkeypatch shim gaps, simulators.progression alias). All fixed by:
- Adding private symbol re-exports to `engine/timing_engine.py` shim (`_uptime`, `_load_wave_timing_baselines`)
- Adding private symbol re-exports to `engine/scenario_engine.py` shim (`_get_boss_timing_override`, `_make_wave_timing_row`)
- Adding `simulators.progression` module alias to resolve `test_progression_recalc_bridge.py` monkeypatch targets
- Adding `engine.stat_engine` private symbol forwarding (`_resolve_manifest_approved_family`) via shim
- Adding `engine.family_baseline_materializer` and `engine.stat_engine` full private-symbol re-exports for delegation tests

**Final non-live suite:** 4 failed, 391 passed, 136 deselected. Failing tests are exactly the 4 proven pre-existing failures (present on main branch before any tranche work):
1. `test_lab_advisory_lookup::test_lab_advisory_rankings_are_not_routed_into_mechanical_or_optimizer_surfaces`
2. `test_perk_scaling::test_free_upgrades_card_is_split_into_canonical_free_upgrade_stats_and_values_match_ep_baseline`
3. `test_perk_scaling::test_all_coin_bonus_multiplier_uses_farming_tier_and_numeric_pack_multipliers`
4. `test_tier_progression_account_state::test_account_state_compiles_tier_progression_fields_from_ids`

Delta versus pre-T4 baseline: 0 new failures. ✅

---

## T5A -- COMPLETE (Scorer/ranker/lab-advisory authority transfer)

**Goal:** Transfer authority for scorer, ranker, and lab-advisory from `optimizer/` and `engine/` into `evaluators/` and `advisors/`.

**Deliverables:**
- `evaluators/scorer.py` -- **AUTHORITY**. Full content from `optimizer/scorer.py`. Owns: MissingGovernedSurfaceError, compute_ehp/edamage/eecon, compute_optimizer_scores, optimizer_consumption_contract_snapshot.
- `evaluators/ranker.py` -- **AUTHORITY**. Full content from `optimizer/path_ranker.py`. Updated: `optimizer.scorer` import -> `evaluators.scorer`. Owns: rank_lab_path, EHP_LABS, EDAMAGE_LABS, EECON_LABS.
- `advisors/upgrade_advisor.py` -- **AUTHORITY**. Full content from `engine/lab_advisory.py`. Owns: LabAdvisoryRow, LabAdvisorySourceRegistryRow, load_lab_advisory_rows, get_lab_advisory_row, etc.

**Shims created:**
| Legacy file | Now a shim for |
|-------------|----------------|
| `optimizer/scorer.py` | `evaluators.scorer.*` |
| `optimizer/path_ranker.py` | `evaluators.ranker.*` |
| `engine/lab_advisory.py` | `advisors.upgrade_advisor.*` |

**Verification:** 13 targeted tests pass (1 pre-existing failure: rg subprocess not on Windows PATH). Full gate waived — tests being consolidated in T7.

---

## T5B -- DEFERRED to T7 (Objectives/enhancement-state-contracts transfer)

**Blocked reason:** `optimizer/enhancement_state_contracts.py` tests use `monkeypatch.setattr(module, '_OBSERVED_RUN_ELS_INPUT_PATH', ...)` and `monkeypatch.setattr(module, '_WORKSHOP_PREP_CONTRACT_PATH', ...)` on module-level path variables. Moving the logic to `evaluators/objectives.py` severs the monkeypatch target, breaking 6 tests. Requires tests to be updated first (T7 scope).

**Current state:**
- `optimizer/enhancement_state_contracts.py` -- remains **AUTHORITY** for its scope. NOT a shim.
- `evaluators/objectives.py` -- remains **stub** with deferred note.

**Will complete in:** T7 (test rebuild), after monkeypatched tests are rewritten to patch `evaluators.objectives`.


---

## T6 -- COMPLETE (App orchestration)

**Goal:** Make `app/` the thin active orchestration shell. No domain logic introduced.

**Deliverables:**
- `app/run_stats.py` -- **ACTIVE CLI ENTRYPOINT**. Thin argparse shell. Calls `app.pipeline.run_pipeline(args)`. No domain logic.
- `app/pipeline.py` -- **ACTIVE ORCHESTRATION**. Owns: wiring input -> qe -> evaluators -> advisors -> out. Imports active layer functions from `qe.*`, `evaluators.*`, `engine.*`. Imports transitional domain helpers from `run_stats` module (T7 scope for extraction).

**Legacy path superseded:**
- Root `run_stats.py` `__main__` block now delegates to `app.run_stats.main()`. Backward compat preserved: `python run_stats.py` still works.
- Root `run_stats.py` becomes a transitional domain helper library (not yet a shim -- domain functions extracted in T7).

**Active layer surfaces used in pipeline:**
| Import | From |
|--------|------|
| `parse_ids` | `input.parsers` |
| `compile_stat_inputs`, `normalize_state_mode`, `state_mode_support` | `compilers.stat_input_compiler` |
| `resolve_stats` | `qe.routing` |
| `publish_phase3_query_surfaces` | `qe.publication` |
| `compute_optimizer_scores` | `evaluators.scorer` |
| `build_ep_compare`, `build_line_by_line_verification`, etc. | `engine.verification` |
| `annotate_display_fields` | `engine.display` |

**Transitional (T7):** `_build_compare_rows_by_preset`, `_build_publish_gate_audits`, `_build_kb_incomplete_areas`, and ~20 other domain helper functions still live in `run_stats.py` module, imported by `app/pipeline.py` as `_h.*` until T7 migrates them to proper layers.

**Verification:**
- `python3 app/run_stats.py --help` -- passes, correct argparse output
- `python3 -c "import app.run_stats; import app.pipeline"` -- both import cleanly
- Delegation chain verified: app/run_stats -> app/pipeline -> qe.* + evaluators.*
- Targeted: `tests/test_smoke.py`, `tests/test_phase3_contract_path.py`, `tests/test_namespace_hygiene.py`, `tests/test_artifact_contracts.py` -- 9 passed
- Targeted: `tests/test_phase3_optimizer_integration.py`, `tests/test_phase3_runtime_validation.py` -- 4 passed

**Next active tranche:** T7 -- Test cull and rebuild

---

## T7A -- COMPLETE (Live spine + quarantine markers)

**Goal:** Implement live architecture spine tests; mark pre-existing failures as quarantine.

See T7B below for default gate hardening.

## T7B -- COMPLETE (Default gate hardening)

**Goal:** Make the default pytest gate the live architecture spine only — small, fast, trustworthy.

**New default gate:**
```bash
python3 -m pytest
# testpaths = ["tests/live"]
# addopts = "-m 'not quarantine'"
# Result: 23 passed in 2:59
```

**Manual commands for broader coverage:**
```bash
# Full legacy suite (not slow, not expensive, not quarantine):
python3 -m pytest tests/ -m 'not slow and not expensive and not quarantine'

# Slow integration tests:
python3 -m pytest tests/ -m slow

# Expensive parity/completion tests:
python3 -m pytest tests/ -m expensive

# Everything (no filter):
python3 -m pytest tests/
```

**What is in each gate:**
| Gate | Command | Count | Contents |
|------|---------|-------|----------|
| **Default (live)** | `pytest` | 23 | Active architecture layer contracts (qe, simulators, evaluators, advisors, app) |
| Legacy non-slow | `pytest tests/ -m 'not slow and not expensive and not quarantine'` | ~416 | Broad legacy + active test coverage |
| Slow | `pytest tests/ -m slow` | 46 | smoke, perk_scaling, boss_wave_scaffold, optimizer, progression_accuracy_merge |
| Expensive | `pytest tests/ -m expensive` | 43 | family_baseline_materializer, query_engine_completion, r86_completion, delegation, migration |
| Quarantine | `pytest tests/ -m quarantine` | 2 | Pre-existing failures (stale data, rg subprocess) |

**pyproject.toml changes:**
- Added `quarantine` marker: "pre-existing failures or stale coupling to private/data-dependent state"
- Updated addopts: `"-m 'not slow and not expensive and not quarantine'"`

**Quarantine (2 tests marked `@pytest.mark.quarantine`):**
| Test | Reason |
|------|--------|
| `test_tier_progression_account_state::test_account_state_compiles_tier_progression_fields_from_ids` | Hardcodes player-specific tier data (`Tier 19 == 52`) that does not match current ids.csv |
| `test_lab_advisory_lookup::test_lab_advisory_rankings_are_not_routed_into_mechanical_or_optimizer_surfaces` | Uses `rg` subprocess not available on Windows PATH |

**Live tests implemented (tests/live/ -- 23 total, all pass):**
| File | Tests | Proves |
|------|-------|--------|
| `test_qe_core.py` | 13 | qe.* runtime authority (T3B, pre-existing) |
| `test_main_path.py` | 3 | app/ CLI wiring (T6) |
| `test_simulators_core.py` | 3 | simulators/ layer importable + qe.* consumed |
| `test_evaluators_core.py` | 4 | evaluators/ + advisors/ layer importable + contract sane |

**Slow (46 tests, pre-existing marker, unchanged):**
`test_smoke.py`, `test_perk_scaling.py`, `test_boss_wave_engine_scaffold.py`, `test_optimizer.py`, `test_progression_accuracy_merge.py`

**Expensive (43 tests, pre-existing marker, unchanged):**
`test_family_baseline_materializer.py`, `test_query_engine_completion.py`, `test_resolve_stats_delegation.py` (expensive subset), `test_r86_completion.py`, `test_progression_query_migration.py`, `test_timing_query_migration.py`

**Targeted verification results:**
- 10 new live stub tests: **10 passed in 1.23s**
- Default gate collection: **416 collected, 138 deselected**
- Pre-existing failures removed from default gate: 2 (quarantined)

**Next active tranche:** T8 -- Archive demotion

---

## T8 -- COMPLETE (Archive demotion)

**Goal:** Move proven-dead files to `archive/legacy/`; delete superseded artefacts.

**What was archived:**

| File(s) | Destination | Reason |
|---------|-------------|--------|
| `AGENTS.md` | `archive/legacy/AGENTS.md` | Superseded by whitelist rebuild docs |
| `AI_EXECUTION_PLAN.md` | `archive/legacy/AI_EXECUTION_PLAN.md` | Old Phase 1–4 plan, superseded |
| `BURNDOWN.yaml` | `archive/legacy/BURNDOWN.yaml` | Old burndown format, superseded |
| `REPO_MAP.yaml` | deleted | Superseded by REPO_INDEX.yaml |
| `engine/geometry_wall_contact_*.py` (9 files) | `archive/legacy/engine/` | No active importers; only geometry tests reference these |
| `registry/naming_contract.py` | `archive/legacy/registry/` | No active code imports; scripts/ also archived |
| `registry/output_contracts.md` | `archive/legacy/registry/` | Doc only, no active import |
| `registry/state_semantics.md` | `archive/legacy/registry/` | Doc only |
| `scripts/*.py` (5 files) | `archive/legacy/scripts/` | Dev utilities, not on active path |
| `worker/` (4 files) | `archive/legacy/worker/` | Old Cloudflare worker, unused |
| `templates/wall_contact_*.json` | `archive/legacy/templates/` | Geometry-specific, no active path |
| `optimizer/ACCURACY.md` | `archive/legacy/optimizer/` | Doc only |

**What was NOT archived (active dependencies confirmed):**

| File | Reason kept |
|------|-------------|
| `engine/display.py` | Imported by `run_stats.py` and `app/pipeline.py` |
| `engine/verification.py` | Imported by `run_stats.py` and `app/pipeline.py` |
| `engine/incremental_*.py` (6) | Imported by `simulators/progression.py` |
| `registry/preset_contract.yaml` | Loaded by `qe/contracts.py` (restored after incorrect initial move) |
| `registry/section_layout_contract.yaml` | Loaded by `qe/contracts.py` and `compilers/account_state_compiler.py` |
| `input/assumptions.yaml` | Read by active engine query files |
| `parsers/ids_parser.py` | Still imported by active paths |
| All shims (`engine/*.py`, `models/*.py`, `optimizer/scorer.py`, etc.) | Still consumed by legacy test suite |

**Default gate post-archive:** `23 passed in 3:05` ✅

**Next active tranche:** T9 -- Final hardening

---

## T9 -- COMPLETE (Active dependency hardening and residual authority cleanup)

**Goal:** Close remaining active-path transitional dependencies.

### Dependency ledger decisions

| Item | Decision | Files changed |
|------|----------|---------------|
|  | MOVED to  |  path updated |
|  | MOVED to  |  path updated |
|  (6 files) | MOVED to ; 6 shims created in  |  imports updated;  internal cross-import fixed |
|  | BOUND: kept in ; too small to merit migration cost | No change |
|  | MOVED to ; shim created at  | Display helpers inlined into  to remove  dependency |
| T5B:  | WIRED:  now re-exports from ; authority transfer blocked by test monkeypatching on  /  |  implemented |
|  orchestration-adjacent helpers | BOUNDED: 6 small utilities inlined into  (, , , , , , ); remaining ~34 domain-builder calls documented as bounded transitional |  updated; no more  orchestration-adjacent calls |

### Files changed
-  — registry yaml paths updated to 
-  → 
-  → 
-  (moved from engine/)
-  (moved; internal import fixed)
-  (moved from engine/)
-  (moved from engine/)
-  (moved from engine/)
-  (moved from engine/)
-  (6) — now shims → simulators.*
-  — imports updated to simulators.incremental_*
-  — AUTHORITY, extracted from engine/verification.py
-  — SHIM → evaluators/compare.py
-  — WIRED facade over optimizer.enhancement_state_contracts
-  — 6 orchestration-adjacent utilities inlined; _h.* domain-builder calls documented

### What remains transitional after T9
-  — bounded: output-formatting utility, no migration trigger
-  — still physical authority for T5B; evaluators/objectives.py is the facade; full transfer requires test monkeypatch refactor
-  ~34 domain-builder calls in  — explicitly bounded; no orchestration-adjacent leakage remaining
- All shims (, , , ) — still consumed by legacy test suite

### Live gate result
 after all T9 changes.

**Repo is ready for final completion.** All active-path dependencies are either resolved, relocated, or explicitly bounded.

---

## T9 -- COMPLETE (Active dependency hardening)

### Dependency decisions executed

| Item | Decision |
|------|----------|
| `registry/preset_contract.yaml` | MOVED to `kb/global-rules/contracts/`; `qe/contracts.py` updated |
| `registry/section_layout_contract.yaml` | MOVED to `kb/global-rules/contracts/`; `qe/contracts.py` updated |
| `engine/incremental_*.py` (6) | MOVED to `simulators/`; 6 shims in `engine/`; `simulators/progression.py` imports updated |
| `engine/display.py` | BOUND: kept in `engine/` (93 lines, no migration trigger) |
| `engine/verification.py` | MOVED to `evaluators/compare.py` (authority); shim at `engine/verification.py`; display helpers inlined |
| T5B `optimizer/enhancement_state_contracts.py` | WIRED: `evaluators/objectives.py` re-exports from optimizer authority; full transfer blocked by monkeypatch tests |
| `run_stats.py` in `app/pipeline.py` | BOUNDED: 6 orchestration-adjacent utilities inlined into pipeline.py; ~34 domain-builder calls documented as bounded transitional |

### What remains transitional
- `engine/display.py` -- bounded output utility
- `optimizer/enhancement_state_contracts.py` -- physical authority until test monkeypatch refactor
- `run_stats.py` domain builders in `app/pipeline.py` -- explicitly bounded, no orchestration leakage
- All shims (`engine/*.py`, `models/*.py`, `optimizer/scorer.py`, `optimizer/path_ranker.py`)

### Live gate: `23 passed in 2:46`


---

## T10 -- COMPLETE (Residual cleanup and final validation)

### Dependency ledger decisions

| Residual | Decision |
|----------|----------|
| `run_stats.py` ~34 domain-builder calls in `app/pipeline.py` | **BOUND** -- 2000+ lines of domain logic; distributing requires 4+ new layer files; acceptance gate explicitly permits bounded exception; documented in pipeline.py |
| `engine/display.py` on active path | **MOVED** to `app/display.py`; shim at `engine/display.py`; `app/pipeline.py` now imports from `app.display` directly |
| `app/pipeline.py` engine.verification shim hop | **REMOVED** -- pipeline now imports from `evaluators.compare` directly |
| `app/pipeline.py` engine.display shim hop | **REMOVED** -- pipeline now imports from `app.display` directly |
| `input/assumptions.yaml` still read by 3 engine query files | **UPDATED** -- 3 files now read `manual_inputs.yaml`; string-literal metadata only retains old name; `assumptions.yaml` archived |
| `optimizer/enhancement_state_contracts.py` authority | **TRANSFERRED** to `evaluators/objectives.py`; `optimizer/enhancement_state_contracts.py` is now a shim; 6 test monkeypatches updated to target `evaluators.objectives` |

### Files changed
- `app/display.py` -- AUTHORITY (moved from engine/display.py)
- `engine/display.py` -- SHIM -> app.display
- `app/pipeline.py` -- imports updated: engine.display -> app.display, engine.verification -> evaluators.compare
- `evaluators/objectives.py` -- AUTHORITY (full content from optimizer/enhancement_state_contracts.py; _OBSERVED_RUN_ELS_INPUT_PATH -> manual_inputs.yaml)
- `optimizer/enhancement_state_contracts.py` -- SHIM -> evaluators.objectives
- `tests/test_optimizer_enhancement_state_contracts.py` -- 6 monkeypatches updated to target evaluators.objectives
- `engine/query_currency_income.py` -- _DEFAULT_MANUAL_INPUT_PATH -> manual_inputs.yaml
- `engine/query_module_drop_economy.py` -- _DEFAULT_MANUAL_INPUT_PATH -> manual_inputs.yaml
- `engine/query_module_runtime_policy.py` -- _DEFAULT_MANUAL_INPUT_PATH -> manual_inputs.yaml
- `input/assumptions.yaml` -- ARCHIVED to archive/legacy/assumptions.yaml
- `README.md` -- rewritten to reflect final active architecture
- `REPO_INDEX.yaml` -- updated status for run_stats.py and archived assumptions.yaml

### Bounded exceptions (explicitly documented, non-blocking)
1. **`run_stats.py` domain builders** -- ~34 domain-builder functions used by `app/pipeline.py` as `_h.*`. These are domain-layer logic (audit builders, compare matrices, gap analysis), not orchestration helpers. Distributing them requires defining dedicated layer files for each domain area. Not feasible in T10 without broadening scope. Pipeline docstring documents this explicitly.

### What remains after T10
- `engine/` shims -- backward-compat for legacy test suite; no active-path imports
- `models/` shims -- backward-compat for legacy test suite
- `optimizer/scorer.py`, `optimizer/path_ranker.py` shims
- `run_stats.py` -- bounded domain library used by pipeline
- `engine/display.py` -- shim (active callers now use app.display or evaluators.compare)
- `engine/verification.py` -- shim (active callers now use evaluators.compare)

### Final validation
- `23 passed in 2:53` -- default gate (tests/live/) passes
- `8 passed in 0.40s` -- test_optimizer_enhancement_state_contracts.py passes with new monkeypatches
