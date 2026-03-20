# R04 Output refresh and closure note

## Key finding
The earlier `cash_kill_multiplier` formula-contract "hydration" issue was not a broken ledger-to-output path.
It was an **output-path freshness issue**.

- `run_stats.py` writes to `output/` by default.
- Earlier audit inspection was reading stale files under `out/`.
- After rerunning `python run_stats.py` and inspecting `output/`, `cash_kill_multiplier` correctly emits:
  - `formula_class: generic_validated`
  - `publish_policy: allow`
  - `compare_policy: normal`

## Current verified consequences
The latest upstream v90 implementation claims for the previously open tail are now supported by live generated output in `output/`:

- `canonical_stat::tower_land_mine_damage` -> resolved
- `mechanic_param::module.orbital_augment.electron_count` -> resolved

## Remaining caution
Legacy directories such as `out/` still exist in the package and can contain stale snapshots.
For this audit rail, the canonical regenerated outputs are the files under `output/` produced by the current `run_stats.py` default path.

## Recommended operational rule
For all future verification in this rail:
1. rerun `python run_stats.py`
2. inspect `output/`
3. treat legacy `out/` folders as historical only unless deliberately refreshed
