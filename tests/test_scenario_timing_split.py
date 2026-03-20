"""Tests for split scenario and timing engines.

Every assertion is grounded in a named KB source or documented formula.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.scenario_engine import (
    ScenarioConfig,
    ScenarioSurfaces,
    _interpolate_bc_magnitude,
    _load_boss_enemy_class_resistances,
    _load_tier_battle_conditions,
    _load_tournament_bc_magnitudes,
    _reduce_additive_magnitude,
    _reduce_resistance_multiplier,
    compute_cf_damage_reduction_pct,
    compute_scenario_surfaces,
    config_from_statbook,
)
from engine.timing_engine import _uptime, compute_timing_surfaces, overlap_fraction, TimingMechanic




class _CombinedSurfaces:
    def __init__(self, scenario, timing):
        self._scenario = scenario
        self._timing = timing
        self.__dict__.update(scenario.to_dict())
        self.__dict__.update(timing.__dict__)

    def to_dict(self):
        out = dict(self._scenario.to_dict())
        out.update(self._timing.__dict__)
        return out


def _combined_surfaces(config: ScenarioConfig):
    scenario = compute_scenario_surfaces(config)
    timing = compute_timing_surfaces(config, scenario)
    return _CombinedSurfaces(scenario, timing)
# ═══ BC reduction math ═══


def test_reduce_resistance_identity():
    assert _reduce_resistance_multiplier(0.5, 0.0) == 0.5


def test_reduce_resistance_10pct():
    # 0.5 raw, 10% lab: penalty 0.5 * 0.90 = 0.45, effective = 0.55
    assert abs(_reduce_resistance_multiplier(0.5, 10.0) - 0.55) < 1e-9


def test_reduce_resistance_full():
    assert abs(_reduce_resistance_multiplier(0.3, 100.0) - 1.0) < 1e-9


def test_reduce_resistance_no_effect_above_1():
    assert _reduce_resistance_multiplier(1.0, 50.0) == 1.0


def test_reduce_additive_10pct():
    assert abs(_reduce_additive_magnitude(5.0, 10.0) - 4.5) < 1e-9


def test_reduce_additive_full():
    assert abs(_reduce_additive_magnitude(5.0, 100.0)) < 1e-9


def test_reduce_additive_negative_value():
    # UW duration BC: -5 seconds, 10% reduction -> -4.5
    assert abs(_reduce_additive_magnitude(-5.0, 10.0) - (-4.5)) < 1e-9


# ═══ Uptime ═══


def test_uptime_basic():
    assert abs(_uptime(29.0, 15.0) - 29.0 / 44.0) < 1e-9


def test_uptime_zero_duration():
    assert _uptime(0.0, 15.0) == 0.0


def test_uptime_zero_cooldown():
    assert _uptime(29.0, 0.0) == 1.0


def test_uptime_both_zero():
    assert _uptime(0.0, 0.0) == 0.0


# ═══ BC magnitude interpolation ═══


def test_interpolate_exact():
    assert _interpolate_bc_magnitude({0: 0.9, 20: 0.75}, 20) == 0.75


def test_interpolate_between():
    assert _interpolate_bc_magnitude({0: 0.9, 20: 0.75, 40: 0.5}, 30) == 0.75


def test_interpolate_beyond():
    assert _interpolate_bc_magnitude({0: 0.9, 20: 0.75}, 100) == 0.75


# ═══ KB table loaders ═══


def test_tier_bcs_has_t14_through_t21():
    tiers = _load_tier_battle_conditions()
    for t in range(14, 22):
        assert t in tiers, f"Missing tier {t}"


def test_tier_14_resistance_values():
    """KB: tier-battle-conditions.csv T14 known values."""
    t14 = _load_tier_battle_conditions()[14]
    assert float(t14["orb_resistance"]["value"]) == 0.5
    assert float(t14["plasma_cannon_resistance"]["value"]) == 0.8
    assert float(t14["thorns_resistance"]["value"]) == 0.8


def test_tier_14_more_bosses():
    """KB: tier-battle-conditions.csv T14 more_bosses = 9 waves."""
    t14 = _load_tier_battle_conditions()[14]
    assert float(t14["more_bosses"]["value"]) == 9.0


def test_tournament_magnitudes_complete():
    mags = _load_tournament_bc_magnitudes()
    for bc in ("plasma_cannon_resistance", "orb_resistance", "thorns_resistance",
               "enemy_attack_speed", "ultimate_weapons_duration", "more_bosses"):
        assert bc in mags, f"Missing {bc}"
        assert len(mags[bc]) >= 10, f"{bc} has too few wave entries"


def test_tournament_orb_resistance_boundary_values():
    """KB: battle-condition-magnitudes.csv known values."""
    mags = _load_tournament_bc_magnitudes()
    assert mags["orb_resistance"][0] == 0.9
    assert mags["orb_resistance"][1000] == 0.01


def test_tournament_enemy_attack_speed_boundary_values():
    """KB: battle-condition-magnitudes.csv: 0.05 at wave 0, 5 at wave 1000."""
    mags = _load_tournament_bc_magnitudes()
    assert mags["enemy_attack_speed"][0] == 0.05
    assert mags["enemy_attack_speed"][1000] == 5.0


def test_tournament_uw_duration_boundary_values():
    """KB: battle-condition-magnitudes.csv: -1 at wave 0, -10 at wave 1000."""
    mags = _load_tournament_bc_magnitudes()
    assert mags["ultimate_weapons_duration"][0] == -1.0
    assert mags["ultimate_weapons_duration"][1000] == -10.0


def test_tournament_more_bosses_is_constant_6():
    """KB: battle-condition-magnitudes.csv: 6 at all waves."""
    mags = _load_tournament_bc_magnitudes()
    for wave in (0, 100, 500, 1000):
        assert mags["more_bosses"][wave] == 6.0


def test_boss_class_resistances():
    """KB: enemy-class-interaction-matrix.csv HIGH confidence."""
    r = _load_boss_enemy_class_resistances()
    assert r["thorns"] == 0.5
    assert r["oa_electrons"] == 0.25


# ═══ Farming mode full scenario ═══


def _farming_t14_config(**overrides) -> ScenarioConfig:
    base = dict(
        mode_id="farming", tier=14,
        bh_base_duration_s=29.0, bh_base_cooldown_s=15.0,
        cf_base_duration_s=20.0, cf_base_cooldown_s=12.0, cf_slow_pct=6.0,
        cf_damage_reduction_pct=30.0,  # unlock 10% + Reduction% lab level 20 = 20%
        gt_base_duration_s=22.0, gt_base_cooldown_s=12.0,
        env_enemy_damage_multiplier=0.45,
        env_boss_health_multiplier=9.84,
        env_boss_speed_multiplier=1.5,
        bot_amplify_duration_s=20.0, bot_amplify_cooldown_s=120.0,
        bot_golden_duration_s=27.5, bot_golden_cooldown_s=90.0,
        bot_thunder_duration_s=5.0, bot_thunder_cooldown_s=120.0,
        bot_flame_cooldown_s=8.0, bot_flame_damage_reduction_pct=0.47,
        tower_orb_count=6, tower_orb_speed_rpm=6.832, electron_count=2,
    )
    base.update(overrides)
    return ScenarioConfig(**base)


def test_farming_t14_bc_resistances():
    s = _combined_surfaces(_farming_t14_config())
    assert s.bc_plasma_cannon_resistance == 0.8
    assert s.bc_orb_resistance == 0.5
    assert s.bc_thorns_resistance == 0.8


def test_farming_no_enemy_attack_speed():
    """Tier BCs do not include enemy_attack_speed -> base 2.0s hit interval."""
    s = _combined_surfaces(_farming_t14_config())
    assert s.bc_enemy_attack_speed_increase_pct == 0.0
    assert s.boss_hit_interval_seconds == 2.0


def test_farming_t14_more_bosses():
    """T14 more_bosses = 9 waves."""
    s = _combined_surfaces(_farming_t14_config())
    assert s.boss_wave_interval == 9


def test_farming_no_uw_duration_bc():
    """Tier BCs do not include UW duration reduction -> full UW durations."""
    s = _combined_surfaces(_farming_t14_config())
    assert s.bc_uw_duration_reduction_s == 0.0
    assert s.bh_effective_duration_s == 29.0
    assert s.cf_effective_duration_s == 20.0
    assert s.gt_effective_duration_s == 22.0


def test_farming_t14_uw_uptime():
    s = _combined_surfaces(_farming_t14_config())
    assert abs(s.bh_uptime_fraction - 29.0 / 44.0) < 1e-9
    assert abs(s.cf_uptime_fraction - 20.0 / 32.0) < 1e-9
    assert abs(s.gt_uptime_fraction - 22.0 / 34.0) < 1e-9


def test_farming_t14_with_perk_adds():
    s = _combined_surfaces(_farming_t14_config(
        bh_perk_duration_add_s=12.0, bh_perk_cooldown_add_s=-4.0,
        cf_perk_duration_add_s=5.0,
    ))
    # BH: (29+12) / (29+12 + 15-4) = 41/52
    assert abs(s.bh_uptime_fraction - 41.0 / 52.0) < 1e-9
    assert s.bh_effective_duration_s == 41.0
    assert s.bh_effective_cooldown_s == 11.0
    # CF: (20+5) / (20+5 + 12) = 25/37
    assert abs(s.cf_uptime_fraction - 25.0 / 37.0) < 1e-9


def test_farming_t14_environment_passthrough():
    s = _combined_surfaces(_farming_t14_config())
    assert s.env_enemy_damage_multiplier == 0.45
    assert s.env_boss_health_multiplier == 9.84
    assert s.env_boss_speed_multiplier == 1.5


def test_farming_t14_bot_uptime():
    s = _combined_surfaces(_farming_t14_config())
    assert abs(s.bot_amplify_uptime_fraction - 20.0 / 140.0) < 1e-9
    assert abs(s.bot_golden_uptime_fraction - 27.5 / 117.5) < 1e-9
    assert abs(s.bot_thunder_uptime_fraction - 5.0 / 125.0) < 1e-9


def test_farming_t14_orb_electron_passthrough():
    s = _combined_surfaces(_farming_t14_config())
    assert s.tower_orb_count == 6
    assert s.tower_orb_speed_rpm == 6.832
    assert s.electron_count == 2
    assert "BLOCKED" in s.orb_boss_hit_rate_status
    assert "BLOCKED" in s.electron_boss_hit_rate_status


def test_farming_t14_boss_class_resistances():
    s = _combined_surfaces(_farming_t14_config())
    assert s.boss_thorns_effectiveness == 0.5
    assert s.boss_electron_effectiveness == 0.25


def test_farming_t14_cf_damage_reduction():
    """CF DR: 30% when active, averaged over uptime."""
    s = _combined_surfaces(_farming_t14_config())
    assert s.cf_damage_reduction_pct == 30.0
    # uptime = 20/(20+12) = 0.625, avg DR fraction = 0.625 * 0.30 = 0.1875
    expected = (20.0 / 32.0) * (30.0 / 100.0)
    assert abs(s.cf_avg_damage_reduction_fraction - expected) < 1e-9
    assert s.cf_slow_pct == 6.0  # separate mechanic, not DR


def test_cf_dr_zero_when_no_unlock():
    """No CF DR unlock -> 0% reduction."""
    s = _combined_surfaces(_farming_t14_config(cf_damage_reduction_pct=0.0))
    assert s.cf_damage_reduction_pct == 0.0
    assert s.cf_avg_damage_reduction_fraction == 0.0


def test_compute_cf_damage_reduction_pct_formula():
    """KB: unlock=10%, Reduction% lab = 10.5 + (level-1)*0.5."""
    assert compute_cf_damage_reduction_pct(0, 0) == 0.0
    assert compute_cf_damage_reduction_pct(1, 0) == 10.0
    assert compute_cf_damage_reduction_pct(1, 1) == 20.5   # 10 + 10.5
    assert compute_cf_damage_reduction_pct(1, 20) == 30.0   # 10 + 20.0
    assert compute_cf_damage_reduction_pct(1, 30) == 35.0   # 10 + 25.0


def test_farming_t14_bc_reduction_group1():
    """10% group 1 reduction moves resistances toward 1.0."""
    s = _combined_surfaces(_farming_t14_config(bc_reduction_group1_pct=10.0))
    assert abs(s.bc_plasma_cannon_resistance - 0.82) < 1e-9   # 0.8 + 0.2*0.10
    assert abs(s.bc_orb_resistance - 0.55) < 1e-9             # 0.5 + 0.5*0.10


def test_farming_t14_enemy_level_skip_reduction():
    """KB: T14 enemy_level_skip_reduction = 0.025 pp."""
    s = _combined_surfaces(_farming_t14_config())
    assert abs(s.bc_enemy_level_skip_reduction_pp - 0.025) < 1e-9


def test_farming_no_death_defy_or_energy_shields_bc():
    """Tier BCs do not include death_defy_down or energy_shields_down."""
    s = _combined_surfaces(_farming_t14_config())
    assert s.bc_death_defy_down_pp == 0.0
    assert s.bc_energy_shields_down_fraction == 0.0


def test_farming_t14_flame_bot_passthrough():
    """Flame bot: no duration, activation-based. Pass-through cooldown and DR."""
    s = _combined_surfaces(_farming_t14_config(
        bot_flame_cooldown_s=8.0, bot_flame_damage_reduction_pct=0.47,
    ))
    assert s.bot_flame_cooldown_s == 8.0
    assert abs(s.bot_flame_damage_reduction_pct - 0.47) < 1e-9


def test_farming_deferred_bc_note():
    s = _combined_surfaces(_farming_t14_config())
    assert "deferred" in s.deferred_bc_note


# ═══ Tournament mode full scenario ═══


def _tournament_config(wave: int = 0, **overrides) -> ScenarioConfig:
    base = dict(
        mode_id="tournament", league="champion", tournament_wave=wave,
        bh_base_duration_s=29.0, bh_base_cooldown_s=15.0,
        cf_base_duration_s=20.0, cf_base_cooldown_s=12.0, cf_slow_pct=6.0,
        cf_damage_reduction_pct=30.0,
        gt_base_duration_s=22.0, gt_base_cooldown_s=12.0,
        tower_orb_count=6, tower_orb_speed_rpm=6.832, electron_count=2,
    )
    base.update(overrides)
    return ScenarioConfig(**base)


def test_tournament_wave_0_resistances():
    """KB: magnitudes at wave 0."""
    s = _combined_surfaces(_tournament_config(0))
    assert abs(s.bc_plasma_cannon_resistance - 0.95) < 1e-9
    assert abs(s.bc_orb_resistance - 0.9) < 1e-9
    assert abs(s.bc_thorns_resistance - 0.95) < 1e-9


def test_tournament_wave_1000_resistances():
    s = _combined_surfaces(_tournament_config(1000))
    assert abs(s.bc_plasma_cannon_resistance - 0.05) < 1e-9
    assert abs(s.bc_orb_resistance - 0.01) < 1e-9
    assert abs(s.bc_thorns_resistance - 0.05) < 1e-9


def test_tournament_enemy_attack_speed_wave_0():
    """KB: enemy_attack_speed magnitude 0.05 at wave 0 = 5% increase."""
    s = _combined_surfaces(_tournament_config(0))
    assert abs(s.bc_enemy_attack_speed_increase_pct - 5.0) < 1e-9
    # Hit interval: 2.0 / (1 + 5/100) = 2.0 / 1.05 ≈ 1.905
    assert abs(s.boss_hit_interval_seconds - 2.0 / 1.05) < 1e-6


def test_tournament_enemy_attack_speed_wave_1000():
    """KB: enemy_attack_speed magnitude 5 at wave 1000 = 500% increase."""
    s = _combined_surfaces(_tournament_config(1000))
    assert abs(s.bc_enemy_attack_speed_increase_pct - 500.0) < 1e-9
    # Hit interval: 2.0 / (1 + 5.0) = 2.0 / 6.0 ≈ 0.333
    assert abs(s.boss_hit_interval_seconds - 2.0 / 6.0) < 1e-6


def test_tournament_uw_duration_bc_wave_0():
    """KB: UW duration magnitude -1 at wave 0 -> durations reduced by 1s."""
    s = _combined_surfaces(_tournament_config(0))
    assert abs(s.bc_uw_duration_reduction_s - (-1.0)) < 1e-9
    assert s.bh_effective_duration_s == 28.0   # 29 - 1
    assert s.cf_effective_duration_s == 19.0   # 20 - 1
    assert s.gt_effective_duration_s == 21.0   # 22 - 1


def test_tournament_uw_duration_bc_wave_1000():
    """KB: UW duration magnitude -10 at wave 1000 -> reduced by 10s."""
    s = _combined_surfaces(_tournament_config(1000))
    assert abs(s.bc_uw_duration_reduction_s - (-10.0)) < 1e-9
    assert s.bh_effective_duration_s == 19.0   # 29 - 10
    assert s.cf_effective_duration_s == 10.0   # 20 - 10
    assert s.gt_effective_duration_s == 12.0   # 22 - 10


def test_tournament_uw_duration_cannot_go_negative():
    """UW duration floored at 0 if BC reduction exceeds base duration."""
    s = _combined_surfaces(_tournament_config(1000,
        cf_base_duration_s=5.0,  # 5 - 10 would be negative
    ))
    assert s.cf_effective_duration_s == 0.0
    assert s.cf_uptime_fraction == 0.0


def test_tournament_more_bosses_is_6():
    """KB: more_bosses constant 6 in tournament."""
    s = _combined_surfaces(_tournament_config(0))
    assert s.boss_wave_interval == 6


def test_tournament_death_defy_down_wave_0():
    """KB: death_defy_down magnitude -0.01 at wave 0."""
    s = _combined_surfaces(_tournament_config(0))
    assert abs(s.bc_death_defy_down_pp - (-0.01)) < 1e-9


def test_tournament_death_defy_down_wave_1000():
    """KB: death_defy_down magnitude -0.3 at wave 1000."""
    s = _combined_surfaces(_tournament_config(1000))
    assert abs(s.bc_death_defy_down_pp - (-0.3)) < 1e-9


def test_tournament_energy_shields_down_wave_0():
    """KB: energy_shields_down magnitude 0.01 at wave 0."""
    s = _combined_surfaces(_tournament_config(0))
    assert abs(s.bc_energy_shields_down_fraction - 0.01) < 1e-9


def test_tournament_energy_shields_down_wave_1000():
    """KB: energy_shields_down magnitude 1.0 at wave 1000 (fully disabled)."""
    s = _combined_surfaces(_tournament_config(1000))
    assert abs(s.bc_energy_shields_down_fraction - 1.0) < 1e-9


def test_tournament_group4_reduction_reduces_death_defy_penalty():
    """Group 4 BC reduction lab shrinks death_defy_down penalty."""
    s = _combined_surfaces(_tournament_config(1000, bc_reduction_group4_pct=10.0))
    # raw=-0.3, 10% reduction: -0.3 * 0.9 = -0.27
    assert abs(s.bc_death_defy_down_pp - (-0.27)) < 1e-9


def test_tournament_group4_reduction_reduces_energy_shields_penalty():
    """Group 4 BC reduction lab shrinks energy_shields_down penalty."""
    s = _combined_surfaces(_tournament_config(1000, bc_reduction_group4_pct=10.0))
    # raw=1.0, 10% reduction: 1.0 * 0.9 = 0.9
    assert abs(s.bc_energy_shields_down_fraction - 0.9) < 1e-9


def test_tournament_bc_source_label():
    s = _combined_surfaces(_tournament_config(100))
    assert "tournament_magnitudes" in s.bc_source
    assert "wave=100" in s.bc_source


# ═══ Stat engine bridge ═══


def test_bridge_from_actual_statbook():
    """End-to-end: load actual stat engine output and build config.

    R32 baseline: orb_count=8 (perk Orbs+1 fix), GT duration=41.0 (lab),
    CF DR=20.0 (R32 semantics: 10% base + 10% Reduction% lab).
    """
    out_path = ROOT / "out" / "statbook.json"
    if not out_path.exists():
        return  # skip if no output available
    rows = json.loads(out_path.read_text())["rows"]
    config = config_from_statbook(rows, mode_id="farming", tier=14)
    assert config.bh_base_duration_s > 0.0
    assert config.cf_base_duration_s > 0.0
    assert config.tower_orb_count == 8  # orb perk routing still present
    # CF DR auto-read from stat engine remains explicit and positive.
    assert config.cf_damage_reduction_pct > 0.0
    s = _combined_surfaces(config)
    assert s.mode_id == "farming"
    assert s.boss_wave_interval == 9
    assert s.cf_damage_reduction_pct == config.cf_damage_reduction_pct
    assert s.surfaces_status == "complete"


def test_bridge_cf_dr_auto_read_vs_override():
    """CF DR: auto-read from stat engine when no override, override wins when given."""
    out_path = ROOT / "out" / "statbook.json"
    if not out_path.exists():
        return
    rows = json.loads(out_path.read_text())["rows"]
    # Auto-read: should get 20.0 from R32 stat engine
    auto = config_from_statbook(rows, mode_id="farming", tier=14)
    assert auto.cf_damage_reduction_pct == 20.0
    # Explicit override: should use the given value
    manual = config_from_statbook(rows, mode_id="farming", tier=14,
                                   cf_damage_reduction_pct=35.0)
    assert manual.cf_damage_reduction_pct == 35.0


# ═══ Serialization ═══


def test_to_dict_complete():
    s = _combined_surfaces(_farming_t14_config())
    d = s.to_dict()
    assert isinstance(d, dict)
    required = [
        "mode_id", "bc_plasma_cannon_resistance", "bc_orb_resistance",
        "bc_thorns_resistance", "bc_enemy_attack_speed_increase_pct",
        "bc_uw_duration_reduction_s", "bc_death_defy_down_pp",
        "bc_energy_shields_down_fraction", "boss_wave_interval",
        "boss_hit_interval_seconds", "boss_thorns_effectiveness",
        "boss_electron_effectiveness", "env_enemy_damage_multiplier",
        "bh_uptime_fraction", "cf_uptime_fraction", "gt_uptime_fraction",
        "cf_damage_reduction_pct", "cf_avg_damage_reduction_fraction", "cf_slow_pct",
        "bot_amplify_uptime_fraction", "bot_golden_uptime_fraction",
        "bot_flame_cooldown_s", "bot_flame_damage_reduction_pct",
        "tower_orb_count", "electron_count", "surfaces_status",
        "deferred_bc_note",
    ]
    for key in required:
        assert key in d, f"Missing key: {key}"


# ═══ Runner ═══


if __name__ == "__main__":
    import inspect

    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for fn in tests:
        try:
            fn()
            print(f"  PASS: {fn.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {fn.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)
