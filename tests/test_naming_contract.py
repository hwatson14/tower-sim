from __future__ import annotations

import pytest

from tower_sim.registry.naming_contract import (
    alias_to_stat_id_map,
    named_entity_alias_maps,
    required_repo_stat_ids,
    resolve_named_entity,
    resolve_stat_id,
    unsupported_or_unmapped_items,
    validate_catalog_contract,
    validate_named_entity_coverage,
    validate_registry_parity,
)
from tower_sim.registry.stat_registry import default_registry


def test_repo_naming_contract_covers_all_registry_stat_ids() -> None:
    parity_errors = validate_registry_parity(default_registry())
    assert parity_errors == ()

    mapped = set(alias_to_stat_id_map().values())
    required = set(required_repo_stat_ids())
    assert required.issubset(mapped)


def test_repo_naming_contract_resolves_known_ids_display_names_and_aliases() -> None:
    assert resolve_stat_id("tower_hp") == "tower_hp"
    assert resolve_stat_id("Health") == "tower_hp"
    assert resolve_stat_id("HPregen") == "tower_regen"
    assert resolve_stat_id("Wall Regen") == "wall_regen"


def test_repo_naming_contract_raises_for_unknown_alias() -> None:
    with pytest.raises(KeyError, match="Unmapped IDS/display alias"):
        resolve_stat_id("Unknown Stat Name")


def test_named_entity_contract_has_all_core_categories() -> None:
    assert validate_catalog_contract() == ()

    errors = validate_named_entity_coverage()
    assert errors == ()

    maps = named_entity_alias_maps()
    expected_categories = {
        "workshop",
        "cards",
        "labs",
        "uws",
        "uw_tracks",
        "modules",
        "module_substats",
        "bots",
        "bot_attributes",
    }
    assert expected_categories.issubset(maps.keys())


def test_named_entity_contract_resolves_representative_paths() -> None:
    assert resolve_named_entity("workshop", "Health Regen") == "Health Regen"
    assert resolve_named_entity("cards", "Plasma Cannon") == "CARD_PLASMA_CANNON"
    assert resolve_named_entity("labs", "Defense %") == "LAB_DEFENSE_PERCENT"
    assert resolve_named_entity("uws", "Black Hole") == "UW_BLACK_HOLE"
    assert resolve_named_entity("uw_tracks", "Black Hole:Duration") == "Black Hole.Duration"
    assert resolve_named_entity("modules", "Galaxy Compressor") == "Galaxy Compressor"
    assert resolve_named_entity("module_substats", "Armor:Recovery Package Chance") == "Recovery Package Chance"
    assert resolve_named_entity("bots", "Golden Bot") == "Golden Bot"
    assert resolve_named_entity("bot_attributes", "Golden Bot:Bonus") == "Golden Bot.Bonus"
    assert resolve_named_entity("labs", "Black Hole Coin Bonus") == "LAB_BLACK_HOLE_COINS_BONUS"
    assert resolve_named_entity("labs", "Damage / Meter") == "LAB_DAMAGE_PER_METER"
    assert resolve_named_entity("labs", "Missile Radius") == "LAB_MISSILES_RADIUS"


def test_named_entity_contract_raises_for_unknown_category_alias() -> None:
    with pytest.raises(KeyError, match="Unknown naming category"):
        resolve_named_entity("unknown", "x")
    with pytest.raises(KeyError, match="Unmapped alias"):
        resolve_named_entity("workshop", "NotARealWorkshopName")


def test_unsupported_or_unmapped_items_flags_contract_drift() -> None:
    failures = unsupported_or_unmapped_items(
        [
            "workshop_unsupported:Health",
            "workshop_mapping:Wall Regen",
            "workshop_unsupported:Not A Real Stat",
        ]
    )
    assert "workshop_unsupported:Health->tower_hp" in failures
    assert "workshop_mapping:Wall Regen->wall_regen" in failures
    assert "workshop_unsupported:Not A Real Stat->unmapped" in failures
