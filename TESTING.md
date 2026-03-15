# Testing

## Core (default)

```bash
PYTHONPATH=. pytest
```

## Quarantine (explicit opt-in)

```bash
PYTHONPATH=. pytest tests
```

## KB conformance gates (v3)

```bash
python scripts/check_repo_map.py
python -m tower_sim.audit.naming_contract_check --ids tests/fixtures/tower-sim-data/_IDS.csv --strict
python scripts/generate_kb_drift_report.py --strict --output audit/kb_drift_report.json
pytest -q tests/test_v3_kb_access.py tests/test_v3_stat_input_compiler.py tests/test_kb_drift_report.py
```
