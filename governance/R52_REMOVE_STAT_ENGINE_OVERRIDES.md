# R52 Remove stat-engine overrides for Wall HP and Free Upgrades

Decision:
- Removed the stat-engine phase-3 exact override path for `canonical_stat::wall_hp`.
- Removed the stat-engine phase-3 exact override path for the three free-upgrade canonicals:
  - `canonical_stat::free_attack_upgrade_chance_pct`
  - `canonical_stat::free_defense_upgrade_chance_pct`
  - `canonical_stat::free_utility_upgrade_chance_pct`

Reason:
- These were explicit hard-coded override paths inside `engine/stat_engine.py`.
- Canonical stats must resolve from contributor routing and normal engine behavior rather than publish-time or post-resolution exact overrides.

Verification:
- `pytest -q` passed after removal.
- `python run_stats.py --state-mode max_progression --out out` passed after removal.
