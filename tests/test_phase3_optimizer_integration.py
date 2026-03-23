import json
from pathlib import Path

import yaml

from models.statbook import StatRow
from engine.query_surface_publication import publish_phase3_query_surfaces
from optimizer.scorer import compute_optimizer_scores, MissingGovernedSurfaceError

ROOT = Path(__file__).resolve().parents[1]


def row(name, value, value_type="scalar"):
    return StatRow(stat_name=name, final_value=value, value_type=value_type, source_count=1, status="resolved", contributors=[], schema={})


def _fixture_rows():
    return {
        'support_surface::ehp.health_factor': row('support_surface::ehp.health_factor', 100.0),
        'support_surface::ehp.armor_factor': row('support_surface::ehp.armor_factor', 1.25),
        'support_surface::ehp.wall_health_factor': row('support_surface::ehp.wall_health_factor', 100.0),
        'support_surface::ehp.max_recovery_factor': row('support_surface::ehp.max_recovery_factor', 1.8),
        'support_surface::ehp.wall_active': row('support_surface::ehp.wall_active', True, 'bool'),
        'support_surface::ehp.max_recovery_active': row('support_surface::ehp.max_recovery_active', True, 'bool'),
        'support_surface::ehp.dabs_factor': row('support_surface::ehp.dabs_factor', 10.0),
        'support_surface::ehp.def_pct': row('support_surface::ehp.def_pct', 0.20),
        'mechanic_param::uw.chrono_field.duration_seconds': row('mechanic_param::uw.chrono_field.duration_seconds', 10.0),
        'runtime_mechanic_param::uw.chrono_field.duration_seconds': row('runtime_mechanic_param::uw.chrono_field.duration_seconds', 0.0),
        'mechanic_param::uw.chrono_field.cooldown_seconds': row('mechanic_param::uw.chrono_field.cooldown_seconds', 20.0),
        'mechanic_param::uw.chrono_field.damage_reduction_pct': row('mechanic_param::uw.chrono_field.damage_reduction_pct', 30.0),
        'runtime_mechanic_param::uw.chain_thunder.reduction_pct': row('runtime_mechanic_param::uw.chain_thunder.reduction_pct', 15.0),
        'mechanic_param::perk.tradeoff_defense_factor': row('mechanic_param::perk.tradeoff_defense_factor', 1.1),
        'support_surface::edamage.damage_factor': row('support_surface::edamage.damage_factor', 120.0),
        'support_surface::edamage.attack_speed_factor': row('support_surface::edamage.attack_speed_factor', 3.5),
        'support_surface::edamage.multishot_factor': row('support_surface::edamage.multishot_factor', 2.0),
        'support_surface::edamage.rapidfire_factor': row('support_surface::edamage.rapidfire_factor', 1.1),
        'support_surface::edamage.bounce_factor': row('support_surface::edamage.bounce_factor', 1.0),
        'support_surface::edamage.super_tower_factor': row('support_surface::edamage.super_tower_factor', 1.0),
        'support_surface::edamage.range_factor': row('support_surface::edamage.range_factor', 1.0),
        'support_surface::edamage.crit_factor': row('support_surface::edamage.crit_factor', 2.5),
        'support_surface::edamage.damage_per_bullet': row('support_surface::edamage.damage_per_bullet', 120.0),
        'support_surface::edamage.bullets_per_second': row('support_surface::edamage.bullets_per_second', 10.0),
        'support_surface::edamage.uw_damage_factor': row('support_surface::edamage.uw_damage_factor', 5.0),
        'support_surface::edamage.slow_factor': row('support_surface::edamage.slow_factor', 1.0),
        'support_surface::eecon.adstarter_theme_relic_factor': row('support_surface::eecon.adstarter_theme_relic_factor', 1.1),
        'support_surface::eecon.cpk_factor': row('support_surface::eecon.cpk_factor', 100.0),
        'support_surface::eecon.freeup_factor': row('support_surface::eecon.freeup_factor', 1.2),
        'runtime_mechanic_param::cards.coins.multiplier': row('runtime_mechanic_param::cards.coins.multiplier', 1.3),
        'support_surface::eecon.module_factor': row('support_surface::eecon.module_factor', 1.05),
        'support_surface::eecon.eom_factor': row('support_surface::eecon.eom_factor', 1.1),
        'support_surface::timing.combined_multiplier': row('support_surface::timing.combined_multiplier', 1.2),
        'runtime_mechanic_param::uw.spotlight.coin_bonus_multiplier': row('runtime_mechanic_param::uw.spotlight.coin_bonus_multiplier', 1.6),
        'support_surface::eecon.sl_quantity': row('support_surface::eecon.sl_quantity', 2.0),
        'support_surface::eecon.sl_angle': row('support_surface::eecon.sl_angle', 45.0),
        'support_surface::eecon.wave_factor': row('support_surface::eecon.wave_factor', 1.4),
    }


def test_optimizer_consumes_phase3_published_required_surfaces(tmp_path: Path):
    payload = {
        'inputs': [
            {'input_id': 'income.gems.per_week', 'value': 111, 'trust_label': 'externally_observed'},
            {'input_id': 'income.stones.per_week', 'value': 7, 'trust_label': 'externally_observed'},
        ]
    }
    p = tmp_path / 'manual_inputs.json'
    p.write_text(json.dumps(payload), encoding='utf-8')

    rows = _fixture_rows()
    publish_phase3_query_surfaces(rows, manual_input_path=p)
    scores = compute_optimizer_scores({'rows': rows})

    assert scores['objectives']['ehp']['score'] == float(rows['derived::ehp'].final_value)
    assert scores['objectives']['edamage']['score'] == float(rows['derived::edamage'].final_value)
    assert scores['objectives']['eecon']['score'] == float(rows['derived::eecon'].final_value)
    assert rows['derived::ehp'].final_value == rows['derived::ehp_ep'].final_value
    assert rows['derived::edamage'].final_value == rows['derived::edamage_ep'].final_value
    assert rows['derived::eecon'].final_value == rows['derived::eecon_ep'].final_value
    assert rows['derived::economy.income.gems'].final_value == 111.0
    assert rows['derived::economy.income.stones'].final_value == 7.0

    bundles = yaml.safe_load((ROOT / 'kb/global-rules/contracts/stat-query-consumer-bundles.yaml').read_text())
    bundle = next(c for c in bundles['consumers'] if c['consumer_id'] == 'optimizer_analysis')['bundles'][0]
    for sid in bundle['required_surface_ids']:
        assert sid in rows
    for sid in ['derived::ehp_ep', 'derived::edamage_ep', 'derived::eecon_ep', 'derived::economy.income.gems', 'derived::economy.income.stones']:
        assert sid in rows


def test_optimizer_fail_closed_when_required_surface_removed_after_publication(tmp_path: Path):
    payload = {'inputs': []}
    p = tmp_path / 'manual_inputs.json'
    p.write_text(json.dumps(payload), encoding='utf-8')
    rows = _fixture_rows()
    publish_phase3_query_surfaces(rows, manual_input_path=p)
    rows.pop('derived::edamage')
    try:
        compute_optimizer_scores({'rows': rows})
    except MissingGovernedSurfaceError as exc:
        assert 'derived::edamage' in str(exc)
    else:
        raise AssertionError('Expected MissingGovernedSurfaceError when derived::edamage is missing')
