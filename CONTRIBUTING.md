# Contributing

Thanks for contributing to TowerSim. Please keep changes aligned with the
architecture contract and repo hygiene rules.

## Structure rules
- **Do not** place generated reports, markdown artefacts, or JSON/YAML outputs in
  `tower_sim/`. Library code only.
- Authoritative tables live in `tables/`.
- Human-facing audits and comparison reports live in `audit/`.
- Large reference dumps live in `reference/`.
- Quarantined tests go in `tests_quarantine/`.

See `REPO_STRUCTURE.md` for the full allowed tree.

## Testing
```bash
PYTHONPATH=. pytest
```

Quarantined tests (explicit opt-in):
```bash
PYTHONPATH=. pytest tests_quarantine
```
