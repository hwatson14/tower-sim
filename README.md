# TowerSim

TowerSim is the active working repository for a deterministic, KB-aligned simulator and calculator stack for *The Tower*.

This is a private personal project owned and used by Harry. The intended operating model is Harry directing work and Codex making constrained changes inside the active repo surface.

## Purpose

This repo exists to:

- maintain a trustworthy deterministic simulation and calculation foundation
- keep mechanics aligned to the active KB and accepted canonical tables
- support reproducible rebuilds, audits, and targeted evaluation
- provide a controlled active surface for Codex-assisted development

This repo is not assumed to be globally complete. If an area is incomplete, staged, or temporary, that must be stated explicitly rather than implied away.

## Truth model

This repository uses three distinct truth layers.

### Mechanic truth
Mechanic truth is owned by the active KB and accepted canonical tables.

This includes:

- formulas
- stat composition
- timing behaviour
- progression rules
- scenario rules
- mechanic ownership
- canonical contributor wiring where defined by the KB

For mechanics, the KB and accepted canonical tables are the source of truth.

### State truth
State truth is owned by accepted active input-state surfaces.

This includes:

- account values
- labs
- workshop levels
- modules
- cards
- equipped loadouts
- inventory state
- scenario inputs
- designated active exports used as inputs

These define the state the simulator/calculator operates on. They do not by themselves define mechanics.

Generated outputs, audit artifacts, and snapshots do not automatically become state truth unless explicitly designated as active input surfaces.

### Implementation truth
Implementation truth is the repo’s current executable realization of mechanic truth and state truth.

Code is authoritative for what the repo currently does.
Code is not automatically authoritative for what is mechanically true.

If implementation and mechanic truth disagree, treat that as a surfaced defect.

## KB alignment rule

This is a KB-aligned repo.

That means:

- mechanic-affecting behaviour must align to the active KB and accepted canonical tables
- implementation must conform to mechanic truth or explicitly declare a temporary accepted model
- existing code, passing tests, matching goldens, parity checks, or prior outputs do not by themselves establish mechanic truth

If a mechanic is not supported by the current accepted KB, it must not be presented as canonical truth.

## Temporary accepted models

Temporary accepted models are allowed only when they are:

- explicitly identified as temporary
- narrowly scoped
- clearly separated from KB truth
- easy to locate and replace later
- validated as far as possible without overstating certainty

Temporary accepted models are implementation devices, not mechanic truth.

## Authority model

Use the following interpretation model:

1. Active KB and accepted canonical tables define mechanic truth.
2. Accepted active input-state surfaces define state truth.
3. Active implementation defines current executable behaviour.
4. Tests, parity checks, audits, and golden outputs validate consistency and regression only.
5. Root governance docs define repo rules, ownership boundaries, and interpretation rules.
6. Archive material is reference-only unless explicitly recovered and promoted.

If these surfaces disagree, surface the mismatch explicitly.

## Active vs archive boundary

`archive/` is non-authoritative by default.

Archive exists for:

- historical reference
- comparison
- targeted recovery
- donor extraction when explicitly reviewed

Archive is not part of the normal active implementation surface.

`tower-sim-data/` is active operational surface and must remain outside archive. It contains live automated exports and related data dependencies used by the active repo.

## Editing model

This repository is intended to be:

- used by Harry
- edited only by Codex under explicit constraints
- governed by the active root docs and active ownership boundaries

Machine-operating rules for Codex live in `AGENTS.md`.

## Quick start

Insert the canonical commands below once finalised.

### Setup

```bash
python -m pip install -e .[dev]
```

### Main rebuild

```bash
python run_stats.py
```

### Tests

```bash
pytest
```

See `TESTING.md` for detailed validation expectations and additional commands.

## Repo layout

High-level intent of the main repo surfaces:

- active implementation code: current simulator, calculator, engine, and runtime ownership surfaces
- KB and canonical tables: accepted mechanic backing
- input-state surfaces: account, inventory, export-input, and scenario input data
- tests and goldens: regression detection, parity, and validation
- `tower-sim-data/`: live export and operational data dependency surface
- root governance docs: repo rules, active-path interpretation, and validation guidance
- `archive/`: non-authoritative historical or recovery-only material

See `AUTHORITATIVE_PATHS.md` for the current active-path map.

## Root docs

- `README.md` — repo purpose, truth model, operator orientation, active versus archive boundary
- `AGENTS.md` — mandatory rules for Codex behaviour and patch control
- `TESTING.md` — validation commands and expectations
- `AUTHORITATIVE_PATHS.md` — active ownership boundaries and non-authoritative surfaces
