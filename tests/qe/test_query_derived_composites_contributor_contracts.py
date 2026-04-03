from __future__ import annotations

import pytest

from qe.contracts import normalize_surface_id_to_contract
from qe.models import StatRow
import qe.query_derived_composites as derived


@pytest.mark.parametrize('source_key', ['canonical_stat::tower_hp', 'state::tower.hp'])
def test_publish_derived_composites_normalizes_contributor_surface_key(source_key: str) -> None:
    normalized_key = normalize_surface_id_to_contract(source_key)
    rows = {
        source_key: StatRow(
            stat_name=source_key,
            final_value=100.0,
            value_type='flat',
            source_count=1,
            status='resolved',
            contributors=[],
            schema=None,
        )
    }

    derived.publish_derived_composites(rows)

    ehp_row = rows['derived::ehp']
    tower_hp_contributor = next(c for c in ehp_row.contributors if c['stat_name'] == normalized_key)
    assert tower_hp_contributor['stat_name'] == normalized_key
    assert tower_hp_contributor['source_name'] == normalized_key
    assert tower_hp_contributor['kb_mapped'] is True
