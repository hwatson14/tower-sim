from __future__ import annotations

import math

import pytest

from tower_sim.libs.module_main_effects import (
    ModuleMainEffectError,
    module_main_effect_multiplier,
)


def test_module_main_effect_common_level_1() -> None:
    result = module_main_effect_multiplier("cannon", "Common", 1)
    assert math.isclose(result, 1.012, rel_tol=1e-9)


def test_module_main_effect_common_level_20() -> None:
    result = module_main_effect_multiplier("cannon", "Common", 20)
    assert math.isclose(result, 1.05, rel_tol=1e-9)


def test_module_main_effect_ancestral_star_multiplier() -> None:
    result = module_main_effect_multiplier("cannon", "Ancestral 3*", 1)
    assert math.isclose(result, 1.379, rel_tol=1e-9)


def test_module_main_effect_unknown_rarity() -> None:
    with pytest.raises(ModuleMainEffectError):
        module_main_effect_multiplier("cannon", "Unknown", 1)
