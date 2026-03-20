# R53 No canonical stat-engine override guard

Added a regression guard that fails if named canonical override helpers/calls reappear in `engine/stat_engine.py`.

Guarded snippets:
- `def _apply_phase3_exact_overrides(`
- `def _apply_exact_free_upgrade_formula(`
- `_apply_phase3_exact_overrides(rows)`
- `_apply_exact_free_upgrade_formula(rows)`

This does not ban normal resolver logic or routed support promotion. It specifically bans bespoke post-resolution correction helpers for named canonicals.
