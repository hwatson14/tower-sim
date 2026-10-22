from __future__ import annotations

from pathlib import Path

import pytest

from qe.module_reroll.ban_labs import (
    ban_lab_capacities_from_account_state,
    build_ban_lab_wiring,
    load_module_ban_lab_names,
)
from qe.module_reroll.domain import ModuleFamily
from qe.module_reroll.kb_loader import load_effect_specs

ROOT = Path(__file__).resolve().parents[3]


def _account_state_with_ban_labs() -> dict:
    return {
        "labs": {
            "Cannon Effect Bans": 2,
            "Armor Effect Bans": 1,
            "Generator Effect Bans": 0,
            "Core Effect Bans": 4,
        }
    }


def test_module_ban_lab_names_are_registry_owned_module_labs() -> None:
    names = load_module_ban_lab_names(ROOT)
    assert names == {
        ModuleFamily.CANNON: "Cannon Effect Bans",
        ModuleFamily.ARMOR: "Armor Effect Bans",
        ModuleFamily.GENERATOR: "Generator Effect Bans",
        ModuleFamily.CORE: "Core Effect Bans",
    }


def test_ban_lab_capacities_load_from_account_state_labs() -> None:
    capacities = ban_lab_capacities_from_account_state(_account_state_with_ban_labs(), repo_root=ROOT)
    assert capacities[ModuleFamily.CANNON].level == 2
    assert capacities[ModuleFamily.ARMOR].level == 1
    assert capacities[ModuleFamily.GENERATOR].level == 0
    assert capacities[ModuleFamily.CORE].level == 4
    assert capacities[ModuleFamily.CORE].source == "account_state.labs"


def test_selected_bans_are_validated_against_capacity_and_effect_pool() -> None:
    capacities = ban_lab_capacities_from_account_state(_account_state_with_ban_labs(), repo_root=ROOT)
    effects = load_effect_specs(ROOT)
    wiring = build_ban_lab_wiring(
        capacities,
        {"Cannon": ["Attack Speed", "Crit Factor"], "Core": ["Chrono Field - Duration"]},
        effects,
    )
    assert wiring.selected_ban_effect_ids[ModuleFamily.CANNON] == ("attack_speed", "crit.factor")
    assert wiring.ban_states[ModuleFamily.CORE].banned_effect_ids == frozenset({"chrono_field.duration"})


def test_selected_bans_over_lab_capacity_fail_closed() -> None:
    capacities = ban_lab_capacities_from_account_state(_account_state_with_ban_labs(), repo_root=ROOT)
    effects = load_effect_specs(ROOT)
    with pytest.raises(ValueError, match="Generator selected bans exceed Generator Effect Bans capacity"):
        build_ban_lab_wiring(capacities, {"Generator": ["Cash Bonus"]}, effects)


def test_selected_bans_must_belong_to_family_pool() -> None:
    capacities = ban_lab_capacities_from_account_state(_account_state_with_ban_labs(), repo_root=ROOT)
    effects = load_effect_specs(ROOT)
    with pytest.raises(ValueError, match="not in this module family effect pool"):
        build_ban_lab_wiring(capacities, {"Cannon": ["Chrono Field - Duration"]}, effects)
