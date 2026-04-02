from qe.materializer import _normalize_composition_stage
from qe.models import StatInput
from qe.query_routing import ENHANCEMENT_ALIAS_OVERRIDES


def _enhancement_row(stat_name: str, destination_id: str) -> StatInput:
    return StatInput(
        stat_name=stat_name,
        source_family='enhancement',
        source_name=stat_name,
        value=1.75,
        value_type='resolved_value',
        stage='account_state',
        destination_object_type='canonical_stat',
        destination_id=destination_id,
    )


def test_enhancement_without_contributor_id_is_multiplicative() -> None:
    row = _enhancement_row('Attack Speed+', 'tower_attack_speed')

    assert _normalize_composition_stage('state::tower.attack_speed', row) == 'multiplicative'


def test_all_enhancement_aliases_compose_multiplicatively() -> None:
    # Every routed enhancement alias must compose multiplicatively without contributor overrides.
    for alias, destination_id in ENHANCEMENT_ALIAS_OVERRIDES.items():
        row = _enhancement_row(alias, destination_id)
        assert _normalize_composition_stage(f'state::{destination_id}', row) == 'multiplicative'


def test_enhancement_contributor_overrides_removed() -> None:
    import qe.query_routing as query_routing

    assert not hasattr(query_routing, 'ENHANCEMENT_CONTRIBUTOR_OVERRIDES')
