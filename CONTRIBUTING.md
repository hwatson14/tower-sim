# Contributing

Thanks for contributing to TowerSim. Please keep changes aligned with the
architecture contract and repo hygiene rules.

## Structure rules
- **Do not** place generated reports, markdown artefacts, or JSON/YAML outputs in
  `tower_sim/`. Library code only.
- Authoritative tables live in `tables/`.
- Human-facing audits and comparison reports live in `audit/`.
- Large reference dumps live in `tables/`.
- Quarantined tests go in `tests/`.

See `REPO_STRUCTURE.md` for the full allowed tree.

## File creation policy (Edit existing first)
- Default to **modifying an existing module/file** instead of creating a new one.
- Before creating a new file, you **must**:
  - List the existing files you checked and why they were insufficient.
  - Justify the new file’s placement against the `ARCHITECTURE.md` planes.
  - Update `REPO_MAP.yaml` if the repo contract changes.
- **Codex and contributors must follow this policy; fail closed if unsure.**

### PR checklist (paste into PR description)
- [ ] Searched for an existing file to edit (list candidates and why insufficient).
- [ ] New files justified (why new file, why location).
- [ ] `REPO_MAP.yaml` updated if required.
- [ ] No duplicate concepts introduced.

## Testing
```bash
PYTHONPATH=. pytest
```

Quarantined tests (explicit opt-in):
```bash
PYTHONPATH=. pytest tests
```
