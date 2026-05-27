from __future__ import annotations

import math

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


def test_publish_derived_composites_publishes_wall_hp_pre_fort_surface() -> None:
    rows = {
        'state::tower.hp': StatRow(stat_name='state::tower.hp', final_value=100.0, value_type='hp', source_count=1, status='resolved', contributors=[], schema=None),
        'state::wall.hp': StatRow(stat_name='state::wall.hp', final_value=520.0, value_type='hp', source_count=1, status='resolved', contributors=[], schema=None),
        'support_surface::ehp.wall_hp_ws': StatRow(stat_name='support_surface::ehp.wall_hp_ws', final_value=100.0, value_type='hp', source_count=0, status='resolved', contributors=[], schema=None),
        'support_surface::ehp.wall_hp_lab_level': StatRow(stat_name='support_surface::ehp.wall_hp_lab_level', final_value=50.0, value_type='scalar', source_count=0, status='resolved', contributors=[], schema=None),
        'support_surface::ehp.wall_hp_prim_sub': StatRow(stat_name='support_surface::ehp.wall_hp_prim_sub', final_value=10.0, value_type='scalar', source_count=0, status='resolved', contributors=[], schema=None),
        'support_surface::ehp.wall_hp_ass_sub': StatRow(stat_name='support_surface::ehp.wall_hp_ass_sub', final_value=0.0, value_type='scalar', source_count=0, status='resolved', contributors=[], schema=None),
        'support_surface::ehp.workshop_enhancement_level': StatRow(stat_name='support_surface::ehp.workshop_enhancement_level', final_value=50.0, value_type='scalar', source_count=0, status='resolved', contributors=[], schema=None),
        'support_surface::ehp.wall_module_primary_effect': StatRow(stat_name='support_surface::ehp.wall_module_primary_effect', final_value=2.0, value_type='multiplier', source_count=0, status='resolved', contributors=[], schema=None),
        'support_surface::ehp.wall_module_assist_effect': StatRow(stat_name='support_surface::ehp.wall_module_assist_effect', final_value=0.0, value_type='multiplier', source_count=0, status='resolved', contributors=[], schema=None),
        'support_surface::ehp.wall_fortification_level': StatRow(stat_name='support_surface::ehp.wall_fortification_level', final_value=3.0, value_type='scalar', source_count=0, status='resolved', contributors=[], schema=None),
    }

    derived.publish_derived_composites(rows)

    pre_fort = rows['derived::wall.hp_pre_fort']
    assert pre_fort.final_value == pytest.approx((100.0 + 1.0 + 10.0) * 1.5 * 2.0)
    assert pre_fort.value_type == 'hp'


def test_publish_derived_composites_publishes_v28_dissonant_echo_multipliers() -> None:
    rows = {
        'state::labs.dissonant_echo.attack.level': StatRow(stat_name='state::labs.dissonant_echo.attack.level', final_value=20.0, value_type='level', source_count=1, status='resolved', contributors=[], schema=None),
        'state::labs.dissonant_echo.defense.level': StatRow(stat_name='state::labs.dissonant_echo.defense.level', final_value=1.0, value_type='level', source_count=1, status='resolved', contributors=[], schema=None),
        'state::labs.dissonant_echo.utility.level': StatRow(stat_name='state::labs.dissonant_echo.utility.level', final_value=0.0, value_type='level', source_count=1, status='resolved', contributors=[], schema=None),
        'state::dissonance.attack.active_boost_multiplier': StatRow(stat_name='state::dissonance.attack.active_boost_multiplier', final_value=5.0, value_type='multiplier', source_count=1, status='resolved', contributors=[], schema=None),
        'state::dissonance.attack.echo_source_bonus': StatRow(stat_name='state::dissonance.attack.echo_source_bonus', final_value=8.0, value_type='scalar', source_count=1, status='resolved', contributors=[], schema=None),
    }

    derived.publish_derived_composites(rows)

    assert rows['derived::dissonance.attack.echo_multiplier'].final_value == pytest.approx(0.105)
    assert rows['derived::dissonance.defense.echo_multiplier'].final_value == pytest.approx(0.010)
    assert rows['derived::dissonance.utility.echo_multiplier'].final_value == pytest.approx(0.005)
    assert rows['derived::dissonance.attack.echo_bonus_multiplier'].final_value == pytest.approx(0.42)
    assert rows['derived::dissonance.attack.total_multiplier'].final_value == pytest.approx(5.42)
    assert rows['derived::dissonance.defense.total_multiplier'].final_value == pytest.approx(1.0)
    assert rows['derived::dissonance.attack.echo_multiplier'].value_type == 'ratio'
    assert '10.5%' in (rows['derived::dissonance.attack.echo_multiplier'].notes or '')
    assert 'active-tier PB is excluded from Echo' in (rows['derived::dissonance.attack.echo_bonus_multiplier'].notes or '')


def test_publish_derived_composites_applies_v28_utility_dissonance_to_eecon() -> None:
    base_rows = {
        'state::economy.coins_per_kill_bonus': StatRow(stat_name='state::economy.coins_per_kill_bonus', final_value=2.0, value_type='multiplier', source_count=1, status='resolved', contributors=[], schema=None),
    }
    dissonant_rows = dict(base_rows)
    dissonant_rows.update({
        'state::dissonance.utility.active_boost_multiplier': StatRow(stat_name='state::dissonance.utility.active_boost_multiplier', final_value=3.0, value_type='multiplier', source_count=1, status='resolved', contributors=[], schema=None),
        'state::dissonance.utility.echo_source_bonus': StatRow(stat_name='state::dissonance.utility.echo_source_bonus', final_value=2.0, value_type='scalar', source_count=1, status='resolved', contributors=[], schema=None),
        'state::labs.dissonant_echo.utility.level': StatRow(stat_name='state::labs.dissonant_echo.utility.level', final_value=0.0, value_type='level', source_count=1, status='resolved', contributors=[], schema=None),
    })

    derived.publish_derived_composites(base_rows)
    derived.publish_derived_composites(dissonant_rows)

    assert dissonant_rows['derived::dissonance.utility.total_multiplier'].final_value == pytest.approx(3.0)
    assert dissonant_rows['derived::eecon.utility_dissonance_factor'].final_value == pytest.approx(3.0)
    assert dissonant_rows['derived::eecon'].final_value == pytest.approx(base_rows['derived::eecon'].final_value * 3.0)


def test_publish_derived_composites_uses_resolved_bhd_freeup_surfaces_for_eecon() -> None:
    rows = {
        'state::economy.coins_per_kill_bonus': StatRow(stat_name='state::economy.coins_per_kill_bonus', final_value=1.0, value_type='multiplier', source_count=1, status='resolved', contributors=[], schema=None),
        'state::module.black_hole_digestor.extra_coin_kill_bonus_per_free_upgrade_pct': StatRow(stat_name='state::module.black_hole_digestor.extra_coin_kill_bonus_per_free_upgrade_pct', final_value=1.0, value_type='pct', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.free_attack_upgrade_chance_pct': StatRow(stat_name='state::tower.free_attack_upgrade_chance_pct', final_value=100.0, value_type='pct', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.free_defense_upgrade_chance_pct': StatRow(stat_name='state::tower.free_defense_upgrade_chance_pct', final_value=100.0, value_type='pct', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.free_utility_upgrade_chance_pct': StatRow(stat_name='state::tower.free_utility_upgrade_chance_pct', final_value=100.0, value_type='pct', source_count=1, status='resolved', contributors=[], schema=None),
        'state::cards.wave_skip.chance_pct': StatRow(stat_name='state::cards.wave_skip.chance_pct', final_value=19.0, value_type='pct', source_count=1, status='resolved', contributors=[], schema=None),
    }

    derived.publish_derived_composites(rows)

    wave_skip_freeup_coeff = sum(derived._epc_card_ws(skip, True, 0.19, False, 0.0) * (skip + 1) for skip in range(0, 11))
    assert rows['derived::eecon.freeup_factor'].final_value == pytest.approx(1.0 + wave_skip_freeup_coeff * 3.0 * 0.01)
    assert rows['derived::eecon'].final_value > 1000.0


def test_publish_derived_composites_publishes_ep_all_coin_display_surface() -> None:
    rows = {
        'state::economy.coins_per_kill_bonus': StatRow(stat_name='state::economy.coins_per_kill_bonus', final_value=47.0, value_type='multiplier', source_count=1, status='resolved', contributors=[], schema=None),
        'state::economy.coin_bonus_multiplier': StatRow(stat_name='state::economy.coin_bonus_multiplier', final_value=2.5, value_type='multiplier', source_count=1, status='resolved', contributors=[], schema=None),
        'state::economy.coins_multiplier': StatRow(stat_name='state::economy.coins_multiplier', final_value=2.0, value_type='multiplier', source_count=1, status='resolved', contributors=[], schema=None),
        'state::meta.cosmetic_bonus.theme_song_coin_multiplier': StatRow(stat_name='state::meta.cosmetic_bonus.theme_song_coin_multiplier', final_value=1.5, value_type='multiplier', source_count=1, status='resolved', contributors=[], schema=None),
        'state::meta.account_context.coin_multiplier_display': StatRow(stat_name='state::meta.account_context.coin_multiplier_display', final_value=9.0, value_type='multiplier', source_count=1, status='resolved', contributors=[], schema=None),
    }

    derived.publish_derived_composites(rows)

    assert rows['derived::eecon.all_coin_bonus_core_factor'].final_value == pytest.approx(67.5)
    assert rows['state::economy.all_coin_bonus_multiplier'].final_value == pytest.approx(3172.5)


def test_publish_derived_composites_applies_v28_attack_dissonance_restrictions() -> None:
    rows = {
        'state::tower.damage': StatRow(stat_name='state::tower.damage', final_value=100.0, value_type='damage', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.attack_speed': StatRow(stat_name='state::tower.attack_speed', final_value=10.0, value_type='rate', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.damage_per_meter_multiplier': StatRow(stat_name='state::tower.damage_per_meter_multiplier', final_value=5.0, value_type='multiplier', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.range_m': StatRow(stat_name='state::tower.range_m', final_value=100.0, value_type='distance', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.crit_chance_pct': StatRow(stat_name='state::tower.crit_chance_pct', final_value=100.0, value_type='pct', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.crit_multiplier': StatRow(stat_name='state::tower.crit_multiplier', final_value=10.0, value_type='multiplier', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.supercrit_chance_pct': StatRow(stat_name='state::tower.supercrit_chance_pct', final_value=100.0, value_type='pct', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.supercrit_multiplier': StatRow(stat_name='state::tower.supercrit_multiplier', final_value=10.0, value_type='multiplier', source_count=1, status='resolved', contributors=[], schema=None),
        'support_surface::amp_strike.damage_multiplier': StatRow(stat_name='support_surface::amp_strike.damage_multiplier', final_value=3.0, value_type='multiplier', source_count=1, status='resolved', contributors=[], schema=None),
        'support_surface::dissonance.attack_run_active': StatRow(stat_name='support_surface::dissonance.attack_run_active', final_value=True, value_type='bool', source_count=1, status='resolved', contributors=[], schema=None),
        'state::dissonance.attack.active_boost_multiplier': StatRow(stat_name='state::dissonance.attack.active_boost_multiplier', final_value=5.0, value_type='multiplier', source_count=1, status='resolved', contributors=[], schema=None),
    }

    derived.publish_derived_composites(rows)

    assert rows['derived::edamage.attack_dissonance_restricted'].final_value == pytest.approx(1.0)
    assert rows['derived::edamage.base_damage_stack'].final_value == pytest.approx(3.0)
    assert rows['derived::edamage.bullet_crit_factor'].final_value == pytest.approx(1.0)
    assert rows['derived::edamage.multishot_factor'].final_value == pytest.approx(1.0)
    assert rows['derived::edamage.bounce_factor'].final_value == pytest.approx(1.0)
    assert rows['derived::edamage.rapidfire_factor'].final_value == pytest.approx(1.0)
    assert rows['derived::edamage.range_dpm_factor'].final_value == pytest.approx(1.0)
    assert rows['derived::edamage.rend_factor'].final_value == pytest.approx(1.0)


def test_publish_derived_composites_publishes_cl_only_boss_applicable_damage_lane() -> None:
    rows = {
        'state::tower.damage': StatRow(stat_name='state::tower.damage', final_value=100.0, value_type='damage', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.attack_speed': StatRow(stat_name='state::tower.attack_speed', final_value=10.0, value_type='rate', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.damage_per_meter_multiplier': StatRow(stat_name='state::tower.damage_per_meter_multiplier', final_value=1.0, value_type='multiplier', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.range_m': StatRow(stat_name='state::tower.range_m', final_value=30.0, value_type='distance', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.crit_chance_pct': StatRow(stat_name='state::tower.crit_chance_pct', final_value=0.0, value_type='pct', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.crit_multiplier': StatRow(stat_name='state::tower.crit_multiplier', final_value=1.0, value_type='multiplier', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.supercrit_chance_pct': StatRow(stat_name='state::tower.supercrit_chance_pct', final_value=0.0, value_type='pct', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.supercrit_multiplier': StatRow(stat_name='state::tower.supercrit_multiplier', final_value=1.0, value_type='multiplier', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.multishot_chance_pct': StatRow(stat_name='state::tower.multishot_chance_pct', final_value=0.0, value_type='pct', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.multishot_targets': StatRow(stat_name='state::tower.multishot_targets', final_value=0.0, value_type='scalar', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.bounce_shot_chance_pct': StatRow(stat_name='state::tower.bounce_shot_chance_pct', final_value=0.0, value_type='pct', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.bounce_shot_targets': StatRow(stat_name='state::tower.bounce_shot_targets', final_value=0.0, value_type='scalar', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.rapid_fire_chance_pct': StatRow(stat_name='state::tower.rapid_fire_chance_pct', final_value=0.0, value_type='pct', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.rapid_fire_duration_seconds': StatRow(stat_name='state::tower.rapid_fire_duration_seconds', final_value=0.0, value_type='seconds', source_count=1, status='resolved', contributors=[], schema=None),
        'state::uw.chain_lightning.damage_multiplier': StatRow(stat_name='state::uw.chain_lightning.damage_multiplier', final_value=2.0, value_type='multiplier', source_count=1, status='resolved', contributors=[], schema=None),
        'state::uw.chain_lightning.quantity': StatRow(stat_name='state::uw.chain_lightning.quantity', final_value=3.0, value_type='scalar', source_count=1, status='resolved', contributors=[], schema=None),
        'state::uw.chain_lightning.chance_pct': StatRow(stat_name='state::uw.chain_lightning.chance_pct', final_value=100.0, value_type='pct', source_count=1, status='resolved', contributors=[], schema=None),
    }

    derived.publish_derived_composites(rows)

    assert rows['derived::edamage.uw.chain_lightning_dps'].final_value > 0.0
    assert rows['derived::edamage.boss_applicable_dps_cl_only'].final_value == pytest.approx(
        rows['derived::edamage.uw.chain_lightning_dps'].final_value
    )


def test_publish_derived_composites_falls_back_to_final_wall_hp_divided_by_fortification() -> None:
    rows = {
        'state::tower.hp': StatRow(stat_name='state::tower.hp', final_value=100.0, value_type='hp', source_count=1, status='resolved', contributors=[], schema=None),
        'state::wall.hp': StatRow(stat_name='state::wall.hp', final_value=520.0, value_type='hp', source_count=1, status='resolved', contributors=[], schema=None),
        'state::wall.fortification_multiplier': StatRow(stat_name='state::wall.fortification_multiplier', final_value=10.4, value_type='multiplier', source_count=1, status='resolved', contributors=[], schema=None),
    }

    derived.publish_derived_composites(rows)

    pre_fort = rows['derived::wall.hp_pre_fort']
    assert pre_fort.final_value == pytest.approx(50.0)
    assert any(c['stat_name'] == 'state::wall.fortification_multiplier' for c in pre_fort.contributors)


def test_publish_derived_composites_derives_health_dwhp_factor_from_tower_hp_contributor() -> None:
    rows = {
        'state::tower.hp': StatRow(
            stat_name='state::tower.hp',
            final_value=1000.0,
            value_type='hp',
            source_count=1,
            status='resolved',
            contributors=[{'contributor_id': 'lab.death_wave_health.account_state', 'value': 12.5}],
            schema=None,
        ),
    }

    derived.publish_derived_composites(rows)

    assert rows['derived::ehp.health_dwhp_factor'].final_value == pytest.approx(12.5)


def test_publish_derived_composites_publishes_primordial_black_hole_damage_reduction_factor() -> None:
    rows = {
        'state::tower.hp': StatRow(stat_name='state::tower.hp', final_value=100.0, value_type='hp', source_count=1, status='resolved', contributors=[], schema=None),
        'state::module.primordial_collapse.bh_damage_reduction_pct': StatRow(stat_name='state::module.primordial_collapse.bh_damage_reduction_pct', final_value=80.0, value_type='pct', source_count=1, status='resolved', contributors=[], schema=None),
        'support_surface::ehp.black_hole_duration_seconds': StatRow(stat_name='support_surface::ehp.black_hole_duration_seconds', final_value=20.0, value_type='seconds', source_count=1, status='resolved', contributors=[], schema=None),
        'support_surface::ehp.black_hole_cooldown_seconds': StatRow(stat_name='support_surface::ehp.black_hole_cooldown_seconds', final_value=50.0, value_type='seconds', source_count=1, status='resolved', contributors=[], schema=None),
    }

    derived.publish_derived_composites(rows)

    assert rows['derived::ehp.primordial_black_hole_uptime'].final_value == pytest.approx(20.0 / 70.0)
    assert rows['derived::ehp.primordial_black_hole_damage_reduction_factor'].final_value == pytest.approx(1.2962962962962963)


def test_publish_derived_composites_consumes_canonical_chain_thunder_surface() -> None:
    rows = {
        'state::tower.hp': StatRow(stat_name='state::tower.hp', final_value=100.0, value_type='hp', source_count=1, status='resolved', contributors=[], schema=None),
        'state::uw.chain_lightning.max_enemy_damage_reduction_pct': StatRow(stat_name='state::uw.chain_lightning.max_enemy_damage_reduction_pct', final_value=36.0, value_type='pct', source_count=1, status='resolved', contributors=[], schema=None),
    }

    derived.publish_derived_composites(rows)

    assert rows['derived::ehp.chain_thunder_reduction_pct'].final_value == pytest.approx(36.0)
    assert rows['derived::ehp.chain_thunder_factor'].final_value == pytest.approx(1.5625)
    contributor = rows['derived::ehp.chain_thunder_factor'].contributors[0]
    assert contributor['stat_name'] == 'state::uw.chain_lightning.max_enemy_damage_reduction_pct'


def test_publish_derived_composites_publishes_berserker_projection_helper_factor() -> None:
    rows = {
        'state::tower.damage': StatRow(stat_name='state::tower.damage', final_value=100.0, value_type='damage', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.attack_speed': StatRow(stat_name='state::tower.attack_speed', final_value=1.0, value_type='rate', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.damage_per_meter_multiplier': StatRow(stat_name='state::tower.damage_per_meter_multiplier', final_value=1.0, value_type='multiplier', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.range_m': StatRow(stat_name='state::tower.range_m', final_value=1.0, value_type='distance', source_count=1, status='resolved', contributors=[], schema=None),
        'state::cards.berserker.assumed_bonus_multiplier': StatRow(stat_name='state::cards.berserker.assumed_bonus_multiplier', final_value=8.0, value_type='multiplier', source_count=1, status='resolved', contributors=[], schema=None),
    }

    derived.publish_derived_composites(rows)

    assert rows['derived::edamage.berserker_bonus_multiplier'].final_value == pytest.approx(8.0)
    assert rows['derived::edamage.berserker_factor'].final_value == pytest.approx(9.0)


def test_publish_derived_composites_applies_damage_mastery_effect_to_edamage_base_stack() -> None:
    rows = {
        'state::tower.damage': StatRow(stat_name='state::tower.damage', final_value=100.0, value_type='damage', source_count=1, status='resolved', contributors=[], schema=None),
        'state::cards.damage.mastery_effect': StatRow(stat_name='state::cards.damage.mastery_effect', final_value=2.6, value_type='multiplier', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.damage_per_meter_multiplier': StatRow(stat_name='state::tower.damage_per_meter_multiplier', final_value=1.0, value_type='multiplier', source_count=1, status='resolved', contributors=[], schema=None),
    }

    derived.publish_derived_composites(rows)

    assert rows['derived::edamage.base_damage_stack'].final_value == pytest.approx(260.0)


def test_publish_derived_composites_uses_dpm_bonus_and_default_kill_at_range_for_range_dpm() -> None:
    rows = {
        'state::tower.damage': StatRow(stat_name='state::tower.damage', final_value=100.0, value_type='damage', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.damage_per_meter_multiplier': StatRow(stat_name='state::tower.damage_per_meter_multiplier', final_value=1.1355112, value_type='multiplier', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.range_m': StatRow(stat_name='state::tower.range_m', final_value=127.9223999157052, value_type='m', source_count=1, status='resolved', contributors=[], schema=None),
    }

    derived.publish_derived_composites(rows)

    expected = 1.0 + 127.9223999157052 * 0.1355112 * 0.25
    assert rows['derived::edamage.range_dpm_factor'].final_value == pytest.approx(expected)


def test_publish_derived_composites_applies_project_funding_to_edamage_objective() -> None:
    rows = {
        'state::tower.damage': StatRow(stat_name='state::tower.damage', final_value=100.0, value_type='damage', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.attack_speed': StatRow(stat_name='state::tower.attack_speed', final_value=1.0, value_type='rate', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.damage_per_meter_multiplier': StatRow(stat_name='state::tower.damage_per_meter_multiplier', final_value=1.0, value_type='multiplier', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.range_m': StatRow(stat_name='state::tower.range_m', final_value=1.0, value_type='distance', source_count=1, status='resolved', contributors=[], schema=None),
        'state::module.project_funding.cash_digit_multiplier_pct': StatRow(stat_name='state::module.project_funding.cash_digit_multiplier_pct', final_value=100.0, value_type='pct', source_count=1, status='resolved', contributors=[], schema=None),
        'support_surface::module.project_funding.current_cash': StatRow(stat_name='support_surface::module.project_funding.current_cash', final_value=50_000_000_000.0, value_type='scalar', source_count=1, status='resolved', contributors=[], schema=None),
    }

    derived.publish_derived_composites(rows)

    expected = 1.0 + math.log10(50_000_000_000.0)
    assert rows['derived::edamage.project_funding_factor'].final_value == pytest.approx(expected)
    assert rows['derived::edamage.base_damage_stack'].final_value == pytest.approx(100.0)

    rows_without_project_funding = {
        'state::tower.damage': StatRow(stat_name='state::tower.damage', final_value=100.0, value_type='damage', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.attack_speed': StatRow(stat_name='state::tower.attack_speed', final_value=1.0, value_type='rate', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.damage_per_meter_multiplier': StatRow(stat_name='state::tower.damage_per_meter_multiplier', final_value=1.0, value_type='multiplier', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.range_m': StatRow(stat_name='state::tower.range_m', final_value=1.0, value_type='distance', source_count=1, status='resolved', contributors=[], schema=None),
    }
    derived.publish_derived_composites(rows_without_project_funding)
    assert rows['derived::edamage'].final_value == pytest.approx(rows_without_project_funding['derived::edamage'].final_value * expected)


def test_publish_derived_composites_consumes_relic_support_surfaces_for_ehp_and_eecon() -> None:
    rows = {
        'state::tower.hp': StatRow(stat_name='state::tower.hp', final_value=100.0, value_type='hp', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.defense_absolute': StatRow(stat_name='state::tower.defense_absolute', final_value=10.0, value_type='scalar', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.defense_pct': StatRow(stat_name='state::tower.defense_pct', final_value=0.5, value_type='ratio', source_count=1, status='resolved', contributors=[], schema=None),
        'support_surface::ehp.health_relic_pct': StatRow(stat_name='support_surface::ehp.health_relic_pct', final_value=0.51, value_type='ratio', source_count=1, status='resolved', contributors=[], schema=None),
        'support_surface::ehp.dabs_relic_pct': StatRow(stat_name='support_surface::ehp.dabs_relic_pct', final_value=0.28, value_type='ratio', source_count=1, status='resolved', contributors=[], schema=None),
        'support_surface::ehp.def_pct_relic_pct': StatRow(stat_name='support_surface::ehp.def_pct_relic_pct', final_value=0.04, value_type='ratio', source_count=1, status='resolved', contributors=[], schema=None),
        'support_surface::eecon.adstarter_theme_relic_factor': StatRow(stat_name='support_surface::eecon.adstarter_theme_relic_factor', final_value=1.48, value_type='multiplier', source_count=1, status='resolved', contributors=[], schema=None),
    }

    derived.publish_derived_composites(rows)

    assert rows['derived::ehp.health_relic_factor'].final_value == pytest.approx(1.51)
    assert rows['derived::ehp.dabs_relic_factor'].final_value == pytest.approx(1.28)
    assert rows['derived::ehp.def_pct_relic_term'].final_value == pytest.approx(0.04)
    assert rows['derived::eecon.base_meta_factor'].final_value == pytest.approx(1.48)


def test_publish_derived_composites_fails_closed_when_eecon_coin_kill_source_is_missing() -> None:
    rows = {
        'support_surface::eecon.adstarter_theme_relic_factor': StatRow(stat_name='support_surface::eecon.adstarter_theme_relic_factor', final_value=1.48, value_type='multiplier', source_count=1, status='resolved', contributors=[], schema=None),
    }

    derived.publish_derived_composites(rows)

    assert rows['derived::eecon.base_meta_factor'].final_value == pytest.approx(1.48)
    assert rows['derived::eecon'].final_value is None
    assert rows['derived::eecon'].status == 'mapped_not_resolved'
    assert rows['derived::eecon.base_coin_income'].final_value is None
    assert 'coin-kill' in (rows['derived::eecon'].notes or '')


def test_publish_derived_composites_fails_closed_when_eecon_coin_kill_source_is_null() -> None:
    rows = {
        'state::economy.coins_per_kill_bonus': StatRow(stat_name='state::economy.coins_per_kill_bonus', final_value=None, value_type='multiplier', source_count=1, status='mapped_not_resolved', contributors=[], schema=None),
    }

    derived.publish_derived_composites(rows)

    assert rows['derived::eecon'].final_value is None
    assert rows['derived::eecon'].status == 'mapped_not_resolved'


def test_publish_derived_composites_publishes_eecon_when_coin_kill_source_is_resolved() -> None:
    rows = {
        'state::economy.coins_per_kill_bonus': StatRow(stat_name='state::economy.coins_per_kill_bonus', final_value=2.49, value_type='multiplier', source_count=1, status='resolved', contributors=[], schema=None),
    }

    derived.publish_derived_composites(rows)

    assert rows['derived::eecon'].final_value is not None
    assert rows['derived::eecon'].status == 'resolved'


def test_publish_derived_composites_publishes_effective_bot_range_surfaces() -> None:
    rows = {
        'state::tower.range_m': StatRow(stat_name='state::tower.range_m', final_value=130.66, value_type='distance', source_count=1, status='resolved', contributors=[], schema=None),
        'state::bot.global.range_bonus_m': StatRow(stat_name='state::bot.global.range_bonus_m', final_value=24.0, value_type='distance', source_count=1, status='resolved', contributors=[], schema=None),
        'state::bot.golden.range_m': StatRow(stat_name='state::bot.golden.range_m', final_value=50.0, value_type='distance', source_count=1, status='resolved', contributors=[], schema=None),
        'state::bot.amplify.range_m': StatRow(stat_name='state::bot.amplify.range_m', final_value=25.0, value_type='distance', source_count=1, status='resolved', contributors=[], schema=None),
        'state::bot.flame.range_m': StatRow(stat_name='state::bot.flame.range_m', final_value=46.0, value_type='distance', source_count=1, status='resolved', contributors=[], schema=None),
        'state::bot.thunder.range_m': StatRow(stat_name='state::bot.thunder.range_m', final_value=25.0, value_type='distance', source_count=1, status='resolved', contributors=[], schema=None),
        'state::bot.bot_bot.range_m': StatRow(stat_name='state::bot.bot_bot.range_m', final_value=20.0, value_type='distance', source_count=1, status='resolved', contributors=[], schema=None),
    }

    derived.publish_derived_composites(rows)

    amplification = 1.33 * (130.66 / 69.5)
    assert rows['state::bot.golden.effective_range_m'].final_value == pytest.approx((50.0 + 24.0) * amplification)
    assert rows['state::bot.amplify.effective_range_m'].final_value == pytest.approx((25.0 + 24.0) * amplification)
    assert rows['state::bot.flame.effective_range_m'].final_value == pytest.approx((46.0 + 24.0) * amplification)
    assert rows['state::bot.thunder.effective_range_m'].final_value == pytest.approx((25.0 + 24.0) * amplification)
    assert rows['state::bot.bot_bot.effective_range_m'].final_value == pytest.approx((20.0 + 24.0) * amplification)


def test_publish_derived_composites_publishes_v28_synchronicity_unlock_surfaces() -> None:
    rows = {
        surface_id: StatRow(stat_name=surface_id, final_value=True, value_type='bool', source_count=1, status='resolved', contributors=[], schema=None)
        for surface_id in (
            'state::bot.plus.wildfire.unlocked',
            'state::bot.plus.titan_shock.unlocked',
            'state::bot.plus.bonus_cell.unlocked',
            'state::bot.plus.echoing_shot.unlocked',
            'state::bot.plus.maximum_power.unlocked',
        )
    }

    derived.publish_derived_composites(rows)

    assert rows['derived::bot.plus.unlocked_count'].final_value == pytest.approx(5.0)
    assert rows['derived::bot.plus.all_unlocked'].final_value == pytest.approx(1.0)
    assert rows['derived::bot.synchronicity.base_slots_unlocked'].final_value == pytest.approx(2.0)


def test_publish_derived_composites_consumes_ultimate_crit_card_for_uw_damage_helpers() -> None:
    rows = {
        'state::tower.damage': StatRow(stat_name='state::tower.damage', final_value=100.0, value_type='damage', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.attack_speed': StatRow(stat_name='state::tower.attack_speed', final_value=1.0, value_type='rate', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.damage_per_meter_multiplier': StatRow(stat_name='state::tower.damage_per_meter_multiplier', final_value=1.0, value_type='multiplier', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.range_m': StatRow(stat_name='state::tower.range_m', final_value=1.0, value_type='distance', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.crit_chance_pct': StatRow(stat_name='state::tower.crit_chance_pct', final_value=0.0, value_type='pct', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.crit_multiplier': StatRow(stat_name='state::tower.crit_multiplier', final_value=16.2, value_type='multiplier', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.supercrit_chance_pct': StatRow(stat_name='state::tower.supercrit_chance_pct', final_value=0.0, value_type='pct', source_count=1, status='resolved', contributors=[], schema=None),
        'state::tower.supercrit_multiplier': StatRow(stat_name='state::tower.supercrit_multiplier', final_value=1.2, value_type='multiplier', source_count=1, status='resolved', contributors=[], schema=None),
        'state::cards.ultimate_crit.chance_pct': StatRow(stat_name='state::cards.ultimate_crit.chance_pct', final_value=3.0, value_type='pct', source_count=1, status='resolved', contributors=[], schema=None),
        'state::uw.death_wave.active': StatRow(stat_name='state::uw.death_wave.active', final_value=True, value_type='bool', source_count=1, status='resolved', contributors=[], schema=None),
        'support_surface::uw.death_wave.final_damage': StatRow(stat_name='support_surface::uw.death_wave.final_damage', final_value=10.0, value_type='scalar', source_count=1, status='resolved', contributors=[], schema=None),
        'support_surface::uw.death_wave.final_quantity': StatRow(stat_name='support_surface::uw.death_wave.final_quantity', final_value=1.0, value_type='scalar', source_count=1, status='resolved', contributors=[], schema=None),
        'support_surface::uw.death_wave.final_cooldown_seconds': StatRow(stat_name='support_surface::uw.death_wave.final_cooldown_seconds', final_value=1.0, value_type='seconds', source_count=1, status='resolved', contributors=[], schema=None),
        'support_surface::uw.death_wave.damage_amp': StatRow(stat_name='support_surface::uw.death_wave.damage_amp', final_value=0.0, value_type='pct', source_count=1, status='resolved', contributors=[], schema=None),
    }

    derived.publish_derived_composites(rows)

    assert rows['derived::edamage.uw_crit_card_factor'].final_value == pytest.approx(1.456)
    assert rows['derived::edamage.uw_total_damage'].final_value == pytest.approx(72.8)
