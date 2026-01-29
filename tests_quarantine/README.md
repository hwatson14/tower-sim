# Quarantined tests

These tests are excluded from the default suite because they currently rely on
known-broken or incomplete mechanics.

## Why quarantined
- `test_max_wave_evaluator.py` and `test_run_api.py` depend on evaluators that are
  still being wired for deterministic end-to-end runs.

## How to run
```bash
PYTHONPATH=. pytest tests_quarantine
```
