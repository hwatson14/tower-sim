# TowerSim

KB-aligned deterministic simulator and calculator stack for The Tower.

## Quick start

```bash
pip install -e .[dev]
python run_stats.py   # or: python -m app.run_stats
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
- `run_stats.py` — legacy domain helper library (bounded transitional; used by pipeline for domain builders)
- `qe/` — Query Engine authority
- `input/manual_inputs.yaml` — manual advisory assumptions
- `input/imports/` — IDS/Progress/EP_Export CSVs
- `out/` — committed generated outputs consumed by some tests
- `ACTIVE_TRANCHE.md` — tranche execution history
- `ARCHITECTURE.md` — target layer model
- `REPO_INDEX.yaml` — file-status ledger

## Transitional state

- `run_stats.py` domain builders (~34 functions) are imported by `app/pipeline.py` as a bounded transitional dependency. These are domain-layer functions (audit builders, compare matrices, gap analysis) pending extraction in a future pass.
- `engine/` shims re-export from active layers for legacy test backward-compat.
- `models/` shims re-export from `qe.models`.
- `optimizer/scorer.py`, `optimizer/path_ranker.py` are shims → `evaluators/`.
