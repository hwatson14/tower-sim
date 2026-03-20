"""v3 Phase-2 stat input compiler with KB naming-contract validation.

This module composes the existing deterministic stat-input compiler surfaces and
adds fail-closed validation against canonical KB contracts loaded through a
single KB accessor.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
import re
from typing import Iterable, Literal

import yaml

from tower_sim.engines.stat_engine import StatInput
from tower_sim.engines.stat_input_compiler import (
    CompiledBaselineLoadout,
    CompiledStatInputs,
    compile_baseline_account_stat_inputs,
    compile_baseline_gem_respec_stat_inputs,
    compile_baseline_loadout_stat_inputs,
    compile_full_stat_inputs,
)
from tower_sim.registry.stat_registry import default_registry
from tower_sim.util.account_snapshot import AccountSnapshot
from v3.kb_access import content_sha256, load_yaml

_NAMING_CONTRACT_IN_KB = "kb/global-rules/contracts/naming-contract.yaml"
_KB_ROUTING_CONTRACT_IN_KB = "kb/global-rules/contracts/contributor-mappings-full.yaml"
_IDS_SECTION_ROUTING_IN_KB = "kb/global-rules/contracts/ids-section-routing.yaml"
_LOCK_PATH = Path("v3/kb_contract_lock.yaml")
_SNAKE_CASE_RE = re.compile(r"^[a-z][a-z0-9_]*$")

# Provenance-prefix -> KB naming-contract contributor source_section
_PROVENANCE_SOURCE_MAP = {
    "workshop_table": "workshop",
    "workshop_formula": "workshop",
    "workshop_alias": "workshop",
    "uw_section": "uw_upgrade",
    "uw_alias": "uw_upgrade",
    "relics": "relic",
    "bot_table": "bot_upgrade",
    "base": "unlock",  # identity/default seed rows
    "modules": "module",
    "cards": "card",
}

# Transitional compatibility policy for legacy compiler rows that are not
# canonical-stat surfaces but still appear in v3 input composition.
# Keep this explicit and deterministic; any noncanonical row outside these
# guards must fail closed.
_LEGACY_NONCANONICAL_COMPAT: dict[str, dict[str, object]] = {
    "unlock": {
        "allowed_prefixes": {"base"},
        "allowed_stat_ids": {
            "death_ray_damage_mult",
            "knockback_mult",
            "orb_damage_mult",
            "plasma_cannon_damage_mult",
        },
    },
    "workshop": {
        "allowed_prefixes": {"workshop_table", "workshop_formula"},
        "required_stat_prefix": "workshop_",
    },
}

# Families that KB allows as noncanonical destination classes but that we keep
# explicitly bounded in v3 until promoted to canonical surfaces.
_NONCANONICAL_OUT_OF_SCOPE_POLICY: dict[str, dict[str, object]] = {
    "bot_upgrade": {
        "allowed_prefixes": {"bot_table"},
        "required_stat_prefix": "bot_",
        # Explicitly freeze currently accepted bot noncanonical backlog rows so
        # newly introduced bot surfaces fail closed until reviewed.
        "allowed_stat_ids": {
            "bot_amplify_bonus",
            "bot_amplify_cooldown",
            "bot_amplify_duration",
            "bot_amplify_range",
            "bot_flame_cooldown",
            "bot_flame_damage",
            "bot_flame_damage_reduction",
            "bot_flame_range",
            "bot_golden_bonus",
            "bot_golden_cooldown",
            "bot_golden_duration",
            "bot_golden_range",
            "bot_thunder_cooldown",
            "bot_thunder_duration",
            "bot_thunder_linger",
            "bot_thunder_range",
        },
    },
    "uw_upgrade": {
        "allowed_prefixes": {"uw_section", "uw_alias"},
        "required_stat_prefix": "uw_",
        # Explicitly freeze currently accepted UW noncanonical backlog rows so
        # newly introduced UW surfaces fail closed until reviewed.
        "allowed_stat_ids": {
            "uw_black_hole_consume",
            "uw_black_hole_cooldown",
            "uw_black_hole_duration",
            "uw_black_hole_duration_next_cost",
            "uw_black_hole_size",
            "uw_black_hole_size_next_cost",
            "uw_chain_lightning_chance",
            "uw_chain_lightning_chance_next_cost",
            "uw_chain_lightning_damage",
            "uw_chain_lightning_damage_next_cost",
            "uw_chain_lightning_quantity",
            "uw_chain_lightning_quantity_next_cost",
            "uw_chain_lightning_smite",
            "uw_chrono_field_chrono_loop",
            "uw_chrono_field_cooldown",
            "uw_chrono_field_duration",
            "uw_chrono_field_duration_next_cost",
            "uw_chrono_field_speed_reduction",
            "uw_chrono_field_speed_reduction_next_cost",
            "uw_death_wave_cooldown",
            "uw_death_wave_cooldown_next_cost",
            "uw_death_wave_damage",
            "uw_death_wave_damage_next_cost",
            "uw_death_wave_kill_wall",
            "uw_death_wave_quantity",
            "uw_death_wave_quantity_next_cost",
            "uw_golden_tower_cooldown",
            "uw_golden_tower_cooldown_next_cost",
            "uw_golden_tower_duration",
            "uw_golden_tower_duration_next_cost",
            "uw_golden_tower_golden_combo",
            "uw_golden_tower_multiplier",
            "uw_golden_tower_multiplier_next_cost",
            "uw_inner_land_mines_charged_mines",
            "uw_inner_land_mines_cooldown",
            "uw_inner_land_mines_cooldown_next_cost",
            "uw_inner_land_mines_damage",
            "uw_inner_land_mines_damage_next_cost",
            "uw_inner_land_mines_quantity",
            "uw_inner_land_mines_quantity_next_cost",
            "uw_poison_swamp_cooldown",
            "uw_poison_swamp_cooldown_next_cost",
            "uw_poison_swamp_damage",
            "uw_poison_swamp_damage_next_cost",
            "uw_poison_swamp_death_creep",
            "uw_poison_swamp_duration",
            "uw_poison_swamp_duration_next_cost",
            "uw_smart_missiles_cooldown",
            "uw_smart_missiles_cooldown_next_cost",
            "uw_smart_missiles_cover_fire",
            "uw_smart_missiles_damage",
            "uw_smart_missiles_damage_next_cost",
            "uw_smart_missiles_quantity",
            "uw_smart_missiles_quantity_next_cost",
            "uw_spotlight_angle",
            "uw_spotlight_angle_next_cost",
            "uw_spotlight_light_range",
            "uw_spotlight_multiplier",
            "uw_spotlight_multiplier_next_cost",
            "uw_spotlight_quantity",
            "uw_spotlight_quantity_next_cost",
        },
    },
    "relic": {
        "allowed_prefixes": {"relics"},
        "allowed_stat_ids": {"bot_range"},
    },
    "card": {
        "allowed_prefixes": {"cards"},
        "allowed_stat_ids": {"plasma_cannon_damage_mult", "workshop_free_upgrades"},
    },
    "module": {
        "allowed_prefixes": {"modules"},
        "allowed_stat_ids": {
            "bot_range",
            "uw_black_hole_cooldown",
            "uw_black_hole_duration",
            "uw_chain_lightning_chance",
            "uw_chain_lightning_damage",
            "uw_chain_lightning_quantity",
            "uw_death_wave_damage",
            "uw_death_wave_quantity",
            "uw_inner_land_mines_damage",
            "uw_poison_swamp_damage",
            "uw_smart_missiles_damage",
            "uw_spotlight_angle",
            "uw_spotlight_multiplier",
        },
    },
    # Explicitly policy-bound to zero accepted noncanonical stat surfaces.
    "enhancements": {
        "allowed_prefixes": {"enhancements"},
        "allowed_stat_ids": set(),
    },
    "vault": {
        "allowed_prefixes": {"vault"},
        "allowed_stat_ids": set(),
    },
    "guardian_upgrade": {
        "allowed_prefixes": {"guardians"},
        "allowed_stat_ids": set(),
    },
    "theme_song": {
        "allowed_prefixes": {"theme_songs"},
        "allowed_stat_ids": set(),
    },
    "player_stuff": {
        "allowed_prefixes": {"player_stuff"},
        "allowed_stat_ids": set(),
    },
}



def noncanonical_policy_contract() -> dict[str, object]:
    unlock = _LEGACY_NONCANONICAL_COMPAT.get("unlock", {})
    unlock_ids = unlock.get("allowed_stat_ids")
    unlock_prefixes = unlock.get("allowed_prefixes")
    if not isinstance(unlock_ids, set):
        raise V3StatInputCompilerError("noncanonical_policy_contract_missing_unlock_allowlist")
    if not isinstance(unlock_prefixes, set):
        raise V3StatInputCompilerError("noncanonical_policy_contract_missing_unlock_prefixes")

    families: dict[str, dict[str, object]] = {
        "unlock": {
            "allowed_prefixes": sorted(unlock_prefixes),
            "allowed_stat_ids": sorted(unlock_ids),
        }
    }
    prefixes: set[str] = set()
    for family, policy in _NONCANONICAL_OUT_OF_SCOPE_POLICY.items():
        if not isinstance(policy, dict):
            raise V3StatInputCompilerError(f"noncanonical_policy_contract_invalid_family_policy:{family}")
        allowed_prefixes = policy.get("allowed_prefixes")
        if not isinstance(allowed_prefixes, set) or not allowed_prefixes:
            raise V3StatInputCompilerError(f"noncanonical_policy_contract_missing_prefixes:{family}")
        required = policy.get("required_stat_prefix")
        if isinstance(required, str) and required.strip() != "":
            prefixes.add(required)
        allowed_stat_ids = policy.get("allowed_stat_ids")
        family_contract: dict[str, object] = {
            "allowed_prefixes": sorted(allowed_prefixes),
        }
        if isinstance(required, str) and required.strip() != "":
            family_contract["required_stat_prefix"] = required
        if isinstance(allowed_stat_ids, set):
            family_contract["allowed_stat_ids"] = sorted(allowed_stat_ids)
        families[family] = family_contract

    kb_noncanonical_families = sorted(_kb_families_allow_noncanonical())
    covered_kb_families = sorted([name for name in families if name in set(kb_noncanonical_families)])
    missing_kb_policy_families = sorted([name for name in kb_noncanonical_families if name not in families])

    return {
        "allowed_stat_prefixes": sorted(prefixes),
        "allowed_unlock_stat_ids": sorted(unlock_ids),
        "families": dict(sorted(families.items())),
        "kb_noncanonical_families": kb_noncanonical_families,
        "covered_kb_policy_families": covered_kb_families,
        "missing_kb_policy_families": missing_kb_policy_families,
        "coverage_complete": len(missing_kb_policy_families) == 0,
    }


_NONCANONICAL_TO_CANONICAL_ALIAS: dict[str, str] = {
    "cash_bonus": "cash_kill_multiplier",
    "coins_bonus": "coin_kill_multiplier",
    "damage_per_meter": "tower_damage_per_meter_multiplier",
    "def_pct": "tower_defense_pct",
    "defense_absolute": "tower_defense_absolute",
    "eals_pct": "enemy_attack_level_skip_pct",
    "ehls_pct": "enemy_health_level_skip_pct",
    "free_attack_upgrade": "free_attack_upgrade_chance_pct",
    "free_defense_upgrade": "free_defense_upgrade_chance_pct",
    "free_utility_upgrade": "free_utility_upgrade_chance_pct",
    "orb_speed": "tower_orb_speed_rpm",
    "lab_speed": "lab_speed_multiplier",
    "super_crit_chance": "tower_supercrit_chance_pct",
    "super_crit_mult": "tower_supercrit_multiplier",
    "thorns_damage_mult": "tower_thorns_damage_pct",
    "recovery_amount": "recovery_amount_pct",
    "tower_crit_chance": "tower_crit_chance_pct",
    "ultimate_damage": "ultimate_damage_multiplier",
    "wall_rebuild": "wall_rebuild_seconds",
    "workshop_attack_speed": "tower_attack_speed",
    "workshop_bounce_shot_chance": "tower_bounce_shot_chance_pct",
    "workshop_bounce_shot_range": "tower_bounce_shot_range_m",
    "workshop_bounce_shot_targets": "tower_bounce_shot_targets",
    "workshop_cash_bonus": "cash_kill_multiplier",
    "workshop_cash_per_wave": "cash_per_wave",
    "workshop_coins_per_kill_bonus": "coin_kill_multiplier",
    "workshop_coins_per_wave": "coins_per_wave",
    "workshop_critical_chance": "tower_crit_chance_pct",
    "workshop_critical_factor": "tower_crit_multiplier",
    "workshop_damage": "tower_damage",
    "workshop_damage_per_meter": "tower_damage_per_meter_multiplier",
    "workshop_death_defy": "tower_death_defy_chance_pct",
    "workshop_defense_absolute": "tower_defense_absolute",
    "workshop_defense_percent": "tower_defense_pct",
    "workshop_enemy_attack_level_skip": "enemy_attack_level_skip_pct",
    "workshop_enemy_health_level_skip": "enemy_health_level_skip_pct",
    "workshop_free_attack_upgrade": "free_attack_upgrade_chance_pct",
    "workshop_free_defense_upgrade": "free_defense_upgrade_chance_pct",
    "workshop_free_utility_upgrade": "free_utility_upgrade_chance_pct",
    "workshop_health": "tower_hp",
    "workshop_health_regen": "tower_regen",
    "workshop_interest": "interest_per_wave_pct",
    "workshop_knockback_chance": "tower_knockback_chance_pct",
    "workshop_knockback_force": "tower_knockback_force",
    "workshop_land_mine_chance": "tower_land_mine_chance_pct",
    "workshop_land_mine_damage": "tower_land_mine_damage",
    "workshop_land_mine_radius": "tower_land_mine_radius_m",
    "workshop_lifesteal": "tower_lifesteal_pct",
    "workshop_max_recovery": "max_recovery_multiplier",
    "workshop_multishot_chance": "tower_multishot_chance_pct",
    "workshop_multishot_targets": "tower_multishot_targets",
    "workshop_orb_speed": "tower_orb_speed_rpm",
    "workshop_orbs": "tower_orb_count",
    "workshop_package_chance": "package_chance_pct",
    "workshop_range_meters": "tower_range_m",
    "workshop_rapid_fire_chance": "tower_rapid_fire_chance_pct",
    "workshop_rapid_fire_duration": "tower_rapid_fire_duration_seconds",
    "workshop_recovery_amount": "recovery_amount_pct",
    "workshop_rend_armor_chance": "tower_rend_armor_chance_pct",
    "workshop_rend_armor_mult": "tower_rend_armor_multiplier",
    "workshop_shockwave_frequency": "tower_shockwave_interval_seconds",
    "workshop_shockwave_size": "tower_shockwave_size_m",
    "workshop_super_crit_chance": "tower_supercrit_chance_pct",
    "workshop_super_crit_mult_alt": "tower_supercrit_multiplier",
    "workshop_thorn_damage": "tower_thorns_damage_pct",
    "workshop_wall_health": "wall_hp",
    "workshop_wall_rebuild": "wall_rebuild_seconds",
    "black_hole_consume": "uw_black_hole_consume",
    "black_hole_cooldown": "uw_black_hole_cooldown",
    "black_hole_duration": "uw_black_hole_duration",
    "black_hole_duration_next_cost": "uw_black_hole_duration_next_cost",
    "black_hole_size": "uw_black_hole_size",
    "black_hole_size_next_cost": "uw_black_hole_size_next_cost",
    "chain_lightning_chance": "uw_chain_lightning_chance",
    "chain_lightning_chance_next_cost": "uw_chain_lightning_chance_next_cost",
    "chain_lightning_damage": "uw_chain_lightning_damage",
    "chain_lightning_damage_next_cost": "uw_chain_lightning_damage_next_cost",
    "chain_lightning_quantity": "uw_chain_lightning_quantity",
    "chain_lightning_quantity_next_cost": "uw_chain_lightning_quantity_next_cost",
    "chain_lightning_smite": "uw_chain_lightning_smite",
    "chrono_field_chrono_loop": "uw_chrono_field_chrono_loop",
    "chrono_field_cooldown": "uw_chrono_field_cooldown",
    "chrono_field_duration": "uw_chrono_field_duration",
    "chrono_field_duration_next_cost": "uw_chrono_field_duration_next_cost",
    "chrono_field_speed_reduction": "uw_chrono_field_speed_reduction",
    "chrono_field_speed_reduction_next_cost": "uw_chrono_field_speed_reduction_next_cost",
    "death_wave_cooldown": "uw_death_wave_cooldown",
    "death_wave_cooldown_next_cost": "uw_death_wave_cooldown_next_cost",
    "death_wave_damage": "uw_death_wave_damage",
    "death_wave_damage_next_cost": "uw_death_wave_damage_next_cost",
    "death_wave_kill_wall": "uw_death_wave_kill_wall",
    "death_wave_quantity": "uw_death_wave_quantity",
    "death_wave_quantity_next_cost": "uw_death_wave_quantity_next_cost",
    "golden_tower_cooldown": "uw_golden_tower_cooldown",
    "golden_tower_cooldown_next_cost": "uw_golden_tower_cooldown_next_cost",
    "golden_tower_duration": "uw_golden_tower_duration",
    "golden_tower_duration_next_cost": "uw_golden_tower_duration_next_cost",
    "golden_tower_golden_combo": "uw_golden_tower_golden_combo",
    "golden_tower_multiplier": "uw_golden_tower_multiplier",
    "golden_tower_multiplier_next_cost": "uw_golden_tower_multiplier_next_cost",
    "inner_land_mines_charged_mines": "uw_inner_land_mines_charged_mines",
    "inner_land_mines_cooldown": "uw_inner_land_mines_cooldown",
    "inner_land_mines_cooldown_next_cost": "uw_inner_land_mines_cooldown_next_cost",
    "inner_land_mines_damage": "uw_inner_land_mines_damage",
    "inner_land_mines_damage_next_cost": "uw_inner_land_mines_damage_next_cost",
    "inner_land_mines_quantity": "uw_inner_land_mines_quantity",
    "inner_land_mines_quantity_next_cost": "uw_inner_land_mines_quantity_next_cost",
    "poison_swamp_cooldown": "uw_poison_swamp_cooldown",
    "poison_swamp_cooldown_next_cost": "uw_poison_swamp_cooldown_next_cost",
    "poison_swamp_damage": "uw_poison_swamp_damage",
    "poison_swamp_damage_next_cost": "uw_poison_swamp_damage_next_cost",
    "poison_swamp_death_creep": "uw_poison_swamp_death_creep",
    "poison_swamp_duration": "uw_poison_swamp_duration",
    "poison_swamp_duration_next_cost": "uw_poison_swamp_duration_next_cost",
    "smart_missiles_cooldown": "uw_smart_missiles_cooldown",
    "smart_missiles_cooldown_next_cost": "uw_smart_missiles_cooldown_next_cost",
    "smart_missiles_cover_fire": "uw_smart_missiles_cover_fire",
    "smart_missiles_damage": "uw_smart_missiles_damage",
    "smart_missiles_damage_next_cost": "uw_smart_missiles_damage_next_cost",
    "smart_missiles_quantity": "uw_smart_missiles_quantity",
    "smart_missiles_quantity_next_cost": "uw_smart_missiles_quantity_next_cost",
    "spotlight_angle": "uw_spotlight_angle",
    "spotlight_angle_next_cost": "uw_spotlight_angle_next_cost",
    "spotlight_light_range": "uw_spotlight_light_range",
    "spotlight_multiplier": "uw_spotlight_multiplier",
    "spotlight_multiplier_next_cost": "uw_spotlight_multiplier_next_cost",
    "spotlight_quantity": "uw_spotlight_quantity",
    "spotlight_quantity_next_cost": "uw_spotlight_quantity_next_cost",
}


class V3StatInputCompilerError(RuntimeError):
    pass


@dataclass(frozen=True)
class V3CompiledStatInputs:
    stat_inputs: list[StatInput]
    missing: list[str]
    dropped_noncanonical: list[str] = field(default_factory=list)
    dropped_kb_unwired: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class V3CompiledBaselineLoadout:
    stat_inputs: list[StatInput]
    missing: list[str]
    module_contribution_ledger: list[dict[str, object]]
    layer_gaps: list[str]
    dropped_noncanonical: list[str] = field(default_factory=list)
    dropped_kb_unwired: list[str] = field(default_factory=list)


def _load_kb_naming_contract() -> dict:
    data = load_yaml(_NAMING_CONTRACT_IN_KB)
    if data.get("kind") != "naming_contract":
        raise V3StatInputCompilerError("KB naming contract kind mismatch.")
    return data


def _load_contract_lock() -> dict[str, str]:
    payload = yaml.safe_load(_LOCK_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise V3StatInputCompilerError("KB contract lock is not a mapping.")
    contracts = payload.get("contracts")
    if not isinstance(contracts, dict) or not contracts:
        raise V3StatInputCompilerError("KB contract lock missing contracts mapping.")
    return {str(k): str(v) for k, v in contracts.items()}


def _validate_contract_hash_lock() -> None:
    expected = _load_contract_lock()
    drift: list[str] = []
    for rel_path, expected_hash in expected.items():
        observed = content_sha256(rel_path)
        if observed != expected_hash:
            drift.append(f"{rel_path}:expected={expected_hash}:observed={observed}")
    if drift:
        raise V3StatInputCompilerError("KB contract hash drift detected: " + ", ".join(drift))


def _allowed_source_sections_from_kb(contract: dict) -> set[str]:
    section_def = (
        contract.get("sections", {})
        .get("contributor_id", {})
        .get("section_definitions", {})
        .get("source_section", "")
    )
    if not isinstance(section_def, str) or section_def.strip() == "":
        raise V3StatInputCompilerError("KB naming contract missing contributor source_section definition.")

    section_csv = section_def
    if "such as" in section_def:
        section_csv = section_def.split("such as", 1)[1]
    allowed = {
        token.strip().replace(" ", "_")
        for token in section_csv.split(",")
        if token.strip()
    }
    if not allowed:
        raise V3StatInputCompilerError("KB naming contract yielded no contributor source sections.")
    return allowed


def _provenance_prefix(provenance: str, *, stat_id: str) -> str:
    raw = provenance.strip()
    if raw == "":
        raise V3StatInputCompilerError(f"missing_provenance:{stat_id}")
    if ":" not in raw:
        raise V3StatInputCompilerError(
            f"ambiguous_provenance_prefix:{stat_id}:missing_separator:{raw}"
        )

    prefix = raw.split(":", 1)[0].strip()
    if not _SNAKE_CASE_RE.fullmatch(prefix):
        bad = prefix if prefix else "<empty>"
        raise V3StatInputCompilerError(
            f"ambiguous_provenance_prefix:{stat_id}:invalid_prefix:{bad}"
        )
    return prefix


def _infer_contributor_family(item: StatInput) -> str:
    if item.contributor_family and item.contributor_family.strip():
        return item.contributor_family.strip()
    provenance = item.provenance or ""
    prefix = _provenance_prefix(provenance, stat_id=item.stat_id)
    if (
        item.stat_id == "wall_regen"
        and prefix == "workshop_alias"
        and "Wall Regen->wall_regen" in provenance
    ):
        # Legacy compiler emits a composite wall_regen row through workshop alias
        # naming, but KB routing authority assigns wall_regen to lab/module only.
        # Route this known composite row into the lab family for v3 closure.
        return "lab"
    mapped = _PROVENANCE_SOURCE_MAP.get(prefix)
    if mapped:
        return mapped
    raise V3StatInputCompilerError(
        "unable_to_infer_contributor_family:"
        f"{item.stat_id}:unknown_provenance_prefix:{prefix}:provenance={item.provenance!r}"
    )


def _enrich_contributor_families(stat_inputs: Iterable[StatInput]) -> list[StatInput]:
    enriched: list[StatInput] = []
    for item in stat_inputs:
        family = _infer_contributor_family(item)
        enriched.append(replace(item, contributor_family=family))
    return enriched


def _promote_noncanonical_aliases(stat_inputs: Iterable[StatInput]) -> list[StatInput]:
    promoted: list[StatInput] = []
    for item in stat_inputs:
        canonical_stat = _NONCANONICAL_TO_CANONICAL_ALIAS.get(item.stat_id)
        if canonical_stat is None:
            promoted.append(item)
            continue
        promoted.append(replace(item, stat_id=canonical_stat))
    return promoted



def _load_kb_routing_contract() -> dict:
    data = load_yaml(_KB_ROUTING_CONTRACT_IN_KB)
    if data.get("kind") != "contributor_routing":
        raise V3StatInputCompilerError("KB routing contract kind mismatch.")
    return data


def _kb_allowed_routes() -> tuple[set[str], dict[str, set[str]]]:
    contract = _load_kb_routing_contract()
    source_families = contract.get("source_families")
    if not isinstance(source_families, dict):
        raise V3StatInputCompilerError("KB routing contract missing source_families mapping.")

    canonical_stats: set[str] = set()
    allowed_by_family: dict[str, set[str]] = {}
    for family, rows in source_families.items():
        if not isinstance(rows, list):
            raise V3StatInputCompilerError(f"KB routing rows must be list for family={family!r}.")
        bucket = allowed_by_family.setdefault(str(family), set())
        for row in rows:
            if not isinstance(row, dict):
                raise V3StatInputCompilerError(f"KB routing row must be mapping for family={family!r}.")
            if str(row.get("destination_object_type") or "") != "canonical_stat":
                continue
            stat_id = str(row.get("destination_id") or "").strip()
            if stat_id == "":
                raise V3StatInputCompilerError(f"KB routing row missing destination_id for family={family!r}.")
            canonical_stats.add(stat_id)
            bucket.add(stat_id)
    return canonical_stats, allowed_by_family


def _kb_families_allow_noncanonical() -> set[str]:
    routing = load_yaml(_IDS_SECTION_ROUTING_IN_KB)
    sections = routing.get("sections")
    if not isinstance(sections, dict) or not sections:
        raise V3StatInputCompilerError("KB ids-section routing missing sections mapping.")

    allowed: set[str] = set()
    for section_name, section in sections.items():
        if not isinstance(section, dict):
            raise V3StatInputCompilerError(f"KB ids-section routing section must be mapping: {section_name!r}")
        family = str(section.get("source_family") or "").strip()
        if family == "":
            raise V3StatInputCompilerError(f"KB ids-section routing missing source_family for section={section_name!r}")
        destination_classes = section.get("destination_classes")
        if not isinstance(destination_classes, list) or not destination_classes:
            raise V3StatInputCompilerError(
                f"KB ids-section routing missing destination_classes for section={section_name!r}"
            )
        classes = {str(item).strip() for item in destination_classes if str(item).strip()}
        if not classes:
            raise V3StatInputCompilerError(
                f"KB ids-section routing produced empty destination_classes for section={section_name!r}"
            )
        if classes != {"canonical_stat"}:
            allowed.add(family)
    return allowed


def _kb_known_source_families() -> set[str]:
    routing = load_yaml(_IDS_SECTION_ROUTING_IN_KB)
    sections = routing.get("sections")
    if not isinstance(sections, dict) or not sections:
        raise V3StatInputCompilerError("KB ids-section routing missing sections mapping.")

    known: set[str] = {"unlock"}
    for section_name, section in sections.items():
        if not isinstance(section, dict):
            raise V3StatInputCompilerError(f"KB ids-section routing section must be mapping: {section_name!r}")
        family = str(section.get("source_family") or "").strip()
        if family == "":
            raise V3StatInputCompilerError(f"KB ids-section routing missing source_family for section={section_name!r}")
        known.add(family)
    return known


def _filter_kb_supported_stat_inputs(
    stat_inputs: Iterable[StatInput],
) -> tuple[list[StatInput], list[str], list[str]]:
    canonical_stats, allowed_by_family = _kb_allowed_routes()
    noncanonical_allowed_families = _kb_families_allow_noncanonical()
    missing_policy_families = sorted(
        family for family in noncanonical_allowed_families if family not in _NONCANONICAL_OUT_OF_SCOPE_POLICY
    )
    if missing_policy_families:
        raise V3StatInputCompilerError(
            "noncanonical_policy_missing_for_noncanonical_families:"
            + ",".join(missing_policy_families)
        )

    known_families = _kb_known_source_families()
    filtered: list[StatInput] = []
    dropped_noncanonical: list[str] = []
    dropped_kb_unwired: list[str] = []

    for item in stat_inputs:
        if item.stat_id not in canonical_stats:
            family = (item.contributor_family or "").strip()
            prefix = _provenance_prefix(item.provenance or "", stat_id=item.stat_id)
            if family in noncanonical_allowed_families:
                policy = _NONCANONICAL_OUT_OF_SCOPE_POLICY.get(family)
                if policy is None:
                    raise V3StatInputCompilerError(
                        "noncanonical_surface_policy_missing_for_family:"
                        f"family={family or '<missing>'}:prefix={prefix}:stat_id={item.stat_id}"
                    )
                allowed_prefixes = policy.get("allowed_prefixes")
                if not isinstance(allowed_prefixes, set) or prefix not in allowed_prefixes:
                    raise V3StatInputCompilerError(
                        "noncanonical_surface_not_allowed_by_policy:"
                        f"family={family or '<missing>'}:prefix={prefix}:stat_id={item.stat_id}"
                    )
                required_stat_prefix = policy.get("required_stat_prefix")
                if isinstance(required_stat_prefix, str) and not item.stat_id.startswith(required_stat_prefix):
                    raise V3StatInputCompilerError(
                        "noncanonical_surface_not_allowed_by_policy:"
                        f"family={family or '<missing>'}:prefix={prefix}:stat_id={item.stat_id}"
                    )
                allowed_stat_ids = policy.get("allowed_stat_ids")
                if isinstance(allowed_stat_ids, set) and item.stat_id not in allowed_stat_ids:
                    raise V3StatInputCompilerError(
                        "noncanonical_surface_not_allowed_by_policy:"
                        f"family={family or '<missing>'}:prefix={prefix}:stat_id={item.stat_id}"
                    )
                # Explicit KB-sanctioned noncanonical family path.
                dropped_noncanonical.append(f"noncanonical_stat_surface:{family or '<missing>'}:{prefix}:{item.stat_id}")
                continue

            compat = _LEGACY_NONCANONICAL_COMPAT.get(family)
            if compat is not None:
                allowed_prefixes = compat.get("allowed_prefixes")
                if not isinstance(allowed_prefixes, set) or prefix not in allowed_prefixes:
                    raise V3StatInputCompilerError(
                        "noncanonical_surface_not_allowed_by_kb:"
                        f"family={family or '<missing>'}:prefix={prefix}:stat_id={item.stat_id}"
                    )
                required_stat_prefix = compat.get("required_stat_prefix")
                if isinstance(required_stat_prefix, str) and not item.stat_id.startswith(required_stat_prefix):
                    raise V3StatInputCompilerError(
                        "noncanonical_surface_not_allowed_by_kb:"
                        f"family={family or '<missing>'}:prefix={prefix}:stat_id={item.stat_id}"
                    )
                allowed_stat_ids = compat.get("allowed_stat_ids")
                if isinstance(allowed_stat_ids, set) and item.stat_id not in allowed_stat_ids:
                    raise V3StatInputCompilerError(
                        "noncanonical_surface_not_allowed_by_kb:"
                        f"family={family or '<missing>'}:prefix={prefix}:stat_id={item.stat_id}"
                    )
                dropped_noncanonical.append(f"noncanonical_stat_surface:{family or '<missing>'}:{prefix}:{item.stat_id}")
                continue

            raise V3StatInputCompilerError(
                "noncanonical_surface_not_allowed_by_kb:"
                f"family={family or '<missing>'}:prefix={prefix}:stat_id={item.stat_id}"
            )
        family = (item.contributor_family or "").strip()
        allowed = allowed_by_family.get(family)
        if allowed is None:
            if family not in known_families:
                raise V3StatInputCompilerError(
                    f"unknown_contributor_family_not_in_kb:{family or '<missing>'}"
                )
            dropped_kb_unwired.append(f"kb_unwired:{family or '<missing>'}:{item.stat_id}")
            continue
        if item.stat_id not in allowed:
            dropped_kb_unwired.append(f"kb_unwired:{family or '<missing>'}:{item.stat_id}")
            continue
        filtered.append(item)
    return filtered, sorted(set(dropped_noncanonical)), sorted(set(dropped_kb_unwired))

def validate_compiled_stat_inputs(
    stat_inputs: Iterable[StatInput],
) -> None:
    _validate_contract_hash_lock()
    contract = _load_kb_naming_contract()
    allowed_sources = _allowed_source_sections_from_kb(contract)
    known_families = _kb_known_source_families()
    registry = default_registry()

    errors: list[str] = []
    for item in stat_inputs:
        if not _SNAKE_CASE_RE.fullmatch(item.stat_id):
            errors.append(f"stat_id_not_snake_case:{item.stat_id}")
            continue

        try:
            registry.get(item.stat_id)
        except KeyError:
            errors.append(f"unknown_stat_id:{item.stat_id}")

        if not item.provenance or item.provenance.strip() == "":
            errors.append(f"missing_provenance:{item.stat_id}")
        else:
            try:
                _provenance_prefix(item.provenance, stat_id=item.stat_id)
            except V3StatInputCompilerError as exc:
                errors.append(str(exc))

        source = (item.contributor_family or "").strip()
        if source == "":
            errors.append(f"missing_contributor_family:{item.stat_id}")
        elif source not in allowed_sources:
            errors.append(f"unknown_contributor_source_section:{item.stat_id}:{source}")
        if source and source not in known_families:
            errors.append(f"unknown_contributor_family_not_in_kb:{item.stat_id}:{source}")

        if item.provenance and source:
            prefix = _provenance_prefix(item.provenance, stat_id=item.stat_id)
            inferred_source = _PROVENANCE_SOURCE_MAP.get(prefix)
            if inferred_source and inferred_source != source:
                is_wall_regen_composite = (
                    item.stat_id == "wall_regen"
                    and inferred_source == "workshop"
                    and source == "lab"
                    and "Wall Regen->wall_regen" in item.provenance
                )
                if not is_wall_regen_composite:
                    errors.append(
                        "provenance_family_mismatch:"
                        f"{item.stat_id}:provenance={inferred_source}:family={source}"
                    )

    if errors:
        unique = sorted(set(errors))
        raise V3StatInputCompilerError(
            "KB naming-contract validation failed for compiled stat inputs: "
            + ", ".join(unique[:20])
            + (" ..." if len(unique) > 20 else "")
        )




def _normalize_missing_against_kb(missing: Iterable[str]) -> list[str]:
    """Normalize runtime missing diagnostics against KB mapping semantics.

    `lab_table_unmapped:*` indicates the legacy runtime lab-value table does not
    cover that active lab yet; it does not mean KB contributor routing is
    missing. For v3 mapping-closure tracking, keep only hard unresolved rows.
    """

    normalized: list[str] = []
    for item in missing:
        if item.startswith("lab_table_unmapped:"):
            continue
        normalized.append(item)
    return normalized

def _wrap_and_validate(compiled: CompiledStatInputs) -> V3CompiledStatInputs:
    enriched = _enrich_contributor_families(compiled.stat_inputs)
    enriched = _promote_noncanonical_aliases(enriched)
    validate_compiled_stat_inputs(enriched)
    kb_filtered, dropped_noncanonical, dropped_kb_unwired = _filter_kb_supported_stat_inputs(enriched)
    return V3CompiledStatInputs(
        stat_inputs=kb_filtered,
        missing=_normalize_missing_against_kb(list(compiled.missing) + dropped_kb_unwired),
        dropped_noncanonical=dropped_noncanonical,
        dropped_kb_unwired=dropped_kb_unwired,
    )


def compile_v3_stat_inputs(
    snapshot: AccountSnapshot,
    *,
    stage: Literal["baseline_account", "baseline_gem_respec", "full"] = "baseline_gem_respec",
) -> V3CompiledStatInputs:
    if stage == "baseline_account":
        compiled = compile_baseline_account_stat_inputs(snapshot)
    elif stage == "baseline_gem_respec":
        compiled = compile_baseline_gem_respec_stat_inputs(snapshot)
    elif stage == "full":
        compiled = compile_full_stat_inputs(snapshot)
    else:
        raise V3StatInputCompilerError(f"Unsupported stage: {stage}")

    return _wrap_and_validate(compiled)


def compile_v3_baseline_loadout_stat_inputs(
    snapshot: AccountSnapshot,
    *,
    module_context: str = "Farming",
    selected_cards: Iterable[str] | None = None,
) -> V3CompiledBaselineLoadout:
    compiled: CompiledBaselineLoadout = compile_baseline_loadout_stat_inputs(
        snapshot,
        module_context=module_context,
        selected_cards=selected_cards,
    )
    enriched = _enrich_contributor_families(compiled.stat_inputs)
    enriched = _promote_noncanonical_aliases(enriched)
    validate_compiled_stat_inputs(enriched)
    kb_filtered, dropped_noncanonical, dropped_kb_unwired = _filter_kb_supported_stat_inputs(enriched)
    return V3CompiledBaselineLoadout(
        stat_inputs=kb_filtered,
        missing=_normalize_missing_against_kb(list(compiled.missing) + dropped_kb_unwired),
        module_contribution_ledger=list(compiled.module_contribution_ledger),
        layer_gaps=list(compiled.layer_gaps),
        dropped_noncanonical=dropped_noncanonical,
        dropped_kb_unwired=dropped_kb_unwired,
    )
