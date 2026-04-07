# ARCHITECTURE.md

## Purpose

This document describes the **target active architecture** for the whitelist rebuild.
It is the canonical reference for which layers own what, what the allowed active file tree is,
and how layers may depend on each other.

It supersedes the Phase 4 architecture description that preceded the whitelist rebuild.

---

## Guiding principle

> Inputs produce runtime state. KB owns truth. QE resolves stats. Simulators project outcomes.
> Evaluators score outcomes. Advisors recommend actions. App orchestrates. Tests verify. Archive holds history.

The active surface should be small enough that an AI agent can navigate it in one pass without ambiguity.

---

## Allowed active tree

```
/
  README.md
  ARCHITECTURE.md
  ACTIVE_TRANCHE.md
  REPO_INDEX.yaml
  pyproject.toml
  requirements.txt
  .gitignore

  input/
    manual_inputs.yaml       # single manual input file
    manual_inputs.contract.yaml  # schema contracts for manual advisory/runtime-policy inputs
    loader.py                # loads and validates all inputs
    ids_parser.py            # IDS CSV parsing + IdsRaw type
    state_types.py           # source/account/scenario state dataclasses
    state_builder.py         # AccountState runtime assembly logic
    runtime_state.py         # thin sanctioned runtime-state entrypoint
    imports/
      ids.csv
      progress.csv
      ep_export.csv
      manifest.json
    derived/
      perks_derived.json     # single derived perk artifact

  kb/
    ... unchanged ...

  qe/
    shared_runtime_context.py  # shared immutable QE/compiler runtime context
    contracts.py               # stat-query value contracts
    models.py                  # typed stat/query model structs
    query_routing.py           # compiler routing indexes and KB binding rules
    stat_input_compiler.py     # stat input compiler
    materializer.py            # family baseline materialisation
    kernel.py                  # core deterministic resolution kernel
    routing.py                 # planner, report snapshots, native family query entrypoints
    stat_resolution.py         # bounded compat/report resolver; not simulator-facing foundation
    publication.py             # sanctioned surface publication coordinator and dashboard payload assembly
    dependency_registry.py     # dependency graph and invalidation
    consumer_registry.py       # runtime consumer bundle registry
    kb_surfaces.py             # KB table loader for gameplay constants
    perk_tables.py             # perk lookup table loader
    query_perk_compiler.py     # perk-query compilation helper
    query_state_mode_policy.py # state-mode policy helper
    query_currency_income.py   # bounded publisher: currency income
    query_derived_composites.py  # bounded publisher: derived composites
    query_module_policy.py       # bounded publisher: module runtime/draw/drop/lab/mission policy

  simulators/
    __init__.py
    contracts.py                # simulator-facing checkpoint/row contracts
    perks.py                    # checkpoint-local perk application helpers
    snapshot_resolver.py        # lightweight QE-backed checkpoint resolver
    performance.py              # narrow simulator performance probes/benchmarks
    progression.py              # progression projection
    timing.py                   # timing/wave projection
    scenario.py                 # scenario projection
    perk_timeline_state.py      # perk state application
    perk_timeline_generator.py  # perk timeline generation (moved from engine/)
    wave_progression_policy.py  # wave progression rules
    runtime_consumer_executor.py # runtime consumer execution
    incremental_cache_fingerprint.py
    incremental_cache_validator.py
    incremental_overlay_publisher.py
    incremental_parity_harness.py
    incremental_recalc_runtime.py
    incremental_subset_executor.py
    run_executor.py             # run-level simulator executor

  evaluators/
    scorer.py                # scoring engine
    objectives.py            # objective definitions
    compare.py               # comparison helpers
    ranker.py                # ranking and sorting

  advisors/
    recommendation_policy.py # policy rules for recommendations
    upgrade_advisor.py       # upgrade/next-step advice

  app/
    __init__.py
    inspector_data.py        # inspector data transforms
    models.py                # app-level dataclasses for orchestration/display
    run_stats.py             # thin CLI entrypoint
    run_analysis.py          # analysis-oriented app entrypoint
    pipeline.py              # layer wiring only
    publication.py           # app-level output publishing helpers
    display.py               # output number formatting and display annotation
    streamlit_inspector.py   # streamlit inspector wiring

  tests/
    conftest.py
    helpers.py
    live/
      test_main_path.py
      test_qe_core.py
      test_simulators_core.py
      test_evaluators_core.py
      test_boundary_contracts.py  # architecture boundary enforcement
    expensive/               # slow tests, not in default gate
    quarantine/              # broken tests pending fix

  out/                       # committed generated outputs

  archive/
    handoff/                 # frozen handoff packs
    ref/                     # reference spreadsheets and docs
    legacy/                  # demoted old code and tests
```

Small `__init__.py` package plumbing files are allowed only where mechanically required.

### Input inventory control

`input/` is a locked foundation layer and its direct-file inventory must remain explicit.
Allowed direct files are:

- `ids_parser.py`
- `loader.py`
- `manual_inputs.contract.yaml`
- `manual_inputs.yaml`
- `runtime_state.py`
- `state_builder.py`
- `state_types.py`

No new direct files may be added under `input/` without updating this inventory and
the matching enforcement test.

### QE inventory control

`qe/` is allowed to be broader than most layers, but its direct-file inventory must remain explicit.
It is split into three categories:

1. Foundation core
   - `shared_runtime_context.py`
   - `contracts.py`
   - `models.py`
   - `query_routing.py`
   - `stat_input_compiler.py`
   - `materializer.py`
   - `kernel.py`
   - `routing.py`
   - `publication.py`

Explicit report/compat boundary:
- `stat_resolution.py`

2. Support registries/loaders
   - `dependency_registry.py`
   - `consumer_registry.py`
   - `kb_surfaces.py`
   - `perk_tables.py`
   - `query_perk_compiler.py`
   - `query_state_mode_policy.py`

3. Bounded publisher modules
   - `query_currency_income.py`
   - `query_derived_composites.py`
   - `query_module_policy.py`
   - `workshop_stat_rows.py`

The bounded publisher modules are allowed as active files today, but they are the first
consolidation candidates if `qe/` needs to shrink further. No new direct files may be added
under `qe/` without updating this inventory and the matching enforcement test.

### Simulator inventory control

`simulators/` direct-file inventory must remain explicit.
Allowed direct files are:

- `__init__.py`
- `contracts.py`
- `incremental_cache_fingerprint.py`
- `incremental_cache_validator.py`
- `incremental_overlay_publisher.py`
- `incremental_parity_harness.py`
- `incremental_recalc_runtime.py`
- `incremental_subset_executor.py`
- `performance.py`
- `perk_timeline_generator.py`
- `perk_timeline_state.py`
- `perks.py`
- `progression.py`
- `run_executor.py`
- `runtime_consumer_executor.py`
- `scenario.py`
- `snapshot_resolver.py`
- `timing.py`
- `wave_progression_policy.py`

No new direct files may be added under `simulators/` without updating this inventory and
the matching enforcement test.

### App inventory control

`app/` direct-file inventory must remain explicit.
Allowed direct files are:

- `__init__.py`
- `display.py`
- `inspector_data.py`
- `models.py`
- `pipeline.py`
- `publication.py`
- `run_analysis.py`
- `run_stats.py`
- `streamlit_inspector.py`

No new direct files may be added under `app/` without updating this inventory and
the matching enforcement test.

---

## Layer contracts

### `input/`
**Owns:** imports, manual inputs, parsing, runtime-state assembly, one derived perk artifact.
**Must not own:** mechanic truth, QE logic, simulation, scoring, recommendations.

Locked-foundation rules:
- `input/` is the only active owner of manual input parsing.
- `input/` must not depend upward on `qe/`, `simulators/`, `evaluators/`, `advisors/`, or `app/`.
- `input/loader.py` must not hide simulator behavior or QE fallback logic.
- Derived artifacts under `input/derived/` must be deterministic and input-owned only.

### `kb/`
**Owns:** canonical mechanic truth, formulas, tables, notes/source trace.
**Must not own:** runtime execution.

### `qe/`
**Owns:** deterministic stat/query resolution, value contracts, routing, materialisation,
dependency registry, publication of sanctioned surfaces.
**Must not own:** simulation, evaluation, recommendation, orchestration.

Locked-foundation rules:
- Native family query/statbook APIs are the foundation surface for downstream runtime consumers.
- Any broad report snapshot path must be explicit and must not masquerade as the native foundation path.
- Compatibility/report resolution must not be on simulator-facing active paths.
- Contract naming is mandatory internally and in published artifacts, except at explicit normalization boundaries.
- The remaining `qe/routing.py -> qe/stat_resolution.py` seam is allowed only for:
  - `resolve_stats` as the explicit report/compat fallback entrypoint
- `qe/stat_resolution.py` is a report/compat module, not part of the locked native QE foundation core.
- No additional `qe.stat_resolution` symbols may be imported into active QE/runtime consumers without updating this document and the matching boundary test.

### `simulators/`
**Owns:** progression projection, timing projection, scenario projection.
**Must not own:** stat resolution truth, recommendation policy.
**Consumes:** QE outputs only (not legacy engine internals directly).

Locked-foundation rules:
- Simulator hot paths must use explicit requested-surface QE seams.
- Ordinary row/checkpoint execution must not call `ProgressionRecalcBridge.recompute()`.
- Simulator hot paths must not import `qe.stat_resolution` or broad report/compat resolver paths.
- Simulator hot paths must not depend on `app.pipeline` orchestration helpers.
- Broad family/reference materialisation is allowed only for explicit parity, migration, or report workflows, never as the default row/checkpoint path.

### Hot-path consumers
**Includes:** simulator row/checkpoint loops, optimizer candidate evaluation loops, advisor recommendation candidate sweeps.

Locked-foundation rules:
- Hot-path consumers must request explicit surfaces and keep QE cost proportional to the requested surfaces.
- Hot-path consumers must not call report/compat resolution in ordinary loops.
- Sanctioned hot-path seams must remain obvious in owner files and enforced by boundary tests.
- If a hot-path consumer needs a new seam, add the sanctioned seam first; do not route through an existing broad fallback path.

### `evaluators/`
**Owns:** scoring, objectives, comparisons, ranking.
**Must not own:** recommendation policy, input parsing, QE contracts.

### `advisors/`
**Owns:** recommendation policy, upgrade advice / next-step advice.
**Must not own:** raw scoring engines.
**Consumes:** evaluator outputs only.

### `app/`
**Owns:** orchestration only, CLI entrypoint, pipeline wiring, writing outputs, display formatting.
**Must not own:** domain logic.

Locked-foundation rules:
- `app/` must not read KB reference tables or ledgers directly.
- `app/` must not assemble dashboard/domain payloads from raw runtime fragments when a sanctioned lower-layer builder exists.
- `app/publication.py` is a thin persistence/render wrapper; publication payload assembly belongs to sanctioned lower-layer owners.

### Generated artifact contracts
Generated outputs are governed as distinct contracts. They must not be treated as interchangeable.

Committed bounded `out/` baseline:
- The sanctioned committed maintenance baseline under `out/` is the bounded `run_stats` subset:
  - `account_state.json`
  - `run_stats.json`
  - `run_stats_query_plan_start_of_run.json`
  - `run_stats_query_plan_max_progression.json`
  - `run_stats_query_rows_start_of_run.json`
  - `run_stats_query_rows_max_progression.json`
- These files are the committed review baseline for `app/run_stats.py`.
- `run_stats.json` is the deterministic product artifact in that baseline; volatile build/write timing telemetry belongs in `diagnostics.json`, not in the committed product payload.
- Do not assume the committed `out/` baseline also contains the richer analysis/debug/publication artifact set.

Local bounded `run_stats` support artifacts:
- `app/run_stats.py` may also emit local support artifacts such as:
  - `diagnostics.json`
  - `module_card_payloads.json`
- Those support artifacts are useful for local inspection, but they are not the sanctioned committed maintenance baseline unless governance is updated explicitly.

Temp/full pipeline artifacts:
- `execute_pipeline(...)` together with `write_core_outputs(...)` produces a richer temporary/full publication set for analysis, dashboards, verification, and debugging.
- That richer set includes dashboards, statbooks, verification reports, manifests, optimizer outputs, residue reports, and `pipeline_trace.json`.
- Treat those artifacts as temp/debug/publication outputs, not as the default committed maintenance baseline.

Ad hoc output directories:
- `out_analysis_check`, `out_direct`, `out_module_test`, `out_runpy_test`, and `out_script_test` are not sanctioned baseline surfaces.
- They must either be removed, ignored, archived, or explicitly governed. They must not persist as ambiguous residue.

### `tests/`
**Owns:** verification only.

### `archive/`
**Owns:** frozen history, old handoff packs, legacy code/docs, non-active references.
**Must never be imported by active code once a tranche is closed.**

---

## Dependency direction

```
app/
  → advisors/ → evaluators/ → simulators/ → qe/ → input/
                                                  → kb/
```

All layers may read `kb/` for mechanic truth.
No layer may import from `archive/` once its tranche is closed.
Tests import any active layer. Tests must not import `archive/`.

---

## Strict layer consumption rules

These rules are mandatory and must be treated as architecture truth:

- `input/` owns parsing/state assembly only.
- `kb/` owns mechanic truth only.
- `qe/` owns deterministic stat resolution.
- `simulators/` consume QE only.
- `evaluators/` consume simulator/QE outputs only.
- `advisors/` consume evaluator outputs only.
- `app/` orchestrates/renders only.
- `tests/` enforce architecture truth.

Any change that weakens these boundaries must update this document and the matching governance tests in `tests/shared/`.

---

## File survival rules

A file survives as active only if ALL are true:

1. **Clear layer** — belongs to exactly one layer above.
2. **Clear contract** — one primary responsibility.
3. **Non-duplicative** — not already covered by another active file.
4. **Proven necessity** — needed by the supported path or supported tests.

---

## Acceptance gates (post-T13 consolidation)

- `input/` is the canonical owner of runtime inputs/state.
- `kb/` remains the authoritative mechanic truth.
- `qe/` owns deterministic stat resolution and the stat input compiler.
- Simulators consume QE outputs only. No engine.* imports.
- Evaluators consume QE/simulator outputs. No engine.* or compilers.* imports.
- Advisors consume evaluator outputs.
- `app/` is thin orchestration only.
- Main CLI path passes.
- Core live tests pass (32 tests).
- No active imports from `archive/`, `engine`, `compilers`, `models`, `optimizer`, `parsers`, `registry`.
- One manual inputs file only (`input/manual_inputs.yaml`).
- One derived perk file only (`input/derived/perks_derived.json`).
- No duplicate active input locations.
- Boundary tests enforce all the above rules automatically.

## Foundation lock review criteria

Before major simulator expansion, `input/` and `qe/` must be treated as locked foundation layers.
That lock is only considered complete when all are true:

- their direct-file inventories are explicit and test-enforced
- ownership boundaries are explicit and test-enforced
- native QE runtime APIs are separated from any report-only path
- no supported runtime path relies on hidden compatibility or fallback semantics
- any remaining `qe/routing.py -> qe/stat_resolution.py` dependency is explicit, minimal, and test-enforced
- active naming matches the KB naming contract throughout the foundation spine
