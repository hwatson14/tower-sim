from __future__ import annotations

from typing import Any

from . import CERTIFICATION_STATUS, ENGINE_VERSION
from .ban_labs import BanLabWiringResult
from .domain import Rarity, RerollMechanicsConfig
from .kb_loader import SOURCE_CONTRACTS, SOURCE_TABLES
from .mechanics import expected_tail_cost_single_slot


def validation_report(
    family_counts: dict[str, int],
    mechanics: RerollMechanicsConfig,
    ban_lab_wiring: BanLabWiringResult | None = None,
) -> dict[str, Any]:
    ancestral = mechanics.rarity_probabilities[Rarity.ANCESTRAL]
    mythic_plus = mechanics.rarity_probabilities[Rarity.MYTHIC] + ancestral
    anchors = {
        "five_lock_one_target_ancestral_pool_12": {
            "pool_size": 12,
            "acceptable_effect_count": 1,
            "rarity_probability": ancestral,
            "cost_per_roll": mechanics.lock_costs[5],
            "expected_shards": expected_tail_cost_single_slot(12, 1, ancestral, mechanics.lock_costs[5]),
        },
        "five_lock_two_target_ancestral_pool_12": {
            "pool_size": 12,
            "acceptable_effect_count": 2,
            "rarity_probability": ancestral,
            "cost_per_roll": mechanics.lock_costs[5],
            "expected_shards": expected_tail_cost_single_slot(12, 2, ancestral, mechanics.lock_costs[5]),
        },
        "core_four_bans_five_locks_two_target_mythic_plus_pool_17": {
            "pool_size": 17,
            "acceptable_effect_count": 2,
            "rarity_probability": mythic_plus,
            "cost_per_roll": mechanics.lock_costs[5],
            "expected_shards": expected_tail_cost_single_slot(17, 2, mythic_plus, mechanics.lock_costs[5]),
        },
    }
    return {
        "schema_version": "module_reroll_validation_report.v1",
        "engine_version": ENGINE_VERSION,
        "certification_status": CERTIFICATION_STATUS,
        "warning": "Standalone Tranche 1 mechanics are not production-certified; no Streamlit or production app pipeline routing is installed.",
        "loaded_family_counts": family_counts,
        "rarity_probabilities": {rarity.value: probability for rarity, probability in mechanics.rarity_probabilities.items()},
        "lock_costs": mechanics.lock_costs,
        "duplicate_policy": mechanics.duplicate_policy.as_dict(),
        "ban_labs": ban_lab_wiring.as_report_dict() if ban_lab_wiring is not None else None,
        "anchor_tail_results": anchors,
        "source_tables": [str(path) for path in SOURCE_TABLES],
        "source_contracts": [str(path) for path in SOURCE_CONTRACTS],
        "certification": {
            "mechanics_certified": False,
            "duplicate_policy_certified": False,
            "scorer_certified": False,
        },
    }

