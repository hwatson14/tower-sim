# Codex handoff: suspicious-panini tests worktree

## Source of truth
- Workspace zip: `suspicious-panini.zip`
- Baseline repo zip: `tower-sim-src.zip`
- Scope compared: `tests/` only

## Exact structural delta
- Active test files: **88 -> 73**
- Root-level `tests/test_*.py`: **79 -> 0**
- Path-level adds: **64**
- Path-level removals: **79**
- In-place modifications: **1** (`tests/conftest.py`)

## Resulting active folders
- `tests/app/` (4)
- `tests/evaluators/` (4)
- `tests/input/` (4)
- `tests/live/` (5)
- `tests/qe/` (17)
- `tests/quarantine/` (4)
- `tests/shared/` (11)
- `tests/simulators/` (24)

## Material changes
1. Root graveyard cleared; tests re-homed by owner domain.
2. Two merged replacement files created:
   - `tests/app/test_app_output_contracts.py`
   - `tests/input/test_input_typed_model_contracts.py`
3. `tests/conftest.py` modified to add both repo root and `tests/` to `sys.path`.
4. Post-move fix applied to `tests/app/test_app_display_formatting.py` after a failing `__module__` assertion due to `engine.display` re-exporting from `app.display`.

## Verification still needed
Claude usage ended while this was still running:

```bash
python -m pytest tests/ --ignore=tests/live --ignore=tests/quarantine -q --tb=short -m "not slow"
```

So the structure is real, but the final broad non-live/non-quarantine/non-slow verification is still unconfirmed.

## Recommended Codex task
1. Apply the tests-only patch from `tests_workspace.patch`.
2. Verify:
   - `python -m pytest tests/live -q`
   - `python -m pytest tests/ --ignore=tests/live --ignore=tests/quarantine -q --tb=short -m "not slow"`
   - `python -m pytest tests/qe/test_qe_surface_resolution_coverage.py tests/qe/test_stat_query_surface_registry.py -q`
3. If failures remain, fix only failures introduced by the migration; do not reopen broad test cleanup.
