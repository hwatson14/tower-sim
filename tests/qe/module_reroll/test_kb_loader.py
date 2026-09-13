from __future__ import annotations

from pathlib import Path

import pytest

from qe.module_reroll.domain import ModuleFamily, Rarity
from qe.module_reroll.kb_loader import (
    load_effect_specs,
    load_lock_costs,
    load_module_reroll_constants,
    load_module_reroll_source_bundle,
    load_rarity_probabilities,
    normalise_effect_id,
)

ROOT = Path(__file__).resolve().parents[3]


def test_normalise_effect_id_examples() -> None:
    assert normalise_effect_id("Chrono Field - Duration") == "chrono_field.duration"
    assert normalise_effect_id("Chain Lightning - Chance") == "chain_lightning.chance"
    assert normalise_effect_id("Multishot Targets") == "multishot.targets"


def test_loads_all_module_family_effect_specs_from_kb() -> None:
    specs = load_effect_specs(ROOT)
    assert set(specs) == set(ModuleFamily)
    counts = {family.value: len(family_specs) for family, family_specs in specs.items()}
    assert counts == {"Cannon": 17, "Armor": 17, "Generator": 13, "Core": 26}, (
        "module-substats.csv family effect counts changed; review fixtures/anchors rather than hard-coding new truth"
    )
    for family_specs in specs.values():
        assert len(family_specs) == len(set(family_specs))
        for spec in family_specs.values():
            assert spec.display_name
            assert spec.values_by_rarity


def test_loads_rarity_probabilities_and_sum_invariant() -> None:
    probabilities = load_rarity_probabilities(ROOT)
    assert set(probabilities) == set(Rarity)
    assert sum(probabilities.values()) == pytest.approx(1.0)
    assert probabilities[Rarity.ANCESTRAL] == pytest.approx(0.003)
    assert probabilities[Rarity.MYTHIC] == pytest.approx(0.01)


def test_loads_closed_lock_cost_ladder_validated_against_source_closed_contract() -> None:
    costs = load_lock_costs(ROOT)
    assert set(costs) >= set(range(7))
    assert costs[0] == 10
    assert costs[4] == 1000
    assert costs[5] == 1600
    assert costs[7] == 3000


def test_loads_constants() -> None:
    constants = load_module_reroll_constants(ROOT)
    assert constants["module.reroll.currency"]["value"] == "reroll_shards"
    assert constants["module.reroll.locking_increases_cost"]["value"] is True


def test_loads_qe_owned_source_bundle_from_kb_inputs() -> None:
    bundle = load_module_reroll_source_bundle(ROOT)
    assert bundle.effect_specs[ModuleFamily.CORE]
    assert bundle.rarity_probabilities[Rarity.ANCESTRAL] == pytest.approx(0.003)
    assert bundle.lock_costs[5] == 1600
    assert any(str(path).endswith("module-reroll-cost-contract-r61.yaml") for path in bundle.source_contracts)


def test_missing_source_path_fails_clearly(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="required module reroll KB table not found"):
        load_effect_specs(tmp_path)
