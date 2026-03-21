from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.boss_wave_engine import BossWaveEngine, BossWaveEngineConfig, ResolvedRuntimeInputs


def test_boss_wave_engine_numeric_ttk_regression_with_simultaneous_events():
    runtime_inputs = ResolvedRuntimeInputs(
        boss_hit_interval_seconds=1.0,
        boss_contact_time_seconds=1.0,
        orb_boss_hit_pct=50.0,
        orb_boss_hits_per_second=1.0,
        electron_hits_per_second=1.0,
        effective_damage_reduction_pct=None,
        incoming_damage_multiplier=1.0,
        source_notes=[],
    )

    result = BossWaveEngine._simulate_boss_ttk(
        boss_effective_hp=1000.0,
        plasma_cannon_effect_pct=20.0,
        tower_thorns_damage_pct=100.0,
        runtime_inputs=runtime_inputs,
        config=BossWaveEngineConfig(
            preset_name='Farming',
            mode_id='farming',
            tier_column='Tier 12',
            start_boss_wave=10,
            end_boss_wave=10,
            max_ttk_seconds=10.0,
        ),
    )

    # Equation:
    # start_after_pc = 1000 * (1 - 0.20) = 800
    # per timestamp when orb + electron + contact coincide:
    # remaining *= (1 - 0.50) * (1 - 0.0375) * (1 - (1.00 * 0.50))
    # remaining *= 0.5 * 0.9625 * 0.5 = 0.240625
    # after 5 timestamps: 800 * 0.240625^5 = 0.6453476326465607 < 1, so ttk = 5.0 seconds
    assert math.isclose(result.remaining_hp_after_opening, 800.0, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(result.ttk_seconds, 5.0, rel_tol=0.0, abs_tol=1e-12)
    assert result.orb_hits_used == 5
    assert result.electron_hits_used == 5
    assert result.thorns_contact_events_used == 5


def test_boss_wave_engine_numeric_damage_intake_regression_with_heat_up():
    runtime_inputs = ResolvedRuntimeInputs(
        boss_hit_interval_seconds=1.0,
        boss_contact_time_seconds=1.0,
        orb_boss_hit_pct=1.0,
        orb_boss_hits_per_second=1.0,
        electron_hits_per_second=1.0,
        effective_damage_reduction_pct=25.0,
        incoming_damage_multiplier=2.0,
        source_notes=[],
    )

    result = BossWaveEngine._simulate_boss_damage_intake(
        boss_base_damage=100.0,
        ttk_seconds=3.2,
        wall_hp=500.0,
        wall_regen=10.0,
        wall_fortification_multiplier=2.0,
        tower_defense_pct=None,
        runtime_inputs=runtime_inputs,
        timing_context=None,
        config=BossWaveEngineConfig(
            preset_name='Farming',
            mode_id='farming',
            tier_column='Tier 12',
            start_boss_wave=10,
            end_boss_wave=10,
        ),
    )

    # Hits at t = 1.0, 2.0, 3.0 only.
    # Damage per hit after incoming multiplier and 25% DR:
    # hit 1: 100 * 2.0 * 1.00 * 0.75 = 150
    # hit 2: 100 * 2.0 * 1.04 * 0.75 = 156
    # hit 3: 100 * 2.0 * 1.08 * 0.75 = 162
    # total_damage = 468
    # effective_wall_hp_pool = 500 * 2 = 1000
    # wall_regen_gained = 10 * 3.2 = 32
    # wall_hp_after_boss = 1000 + 32 - 468 = 564
    assert result.boss_hits_taken == 3
    assert math.isclose(result.total_damage_taken, 468.0, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(result.effective_wall_hp_pool, 1000.0, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(result.wall_regen_gained, 32.0, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(result.wall_hp_after_boss, 564.0, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(result.survival_margin_hp, 564.0, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(result.damage_reduction_pct_used, 25.0, rel_tol=0.0, abs_tol=1e-12)


def test_boss_wave_engine_numeric_damage_intake_regression_without_contact():
    runtime_inputs = ResolvedRuntimeInputs(
        boss_hit_interval_seconds=1.0,
        boss_contact_time_seconds=None,
        orb_boss_hit_pct=1.0,
        orb_boss_hits_per_second=1.0,
        electron_hits_per_second=1.0,
        effective_damage_reduction_pct=40.0,
        incoming_damage_multiplier=1.0,
        source_notes=[],
    )

    result = BossWaveEngine._simulate_boss_damage_intake(
        boss_base_damage=100.0,
        ttk_seconds=4.5,
        wall_hp=200.0,
        wall_regen=5.0,
        wall_fortification_multiplier=1.5,
        tower_defense_pct=None,
        runtime_inputs=runtime_inputs,
        timing_context=None,
        config=BossWaveEngineConfig(
            preset_name='Farming',
            mode_id='farming',
            tier_column='Tier 12',
            start_boss_wave=10,
            end_boss_wave=10,
        ),
    )

    # No boss contact means no hits taken.
    # effective_wall_hp_pool = 200 * 1.5 = 300
    # wall_regen_gained = 5 * 4.5 = 22.5
    # wall_hp_after_boss = 322.5
    assert result.boss_hits_taken == 0
    assert math.isclose(result.total_damage_taken, 0.0, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(result.effective_wall_hp_pool, 300.0, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(result.wall_regen_gained, 22.5, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(result.wall_hp_after_boss, 322.5, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(result.survival_margin_hp, 322.5, rel_tol=0.0, abs_tol=1e-12)
