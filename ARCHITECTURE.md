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
    loader.py                # loads and validates all inputs
    runtime_state.py         # assembles RuntimeState from inputs
    parsers.py               # raw CSV/JSON parsing helpers
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
    contracts.py             # stat-query value contracts
    models.py                # typed stat/query model structs
    routing.py               # query dispatch and routing
    materializer.py          # family baseline materialisation
    kernel.py                # core deterministic resolution kernel
    publication.py           # sanctioned surface publication
    dependency_registry.py   # dependency graph and invalidation

  simulators/
    progression.py           # progression projection
    timing.py                # timing/wave projection
    scenario.py              # scenario projection

  evaluators/
    scorer.py                # scoring engine
    objectives.py            # objective definitions
    compare.py               # comparison helpers
    ranker.py                # ranking and sorting

  advisors/
    recommendation_policy.py # policy rules for recommendations
    upgrade_advisor.py       # upgrade/next-step advice

  app/
    run_stats.py             # thin CLI entrypoint
    pipeline.py              # layer wiring only

  tests/
    conftest.py
    helpers.py
    live/
      test_main_path.py
      test_qe_core.py
      test_simulators_core.py
      test_evaluators_core.py
    expensive/               # slow tests, not in default gate
    quarantine/              # broken tests pending fix

  out/                       # committed generated outputs

  archive/
    handoff/                 # frozen handoff packs
    ref/                     # reference spreadsheets and docs
    legacy/                  # demoted old code and tests
```

Small `__init__.py` package plumbing files are allowed only where mechanically required.

---

## Layer contracts

### `input/`
**Owns:** imports, manual inputs, parsing, runtime-state assembly, one derived perk artifact.
**Must not own:** mechanic truth, QE logic, simulation, scoring, recommendations.

### `kb/`
**Owns:** canonical mechanic truth, formulas, tables, notes/source trace.
**Must not own:** runtime execution.

### `qe/`
**Owns:** deterministic stat/query resolution, value contracts, routing, materialisation,
dependency registry, publication of sanctioned surfaces.
**Must not own:** simulation, evaluation, recommendation, orchestration.

### `simulators/`
**Owns:** progression projection, timing projection, scenario projection.
**Must not own:** stat resolution truth, recommendation policy.
**Consumes:** QE outputs only (not legacy engine internals directly).

### `evaluators/`
**Owns:** scoring, objectives, comparisons, ranking.
**Must not own:** recommendation policy, input parsing, QE contracts.

### `advisors/`
**Owns:** recommendation policy, upgrade advice / next-step advice.
**Must not own:** raw scoring engines.
**Consumes:** evaluator outputs only.

### `app/`
**Owns:** orchestration only, CLI entrypoint, pipeline wiring, writing outputs.
**Must not own:** domain logic.

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

## File survival rules

A file survives as active only if ALL are true:

1. **Clear layer** — belongs to exactly one layer above.
2. **Clear contract** — one primary responsibility.
3. **Non-duplicative** — not already covered by another active file.
4. **Proven necessity** — needed by the supported path or supported tests.

---

## Acceptance gates (final)

- `input/` is the canonical owner of runtime inputs/state.
- `kb/` remains the authoritative mechanic truth.
- `qe/` owns deterministic stat resolution.
- Simulators consume QE outputs, not legacy engine code.
- Evaluators consume QE/simulator outputs.
- Advisors consume evaluator outputs.
- `app/` is thin orchestration only.
- Main CLI path passes.
- Core live tests pass.
- No active imports from `archive/`.
- One manual inputs file only (`input/manual_inputs.yaml`).
- One derived perk file only (`input/derived/perks_derived.json`).
- No duplicate active input locations.
