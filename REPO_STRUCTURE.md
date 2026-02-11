> **Role:** Explanatory index of repository structure.

# Repository Structure

## Allowed top-level folders
- `tower_sim/`: importable Python library code only. **No generated outputs** (md/json/yaml) live here.
- `tables/`: authoritative immutable tables (CSV/TSV/JSON), including cached wiki tables.
- `tables/`: large evidence locker (Step1 dumps, source snapshots). Treated as read-only.
- `audit/`: human-facing audits, comparisons, cleanup ledgers, and optional generated reports.
- `tests/`: primary test suite.
- `tests/`: quarantined legacy tests (not collected by default).
- `scripts/`: thin command-line helpers.

## Package layout (`tower_sim/`)
The importable package maps to the architecture planes and contains Python-only modules.

### Ownership map (canonical planes)
- `loaders/`: IO + parsing only (source ingestion, CSV readers)
- `libs/`: deterministic table interpreters and reference tables
- `engines/`: mechanics engines (no IO)
- `evaluators/`: objective evaluators
- `run/`: orchestration (ProblemSpec, wiring, run context)

### Supporting packages
- `registry/`: canonical IDs, stat registry, enums, validation (shared by all planes)
- `util/`: shared helpers (types, errors, validation)
- `audit/`: audit tooling code only (no outputs)

## Root documents
- `README.md`, `PROJECT_INTENT.md`, `GAME_OVERVIEW.md`, `ARCHITECTURE.md`, `TESTING.md`, `CONTRIBUTING.md`
- `REPO_MAP.yaml`: authoritative repo layout rules.
- `REPO_STRUCTURE.md`: human-readable structure overview.

## No outputs in `tower_sim/`
Generated reports and artefacts must live under `audit/` (or remain uncommitted). Do not
check generated markdown/json/yaml into `tower_sim/`.

## Enforcement
Structure and naming rules are enforced by `scripts/check_repo_map.py` and covered by
`tests/test_repo_map.py`. Update `REPO_MAP.yaml` intentionally when adding new files.
See `CONTRIBUTING.md` → "File creation policy (Edit existing first)" for governance.
