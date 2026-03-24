"""Tests for registry/naming_contract.py.

Adapted from archive/tests/test_naming_contract.py.

Key adaptations vs. reference archive:
  - No default_registry() dependency; validate_registry_parity() is arg-free.
  - Module unique names are snake_case (from mechanic-params.yaml domains),
    not display-name strings from the archive's modules_library.
  - Bot attribute keys are mechanic-params.yaml param key suffixes
    (e.g. "bonus_multiplier"), not shortened display names (e.g. "Bonus").
  - UW track names match ultimate-weapon-track-ladders.csv track_name column.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from registry.naming_contract import (
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


# ---------------------------------------------------------------------------
# Stat registry parity
# ---------------------------------------------------------------------------

def test_repo_naming_contract_covers_all_registry_stat_ids() -> None:
    """Every canonical stat ID must appear in the alias map (no missing IDs)."""
    parity_errors = validate_registry_parity()
    assert parity_errors == (), f"Parity errors: {parity_errors}"

    mapped = set(alias_to_stat_id_map().values())
    required = set(required_repo_stat_ids())
    missing = required - mapped
    assert missing == set(), f"Required IDs missing from alias map: {missing}"


def test_repo_naming_contract_resolves_known_ids_display_names_and_aliases() -> None:
    """Core aliases must resolve to their canonical stat IDs."""
    # Direct canonical ID round-trips
    assert resolve_stat_id("tower_hp") == "tower_hp"
    assert resolve_stat_id("wall_regen") == "wall_regen"
    assert resolve_stat_id("tower_supercrit_multiplier") == "tower_supercrit_multiplier"
    # Explicit human-readable aliases
    assert resolve_stat_id("Health") == "tower_hp"
    assert resolve_stat_id("HPregen") == "tower_regen"
    assert resolve_stat_id("Wall Regen") == "wall_regen"
    assert resolve_stat_id("hp") == "tower_hp"
    assert resolve_stat_id("defence %") == "tower_defense_pct"
    assert resolve_stat_id("defense") == "tower_defense_pct"
    assert resolve_stat_id("max amount") == "max_recovery_multiplier"
    # Deprecated-transition alias
    assert resolve_stat_id("coin kill bonus") == "coins_per_kill_bonus"
    # Super-crit normalisation
    assert resolve_stat_id("super_crit_mult") == "tower_supercrit_multiplier"


def test_repo_naming_contract_raises_for_unknown_alias() -> None:
    with pytest.raises(KeyError, match="Unmapped IDS/display alias"):
        resolve_stat_id("Unknown Stat Name XYZ")


# ---------------------------------------------------------------------------
# Named entity categories
# ---------------------------------------------------------------------------

def test_named_entity_contract_has_all_core_categories() -> None:
    """Catalog must be valid; all nine entity categories must be populated."""
    assert validate_catalog_contract() == (), (
        f"Catalog errors: {validate_catalog_contract()}"
    )

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
    # Every category must contain at least one entry.
    for cat in expected_categories:
        assert maps[cat], f"Category '{cat}' is empty"


def test_named_entity_contract_resolves_representative_paths() -> None:
    """Spot-check concrete resolution paths across all categories."""
    # Workshop – concrete rows from WORKSHOP_IDS_TO_CONTRIBUTOR
    assert resolve_named_entity("workshop", "Health") == "Health"
    assert resolve_named_entity("workshop", "Health Regen") == "Health Regen"
    assert resolve_named_entity("workshop", "Wall Rebuild") == "Wall Rebuild"
    assert resolve_named_entity("workshop", "Package Chance") == "Package Chance"

    # Cards – from catalog.yaml
    assert resolve_named_entity("cards", "Plasma Cannon") == "CARD_PLASMA_CANNON"
    assert resolve_named_entity("cards", "Damage") == "CARD_DAMAGE"
    assert resolve_named_entity("cards", "CC") == "CARD_CRITICAL_CHANCE"

    # Labs – from catalog.yaml
    assert resolve_named_entity("labs", "Defense %") == "LAB_DEFENSE_PERCENT"
    assert resolve_named_entity("labs", "Wall Regen") == "LAB_WALL_REGEN"
    assert resolve_named_entity("labs", "Damage / Meter") == "LAB_DAMAGE_PER_METER"
    assert resolve_named_entity("labs", "Missile Radius") == "LAB_MISSILES_RADIUS"

    # UWs – from catalog.yaml
    assert resolve_named_entity("uws", "Black Hole") == "UW_BLACK_HOLE"
    assert resolve_named_entity("uws", "BH") == "UW_BLACK_HOLE"
    assert resolve_named_entity("uws", "GT") == "UW_GOLDEN_TOWER"

    # UW tracks – pattern rows from uw track CSV (track_name column)
    assert resolve_named_entity("uw_tracks", "Black Hole:Duration") == "Black Hole.Duration"
    assert resolve_named_entity("uw_tracks", "Chain Lightning:Damage") == "Chain Lightning.Damage"

    # Modules – pattern rows from mechanic-params.yaml modules.uniques (snake_case names)
    assert resolve_named_entity("modules", "galaxy_compressor") == "galaxy_compressor"
    assert resolve_named_entity("modules", "amplifying_strike") == "amplifying_strike"

    # Module substats – slot type keys (concrete rows; full substat map is DEFERRED)
    assert resolve_named_entity("module_substats", "cannon") == "cannon"
    assert resolve_named_entity("module_substats", "armor") == "armor"

    # Bots – pattern rows from mechanic-params.yaml bot.* domains
    assert resolve_named_entity("bots", "Golden Bot") == "Golden Bot"
    assert resolve_named_entity("bots", "Flame Bot") == "Flame Bot"

    # Bot attributes – pattern rows (attr key = mechanic-params.yaml param suffix)
    assert resolve_named_entity("bot_attributes", "Golden Bot:bonus_multiplier") == (
        "Golden Bot.bonus_multiplier"
    )
    assert resolve_named_entity("bot_attributes", "Golden Bot:cooldown_seconds") == (
        "Golden Bot.cooldown_seconds"
    )


def test_named_entity_contract_raises_for_unknown_category_alias() -> None:
    with pytest.raises(KeyError, match="Unknown naming category"):
        resolve_named_entity("unknown_category", "x")
    with pytest.raises(KeyError, match="Unmapped alias"):
        resolve_named_entity("workshop", "NotARealWorkshopStatName")


# ---------------------------------------------------------------------------
# Named entity coverage
# ---------------------------------------------------------------------------

def test_named_entity_coverage_has_no_errors() -> None:
    errors = validate_named_entity_coverage()
    assert errors == (), f"Named entity coverage errors: {errors}"


# ---------------------------------------------------------------------------
# Unsupported/unmapped item detection
# ---------------------------------------------------------------------------

def test_unsupported_or_unmapped_items_flags_contract_drift() -> None:
    """Workshop items that are decisive combat stats must be flagged."""
    failures = unsupported_or_unmapped_items(
        [
            "workshop_unsupported:Health",           # maps → tower_hp (tower domain, decisive)
            "workshop_mapping:Wall Regen",           # maps → wall_regen (wall domain, decisive)
            "workshop_unsupported:Not A Real Stat",  # not in alias map → unmapped
        ]
    )
    assert "workshop_unsupported:Health->tower_hp" in failures
    assert "workshop_mapping:Wall Regen->wall_regen" in failures
    assert "workshop_unsupported:Not A Real Stat->unmapped" in failures
