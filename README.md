# TowerSim Codex Baseline

This ZIP is a **clean baseline** for moving TowerSim into Codex.

It contains:
- `ARCHITECTURE.md`: frozen architecture contract and build plan
- `IMPLEMENTATION_STATUS.md`: truthful audit of what exists vs what is missing
- `AGENTS.md`: rules for Codex/agents (deterministic, fail-closed, no invented mechanics)
- `REPO_STRUCTURE.md`: allowed top-level folders and usage rules
- `tower_sim/`: Python package (library code only)
- `tables/`: authoritative tables + cached wiki tables
- `audit/`: audit reports and cleanup ledgers
- `tests/` and `tests_quarantine/`: test suites

## What this is (and isn't)
- This is **not yet a full simulator** (no typed `_IDS` → `IdsState`, no StatBook, no boss model).
- It is the most coherent salvage base we found and is intended to be extended via PRs in Codex.

## Recommended environment
- Python 3.11+
- `pip install -e .[dev]`
- `PYTHONPATH=. pytest`
- `python -m tower_sim.loaders.wiki.audit_cache_tables`

## Repo audit
Run the repository audit to validate naming integrity, registry references, table presence, and module completeness:

```bash
python -m tower_sim.audit.repo_audit --json audit.json --markdown audit.md
```

Strict mode returns exit code 2 when failures are present:

```bash
python -m tower_sim.audit.repo_audit --strict
```

## Data dependency
This repo expects CSV snapshots from `hwatson14/tower-sim-data`.
Recommended approach: add it as a git submodule (pinned SHA) under `reference/tower-sim-data`.

## First Codex task
Implement typed `_IDS.csv` parsing to `IdsState` (raw values only), with unit tests.
See `ARCHITECTURE.md` for full contract.
