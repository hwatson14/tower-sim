from __future__ import annotations

import pytest

from tower_sim.registry.ep_formula_registry import (
    RegistryValidationError,
    load_ep_formula_registry,
)


def test_ep_registry_loads_without_validation() -> None:
    registry = load_ep_formula_registry(strict=False)

    assert "EPD_ASPD" in registry.mechanics
    assert "EPD_BST" in registry.mechanics
    assert "ep_edamage_ef5" in registry.formulas

    bst = registry.mechanics["EPD_BST"]
    assert bst.implicit_globals == ()

    dd5 = registry.formulas["ep_edamage_dd5"]
    deps = set(dd5.depends_on)
    assert {
        "ep_edamage_cz5",
        "ep_edamage_da5",
        "ep_edamage_db5",
        "ep_edamage_dc5",
    }.issubset(deps)


def test_ep_registry_strict_missing_symbols() -> None:
    with pytest.raises(RegistryValidationError) as excinfo:
        load_ep_formula_registry()

    missing = set(excinfo.value.missing_symbols)
    assert {"EPD_SPB", "EPG_MODULE_BONUS"}.issubset(missing)
