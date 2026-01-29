from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_RUNTIME_TABLES = {
    "bc_heat": ["battle_conditions.csv", "heat.csv"],
    "wave_damage": ["tier_wave_damage.csv", "tournament_wave_damage.csv"],
    "tournament_boss_freq": ["tournament_more_bosses_static.csv"],
    "dag_inputs": ["tiers.csv", "dag.json"],
}

EXCLUDED_DIRS = {"reference", "tests"}


def _is_runtime_path(path: Path) -> bool:
    return not any(part in EXCLUDED_DIRS for part in path.parts)


def _find_runtime_matches(filename: str) -> list[Path]:
    return [path for path in ROOT.rglob(filename) if _is_runtime_path(path)]


def test_required_runtime_tables_present() -> None:
    missing: dict[str, list[str]] = {}

    for category, filenames in REQUIRED_RUNTIME_TABLES.items():
        for filename in filenames:
            if not _find_runtime_matches(filename):
                missing.setdefault(category, []).append(filename)

    assert not missing, (
        "Missing required runtime tables (expected outside reference/ and tests/): "
        f"{missing}"
    )
