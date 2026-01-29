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
        "tower_sim.loaders.sources",
        "tower_sim.loaders.ids",
        "tower_sim.engines.free_upgrades",
        "tower_sim.engines.workshop_progression",
        "tower_sim.engines.wave_engine",
        "tower_sim.libs.enemy_tables",
        "tower_sim.libs.modules_library",
        "tower_sim.engines.modules",
        "tower_sim.libs.assist_efficiency",
        "tower_sim.engines.stat_engine",
        "tower_sim.loaders.wiki.cards",
        "tower_sim.loaders.wiki.labs",
        "tower_sim.loaders.wiki.labs_formula",
        "tower_sim.loaders.wiki.perks",
        "tower_sim.loaders.wiki.labs_eals_ehls",
        "tower_sim.libs.wave_damage_strict",
    ]
    for m in modules:
        importlib.import_module(m)
