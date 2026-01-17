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
        "towersim",
        "towersim.sources",
        "towersim.ids",
        "towersim.free_upgrades",
        "towersim.workshop_progression",
        "towersim.wave_engine",
        "towersim.enemy_tables",
        "towersim.modules_library",
        "towersim.modules",
        "towersim.assist_efficiency",
        "towersim.wiki.cards",
        "towersim.wiki.labs",
        "towersim.wiki.labs_formula",
        "towersim.wiki.perks",
        "towersim.wiki.labs_eals_ehls",
        "towersim.enemies.wave_damage_strict",
    ]
    for m in modules:
        importlib.import_module(m)
