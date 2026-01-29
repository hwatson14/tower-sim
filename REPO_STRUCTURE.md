# Repository Structure

## Allowed top-level folders
- `tower_sim/`: importable Python library code only. **No generated outputs** (md/json/yaml) live here.
- `tables/`: authoritative immutable tables (CSV/TSV/JSON), including cached wiki tables.
- `reference/`: large evidence locker (Step1 dumps, source snapshots). Treated as read-only.
- `audit/`: human-facing audits, comparisons, cleanup ledgers, and optional generated reports.
- `tests/`: primary test suite.
- `tests_quarantine/`: quarantined legacy tests (not collected by default).
- `scripts/`: thin command-line helpers.

## Package layout (`tower_sim/`)
The importable package maps to the architecture planes and contains Python-only modules:

- `run/`: orchestration (ProblemSpec, wiring, evaluators)
- `registry/`: canonical IDs, stat registry, enums, validation
- `loaders/`: IO + parsing only
- `libs/`: deterministic table interpreters
- `engines/`: mechanics engines (no IO)
- `evaluators/`: objective evaluators
- `audit/`: audit tooling code only (no outputs)
- `util/`: shared helpers (types, errors, validation)

## Root documents
- `README.md`, `ARCHITECTURE.md`, `TESTING.md`, `CONTRIBUTING.md`
- `REPO_MAP.yaml`: authoritative repo layout rules.
- `REPO_STRUCTURE.md`: human-readable structure overview.

## No outputs in `tower_sim/`
Generated reports and artefacts must live under `audit/` (or remain uncommitted). Do not
check generated markdown/json/yaml into `tower_sim/`.

## Enforcement
Structure and naming rules are enforced by `scripts/check_repo_map.py` and covered by
`tests/test_repo_map.py`. Update `REPO_MAP.yaml` intentionally when adding new files.
