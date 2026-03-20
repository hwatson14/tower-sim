from __future__ import annotations

import pytest

from tower_sim.engines.stat_engine import StatInput
from tower_sim.registry.stat_registry import Phase
from v3.stat_engine import V3StatEngine, V3StatEngineError


def test_v3_stat_engine_composes_standard_row() -> None:
    engine = V3StatEngine()
    result = engine.build(
        [
            StatInput(
                stat_id="tower_hp",
                phase=Phase.START_OF_RUN,
                base_value=100.0,
                loadout_delta=5.0,
                enhancement_multiplier=1.1,
                provenance="test:tower_hp",
                contributor_family="workshop",
            )
        ]
    )
    assert len(result.rows) == 1
    assert result.run_stats[Phase.START_OF_RUN]["tower_hp"] == pytest.approx(115.5)


def test_v3_stat_engine_rejects_derived_mixed_with_components() -> None:
    engine = V3StatEngine()
    with pytest.raises(V3StatEngineError, match="cannot mix"):
        engine.build(
            [
                StatInput(
                    stat_id="wave_attack_index",
                    phase=Phase.AT_WAVE,
                    base_value=1.0,
                    derived_value=10.0,
                    provenance="test:bad",
                    contributor_family="base",
                )
            ]
        )
