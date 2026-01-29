# Repository Structure

## Allowed top-level folders
- `tower_sim/`: importable Python library code only. **No generated outputs** (md/json/yaml) live here.
- `tables/`: authoritative immutable tables (CSV/TSV/JSON), including cached wiki tables.
- `reference/`: large evidence locker (Step1 dumps, source snapshots). Treated as read-only.
- `audit/`: human-facing audits, comparisons, cleanup ledgers, and optional generated reports.
- `tests/`: primary test suite.
- `tests_quarantine/`: quarantined legacy tests (not collected by default).
- `scripts/`: thin command-line helpers.

## Root documents
- `README.md`, `ARCHITECTURE.md`, `TESTING.md`, `CONTRIBUTING.md`

## No outputs in `tower_sim/`
Generated reports and artefacts must live under `audit/` (or remain uncommitted). Do not
check generated markdown/json/yaml into `tower_sim/`.
