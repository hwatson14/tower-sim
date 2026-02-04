import sys
from pathlib import Path


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.loaders.ids_parser import parse_ids  # noqa: E402


def test_parse_ids_fixture_sections() -> None:
    ids_raw = parse_ids()

    assert ids_raw.raw_sections["Labs"]
    assert ids_raw.raw_sections["WS"]
    assert ids_raw.raw_sections["Modules"]
    assert ids_raw.raw_sections["UWs"]
    assert ids_raw.raw_sections["Cards"]
    assert ids_raw.raw_sections["Bots"]
    assert ids_raw.raw_sections["Relics"]
    assert ids_raw.raw_sections["Vault"]
    assert ids_raw.raw_sections["Themes & Songs"]
    assert ids_raw.raw_sections["Guardians"]
    assert ids_raw.raw_sections["Player & Stuff"]
