# TowerSim Codex Baseline

This ZIP is a **clean baseline** for moving TowerSim into Codex.

It contains:
- `ARCHITECTURE.md`: frozen architecture contract and build plan
- `IMPLEMENTATION_STATUS.md`: truthful audit of what exists vs what is missing
- `AGENTS.md`: rules for Codex/agents (deterministic, fail-closed, no invented mechanics)
- `towersim/`: Python package (salvaged baseline) including progression + skip mapping + wiki ingest utilities
- `tests/`: minimal smoke tests

## What this is (and isn't)
- This is **not yet a full simulator** (no typed `_IDS` → `IdsState`, no StatBook, no boss model).
- It is the most coherent salvage base we found and is intended to be extended via PRs in Codex.

## Recommended environment
- Python 3.11+
- `pip install -e .[dev]`
- `pytest`

## Data dependency
This repo expects CSV snapshots from `hwatson14/tower-sim-data`.
Recommended approach: add it as a git submodule (pinned SHA) and point the DataLoader at it.

## First Codex task
Implement typed `_IDS.csv` parsing to `IdsState` (raw values only), with unit tests.
See `ARCHITECTURE.md` for full contract.
