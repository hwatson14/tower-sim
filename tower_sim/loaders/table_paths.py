from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping


class TablePathError(ValueError):
    """Raised when table path resolution fails."""


REPO_ROOT = Path(__file__).resolve().parents[2]
TABLES_ROOT = REPO_ROOT / "tables"


@dataclass(frozen=True)
class TableEntry:
    key: str
    relative_path: str

    @property
    def path(self) -> Path:
        return REPO_ROOT / self.relative_path


_TABLE_MANIFEST: tuple[TableEntry, ...] = (
    TableEntry("enemy_damage_table", "tables/inputs/combat/enemy_damage_table.csv"),
    TableEntry("enemy_health_table", "tables/inputs/combat/enemy_health_table.csv"),
    TableEntry("boss_hit_interval", "tables/inputs/combat/boss_hit_interval_v1.csv"),
    TableEntry("tier_battle_conditions", "tables/inputs/combat/tier_battle_conditions.csv"),
    TableEntry("battle_condition_magnitudes", "tables/inputs/combat/battle_condition_magnitudes.csv"),
    TableEntry("heat_scale_long", "tables/inputs/tournament/heat_scale_long.csv"),
    TableEntry("heat_bc_registry", "tables/inputs/tournament/heat_bc_registry.csv"),
    TableEntry("tournament_league_rules", "tables/inputs/tournament/tournament_league_rules.csv"),
    TableEntry("tournament_more_bosses_static", "tables/inputs/tournament/tournament_more_bosses_static.csv"),
    TableEntry("tournament_heat_steps", "tables/inputs/tournament/tournament_heat_steps.csv"),
    TableEntry("tournament_heat_bc_values_long", "tables/inputs/tournament/tournament_heat_bc_values_long.csv"),
    TableEntry("labs_values", "tables/inputs/economy/labs_values_v1.csv"),
    TableEntry("vault_stats", "tables/inputs/economy/vault_stats_v1.csv"),
    TableEntry("wse_presets", "tables/inputs/economy/wse_presets_v1.csv"),
    TableEntry("module_substats", "tables/inputs/modules/module_substats_v1.csv"),
    TableEntry("module_main_effect_bases", "tables/inputs/modules/module_main_effect_bases_v1.csv"),
    TableEntry("module_main_effect_bands", "tables/inputs/modules/module_main_effect_bands_v1.csv"),
    TableEntry("assist_efficiency_upgrade_costs", "tables/inputs/modules/assist_efficiency_upgrade_costs_v1.csv"),
    TableEntry("assist_slot_unlock_costs", "tables/inputs/modules/assist_slot_unlock_costs_v1.csv"),
    TableEntry("assist_stone_levels", "tables/inputs/modules/assist_stone_levels_v1.csv"),
    TableEntry("assist_unique_rarity_upgrade_costs", "tables/inputs/modules/assist_unique_rarity_upgrade_costs_v1.csv"),
    TableEntry("bot_upgrades", "tables/inputs/modules/bot_upgrades_v1.csv"),
    TableEntry("guardian_upgrades", "tables/inputs/modules/guardian_upgrades_v1.csv"),
    TableEntry("uw_purchase_costs", "tables/inputs/uw/uw_purchase_costs_v1.csv"),
    TableEntry("uw_track_ladders", "tables/inputs/uw/uw_track_ladders_v1.csv"),
    TableEntry("uw_plus_ladders", "tables/inputs/uw/uw_plus_ladders_v1.csv"),
    TableEntry("perks", "tables/inputs/perks/perks_v1.csv"),
    TableEntry("perk_pool_weights", "tables/inputs/perks/perk_pool_weights_v1.csv"),
    TableEntry("perk_wave_requirement_steps", "kb/perks/tables/perk-wave-requirement-steps.csv"),
    TableEntry("card_masteries", "tables/inputs/cards/card_masteries_v1.csv"),
    TableEntry("wiki_cache_dir", "tables/cache/wiki"),
    TableEntry("schemas_dir", "tables/meta/schemas"),
    TableEntry("registry_dir", "tables/meta/registry"),
    TableEntry("dag", "tables/derived/dag.json"),
    TableEntry("tier_wave_damage_legacy", "tables/legacy/tier_wave_damage.csv"),
    TableEntry("tournament_wave_damage_legacy", "tables/legacy/tournament_wave_damage.csv"),
)


def _validate_manifest(entries: Iterable[TableEntry]) -> dict[str, TableEntry]:
    resolved: dict[str, TableEntry] = {}
    for entry in entries:
        if entry.key in resolved:
            raise TablePathError(f"Duplicate table manifest key: {entry.key}")
        resolved[entry.key] = entry
    return resolved


TABLE_MANIFEST: Mapping[str, TableEntry] = _validate_manifest(_TABLE_MANIFEST)


def resolve_table_path(key: str, *, runtime_mode: bool = True) -> Path:
    entry = TABLE_MANIFEST.get(key)
    if entry is None:
        raise TablePathError(f"Unknown table manifest key: {key}")

    if runtime_mode and _is_runtime_restricted(entry.relative_path):
        raise TablePathError(
            f"Runtime table resolution rejected non-canonical key {key!r}: {entry.relative_path}"
        )

    path = entry.path
    if not path.exists():
        raise FileNotFoundError(f"Missing required table for key {key!r}: {entry.relative_path}")
    return path


def _is_runtime_restricted(relative_path: str) -> bool:
    return relative_path.startswith("tables/legacy/") or relative_path.startswith("tables/cache/")
