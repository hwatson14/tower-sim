# TowerSim

KB-aligned deterministic simulator and calculator stack for The Tower.

This repo is the cleaned working core intended for Codex-driven development. It contains active code, the full knowledge base, runtime inputs, validation surfaces, and committed generated outputs still consumed by tests.

## Quick start

```bash
pip install -e .[dev]
python run_stats.py
pytest
```

## Canonical layer model

The canonical program stack is:

1. Knowledge Base
2. Inputs
3. Query Engine
4. Simulators
5. Optimisers
6. Advisors

`AI_EXECUTION_PLAN.md` is the canonical whole-program plan. `ACTIVE_TRANCHE.md` defines the only tranche Codex should execute now, and `BURNDOWN.yaml` records delivery and verification state.

## Current execution pipeline

```text
parsers/ids_parser.py
→ compilers/account_state_compiler.py
→ compilers/stat_input_compiler.py
→ engine/stat_engine.py
→ optimizer/scorer.py
```

This pipeline is the current implementation path, not a contradictory architecture model. In canonical terminology, the runtime and event-model code in `engine/` is the current Simulator layer while `optimizer/` remains the current optimiser owner.

`run_stats.py` is the orchestration entrypoint. It compiles runtime state, emits output artifacts into `out/`, runs comparison and diagnostic routines, and formats current generated surfaces.

## Repo map

- `kb/` — authoritative mechanics, tables, contracts, notes, and ledgers
- `input/` — IDS export, loadout, perk policy inputs, and committed scenario inputs
- `parsers/` — raw IDS parsing
- `compilers/` — account-state and stat-input compilation
- `models/` — runtime data structures
- `engine/` — stat engine plus scoped subsystems
- `optimizer/` — scorer and path ranking
- `scripts/` — workflow helpers
- `templates/` — static assets required by geometry workflows/tests
- `tests/` — regression and contract suite
- `out/` — committed generated outputs used by active tests/workflows

## Scoped subsystems in `engine/`

- Geometry wall-contact fit pipeline
- Incremental recalc and progression runtime
- Boss wave engine
- Scenario and timing engine
- Perk timeline generator

## Notes on current shape

- The KB is the authoritative mechanics/data layer.
- `run_stats.py` remains a large orchestration surface by design in this phase.
- `compilers/stat_input_compiler.py` is the major routing hub for KB-backed stat composition.
- `out/` ships populated because some tests read committed artifacts directly.

## Expected workflow

1. update or inspect inputs and KB-backed code
2. run `python run_stats.py`
3. run targeted tests for touched surfaces
4. run `pytest` for release-level confidence

## Editing guidance

- Prefer editing existing owners over adding new layers.
- Keep mechanics aligned to KB sources.
- Remove stale references when retiring paths.
- Rebuild outputs when a change affects committed generated artifacts.

## Planning note

`AI_EXECUTION_PLAN.md` is the sole long-lived planning authority. Product principles, scope cuts, optimiser-family distinctions, trust labels, and representative user questions must live there instead of in a parallel roadmap file.

## Current handover goal

Codex should be able to open this repo and immediately see a coherent operating core rather than merged historical scaffolding.
