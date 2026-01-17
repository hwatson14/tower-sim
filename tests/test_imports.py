import importlib
import sys
from pathlib import Path


def test_imports_smoke():
    """Basic smoke test: the baseline package should import without side effects.

    Works for raw source checkouts (no install) by adding repo root to sys.path.
    """
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))

    modules = [
        "tower_sim",
        "tower_sim.sources",
        "tower_sim.ids",
        "tower_sim.free_upgrades",
        "tower_sim.workshop_progression",
        "tower_sim.wave_engine",
        "tower_sim.enemy_tables",
        "tower_sim.modules_library",
        "tower_sim.modules",
        "tower_sim.assist_efficiency",
        "tower_sim.wiki.cards",
        "tower_sim.wiki.labs",
        "tower_sim.wiki.labs_formula",
        "tower_sim.wiki.perks",
        "tower_sim.wiki.labs_eals_ehls",
        "tower_sim.enemies.wave_damage_strict",
    ]
    for m in modules:
        importlib.import_module(m)
