from __future__ import annotations

import csv
from pathlib import Path

import yaml

from qe.query_routing import (
    CARD_NAME_FALLBACK_DESTINATION,
    CARD_TARGET_SURFACE_TO_CANONICAL,
    CARD_TARGET_SURFACE_TO_DESTINATION,
    DIRECT_WORKSHOP_TABLE_COLUMNS,
    ENHANCEMENT_ALIAS_OVERRIDES,
    LAB_APPLICATION_TARGET_TO_DESTINATION,
    LAB_IDS_TO_CONTRIBUTOR,
    MODULE_SUBSTAT_NAME_TO_DESTINATION,
    PERK_TARGET_DESTINATION_OVERRIDES,
    RELIC_CONTRIBUTOR_OVERRIDES,
    WORKSHOP_IDS_TO_CONTRIBUTOR,
    _UW_LAB_DIRECT_DESTINATION,
    uw_contributor_id,
)


def _load_query_routing_mapping_table() -> dict:
    path = Path(__file__).resolve().parents[2] / 'kb' / 'global-rules' / 'contracts' / 'query-routing-mappings.yaml'
    return yaml.safe_load(path.read_text(encoding='utf-8')) or {}


def _tuple_destination_map(raw: dict[str, list[str]] | None) -> dict[str, tuple[str, str]]:
    return {k: tuple(v) for k, v in (raw or {}).items()}


def _nested_destination_map(rows: list[dict] | None) -> dict[tuple[str, str], tuple[str, str]]:
    out: dict[tuple[str, str], tuple[str, str]] = {}
    for row in rows or []:
        out[(row['destination_namespace'], row['destination_field'])] = (
            row['destination_object_type'],
            row['destination_id'],
        )
    return out


def test_query_routing_maps_are_loaded_from_kb_contract_surface() -> None:
    table = _load_query_routing_mapping_table()

    assert _UW_LAB_DIRECT_DESTINATION == _tuple_destination_map(table['uw_lab_direct_destination'])
    assert WORKSHOP_IDS_TO_CONTRIBUTOR == table['workshop_ids_to_contributor']
    assert LAB_IDS_TO_CONTRIBUTOR == table['lab_ids_to_contributor']
    assert DIRECT_WORKSHOP_TABLE_COLUMNS == table['direct_workshop_table_columns']
    assert CARD_TARGET_SURFACE_TO_CANONICAL == table['card_target_surface_to_canonical']
    assert CARD_TARGET_SURFACE_TO_DESTINATION == _tuple_destination_map(table['card_target_surface_to_destination'])
    assert LAB_APPLICATION_TARGET_TO_DESTINATION == _nested_destination_map(table['lab_application_target_to_destination'])
    assert CARD_NAME_FALLBACK_DESTINATION == _tuple_destination_map(table['card_name_fallback_destination'])
    assert MODULE_SUBSTAT_NAME_TO_DESTINATION == _tuple_destination_map(table['module_substat_name_to_destination'])
    assert ENHANCEMENT_ALIAS_OVERRIDES == table['enhancement_alias_overrides']
    assert RELIC_CONTRIBUTOR_OVERRIDES == table['relic_contributor_overrides']
    assert PERK_TARGET_DESTINATION_OVERRIDES == _tuple_destination_map(table['perk_target_destination_overrides'])


def test_uw_contributor_id_is_sourced_from_kb_mapping_surface() -> None:
    table = _load_query_routing_mapping_table()
    expected = {
        (row['uw_name'], row['track_name']): row['contributor_id']
        for row in table['uw_contributor_map']
    }

    for (uw_name, track_name), contributor_id in expected.items():
        assert uw_contributor_id(uw_name, track_name) == contributor_id

    assert uw_contributor_id('Unknown UW', 'Unknown Track') is None


def test_audited_base_cards_have_kb_effect_registry_rows_with_explicit_target_surfaces() -> None:
    path = Path(__file__).resolve().parents[2] / 'kb' / 'cards' / 'tables' / 'card-effect-registry.csv'
    rows = {}
    with path.open(newline='', encoding='utf-8') as fh:
        for row in csv.DictReader(fh):
            if row.get('layer') == 'base_card':
                rows[row['card_id']] = row['target_surface']

    assert rows['AREA_OF_EFFECT'] == 'cards.aoe.level'
    assert rows['BERSERKER'] == 'cards.berserker.absorbed_damage_pct'
    assert rows['DEATH_RAY'] == 'cards.death_ray.duration_seconds'
    assert rows['DEMON_MODE'] == 'cards.demon_mode.duration_seconds'
    assert rows['ENEMY_BALANCE'] == 'enemy_balance.runtime_bonus'
    assert rows['ENERGY_NET'] == 'cards.energy_net.duration_seconds'
    assert rows['ENERGY_SHIELD'] == 'cards.energy_shield.recharge_cooldown_seconds'
    assert rows['FORTRESS'] == 'tower.defense_absolute_multiplier'
    assert rows['LAND_MINE_STUN'] == 'cards.land_mine_stun.duration_seconds'
    assert rows['NUKE'] == 'cards.nuke.enemy_fraction_pct'
    assert rows['RANGE'] == 'tower.range_multiplier'
    assert rows['RECOVERY_PACKAGE_CHANCE'] == 'tower.recovery_package_chance_percent_points'
    assert rows['SECOND_WIND'] == 'cards.second_wind.shield_duration_seconds'
    assert rows['SLOW_AURA'] == 'cards.slow_aura.enemy_speed_pct'
    assert rows['SUPER_TOWER'] == 'cards.super_tower.bonus_multiplier'
    assert rows['ULTIMATE_CRIT'] == 'cards.ultimate_crit.chance_pct'
    assert rows['WAVE_ACCELERATOR'] == 'waves.spawn_rate_acceleration'
    assert rows['WAVE_SKIP'] == 'waves.skip_chance'
