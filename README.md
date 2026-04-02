# TowerSim

KB-aligned deterministic simulator and calculator stack for The Tower.

## Quick start

```bash
pip install -e .[dev]
python -m app.run_stats
pytest                # runs the live architecture gate (23 tests, ~3 min)
```

## Active architecture

```
input/          -- IDS parsing, runtime-state assembly, manual inputs
qe/             -- deterministic stat/query resolution (AUTHORITY)
simulators/     -- progression and timing projection
evaluators/     -- scoring, comparison, objective definitions
advisors/       -- lab advisory, upgrade advice
app/            -- thin CLI entrypoint + pipeline wiring
kb/             -- authoritative mechanics, tables, contracts
```

Dependency direction:
```
app/ → advisors/ → evaluators/ → simulators/ → qe/ → input/
                                                     → kb/
```

Strict consumption rules:
- `input/` owns parsing/state assembly only.
- `kb/` owns mechanic truth only.
- `qe/` owns deterministic stat resolution.
- `simulators/` consume QE only.
- `evaluators/` consume simulator/QE outputs only.
- `advisors/` consume evaluator outputs only.
- `app/` orchestrates/renders only.
- `tests/` enforce architecture truth.

## Default test gate

```bash
pytest                                                          # live gate: 23 tests, ~3 min
pytest tests/ -m 'not slow and not expensive and not quarantine'  # legacy non-slow suite: ~416 tests
pytest tests/ -m slow                                           # slow integration tests
pytest tests/ -m expensive                                      # expensive parity tests
```

## Key files

- `app/run_stats.py` — CLI entrypoint (argparse)
- `app/pipeline.py` — orchestration: input → qe → evaluators → out
- `app/display.py` — output display formatting
- `qe/` — Query Engine authority
- `input/manual_inputs.yaml` — manual advisory assumptions
- `input/imports/` — IDS/Progress/EP_Export CSVs
- `out/` — committed generated outputs consumed by some tests
- `ACTIVE_TRANCHE.md` — tranche execution history
- `ARCHITECTURE.md` — target layer model
- `REPO_INDEX.yaml` — file-status ledger

## Archive and authority

This repository’s authoritative implementation lives on `main`.

Historical handoff material, deprecated references, legacy snapshots, and bulky provenance artifacts do not live on the active implementation surface. They are non-authoritative and must not be treated as current code, runtime truth, or active execution instructions.

Rules of thumb:
- `main` is the only implementation authority.
- Archived material is for provenance, reconstruction, and historical context only.
- Archived content must not be imported, referenced by runtime code, or used as an active instruction source.
- Anything revived from archive must be reviewed and reintroduced deliberately as fresh work.

If archived material conflicts with active code, contracts, or tests, prefer the active implementation surface and resolve the mismatch explicitly.

## Transitional state

There is no active root-level `run_stats.py` transitional dependency on this branch.
The active CLI entrypoint is `app/run_stats.py`, and runtime/domain ownership follows the
layer model documented in `ARCHITECTURE.md`.
