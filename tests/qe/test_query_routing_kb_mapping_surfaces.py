from __future__ import annotations

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
