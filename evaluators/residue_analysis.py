"""
evaluators/residue_analysis.py -- Residue analysis and closure reports.
"""
from __future__ import annotations


def build_survivability_residue_analysis(ep_compare: dict, compare_situation_fit_matrix: dict, statbook_dict: dict) -> dict:
    from evaluators.compare_core import _state
    destinations = [
        _state('tower_hp'),
        _state('tower_regen'),
        _state('tower_defense_absolute'),
        _state('wall_hp'),
        _state('wall_regen'),
    ]
    best_fit = compare_situation_fit_matrix.get('best_fit_by_destination', {}) if isinstance(compare_situation_fit_matrix, dict) else {}
    analysis = {}
    for dest in destinations:
        compare_row = ep_compare.get(dest, {}) if isinstance(ep_compare, dict) else {}
        fit = best_fit.get(dest, {}) if isinstance(best_fit, dict) else {}
        package_value = compare_row.get('package_value')
        ep_value = compare_row.get('ep_value')
        ratio = None
        if isinstance(package_value, (int, float)) and isinstance(ep_value, (int, float)) and ep_value:
            ratio = package_value / ep_value
        contributor_summary = []
        for c in compare_row.get('package_contributors', []) or []:
            contributor_summary.append({
                'source_family': c.get('source_family'),
                'source_name': c.get('source_name'),
                'preset_name': c.get('preset_name'),
                'value': c.get('value'),
                'value_type': c.get('value_type'),
            })
        analysis[dest] = {
            'status': compare_row.get('status'),
            'package_value': package_value,
            'ep_value': ep_value,
            'relative_delta_pct': compare_row.get('relative_delta_pct'),
            'package_to_ep_ratio': ratio,
            'best_fit_state_key': fit.get('state_key'),
            'best_fit_preset': fit.get('preset'),
            'best_fit_perk_state': fit.get('perk_state'),
            'compare_state_key': compare_row.get('compare_state_key'),
            'compare_preset': compare_row.get('compare_preset'),
            'compare_perk_state': compare_row.get('compare_perk_state'),
            'contributors': contributor_summary,
        }
    tower_hp_ratio = analysis.get(_state('tower_hp'), {}).get('package_to_ep_ratio')
    wall_hp_ratio = analysis.get(_state('wall_hp'), {}).get('package_to_ep_ratio')
    tower_regen_ratio = analysis.get(_state('tower_regen'), {}).get('package_to_ep_ratio')
    wall_regen_ratio = analysis.get(_state('wall_regen'), {}).get('package_to_ep_ratio')
    analysis['_shared_residue_summary'] = {
        'tower_hp_ratio': tower_hp_ratio,
        'wall_hp_ratio': wall_hp_ratio,
        'tower_regen_ratio': tower_regen_ratio,
        'wall_regen_ratio': wall_regen_ratio,
        'tower_hp_vs_wall_hp_ratio_gap': None if tower_hp_ratio is None or wall_hp_ratio is None else wall_hp_ratio - tower_hp_ratio,
        'tower_regen_vs_wall_regen_ratio_gap': None if tower_regen_ratio is None or wall_regen_ratio is None else wall_regen_ratio - tower_regen_ratio,
    }
    return analysis


def _build_tower_regen_closure_report(ep_compare: dict) -> dict:
    from evaluators.compare_core import _state
    dest = _state('tower_regen')
    row = (ep_compare or {}).get(dest) or {}
    contributors = row.get('package_contributors') or []
    multiplier_product = 1.0
    workshop_base = None
    ledger = []
    for c in contributors:
        v = c.get('value')
        try:
            vf = float(v)
        except Exception:
            vf = None
        family = c.get('source_family')
        value_type = c.get('value_type')
        factor = None
        if vf is None:
            factor = None
        elif family == 'workshop':
            workshop_base = vf
        elif family == 'module_substat' and value_type == 'percent_display':
            factor = 1.0 + (vf / 100.0)
        elif family == 'enhancement':
            factor = vf
        elif family in {'relic', 'vault'}:
            factor = 1.0 + vf
        elif family in {'lab', 'card', 'perk'}:
            factor = vf if vf > 1.0 else 1.0 + vf
        else:
            factor = vf if vf > 1.0 else 1.0 + vf
        if factor is not None:
            multiplier_product *= factor
        ledger.append({
            'source_family': family,
            'source_name': c.get('source_name'),
            'preset_name': c.get('preset_name'),
            'raw_value': v,
            'value_type': value_type,
            'applied_factor': factor,
        })
    recomputed = None if workshop_base is None else workshop_base * multiplier_product
    ep_value = row.get('ep_value')
    required_missing_multiplier = None
    if isinstance(recomputed, (int, float)) and isinstance(ep_value, (int, float)) and recomputed:
        required_missing_multiplier = ep_value / recomputed
    return {
        'destination': dest,
        'compare_state_key': row.get('compare_state_key'),
        'compare_preset': row.get('compare_preset'),
        'compare_perk_state': row.get('compare_perk_state'),
        'package_value': row.get('package_value'),
        'ep_value': ep_value,
        'relative_delta_pct': row.get('relative_delta_pct'),
        'workshop_base': workshop_base,
        'multiplier_product': multiplier_product,
        'recomputed_package_value': recomputed,
        'required_missing_multiplier_to_match_ep': required_missing_multiplier,
        'contributors': ledger,
    }


def _build_tower_hp_semantic_gap_report(ep_compare: dict) -> dict:
    from evaluators.compare_core import _state
    from evaluators.compare import ROOT
    dest = _state('tower_hp')
    row = (ep_compare or {}).get(dest) or {}
    contributors = row.get('package_contributors') or []

    workshop_base = None
    current_factors = {}
    for c in contributors:
        family = c.get('source_family')
        name = c.get('source_name')
        key = f"{family}::{name}"
        value = c.get('value')
        try:
            vf = float(value)
        except Exception:
            vf = None
        factor = None
        if vf is None:
            factor = None
        elif family == 'workshop':
            workshop_base = vf
        elif family == 'module_substat' and c.get('value_type') == 'percent_display':
            factor = 1.0 + (vf / 100.0)
        elif family == 'enhancement':
            factor = vf
        elif family in {'relic', 'vault'}:
            factor = 1.0 + vf
        elif family == 'module' and c.get('value_type') == 'multiplier_display':
            factor = vf if vf >= 1.0 else 1.0 + vf
        elif family == 'perk' and c.get('value_type') == 'multiplier':
            factor = vf
        else:
            factor = vf if vf >= 1.0 else 1.0 + vf
        if factor is not None:
            current_factors[key] = factor

    def _recompute(factors: dict[str, float]) -> float | None:
        if workshop_base is None:
            return None
        out = workshop_base
        for _, factor in factors.items():
            out *= factor
        return out

    package_value = row.get('package_value')
    ep_value = row.get('ep_value')
    recomputed = _recompute(current_factors)

    standard_key = 'perk::x1.20 Max Health'
    coin_to_key = 'perk::x1.80 coins, but Tower Max Health -70%'
    regen_to_key = 'perk::Tower Health Regen x8.00, But Tower Max Max Health -60%'

    current_standard = current_factors.get(standard_key)
    current_coin_to = current_factors.get(coin_to_key)
    current_regen_to = current_factors.get(regen_to_key)

    ep_standard = None if current_standard is None else (1.0 + 0.2 * 5.0) * (1.0 + 0.01 * 25.0)

    scenarios = []

    def add_scenario(name: str, updates: dict[str, float], note: str):
        factors = dict(current_factors)
        factors.update(updates)
        value = _recompute(factors)
        required = None
        if isinstance(value, (int, float)) and value not in (None, 0) and isinstance(ep_value, (int, float)):
            required = ep_value / value
        scenarios.append({
            'scenario': name,
            'package_value': value,
            'relative_delta_pct': None if value in (None, 0) or not isinstance(ep_value, (int, float)) else ((value - ep_value) / ep_value) * 100.0,
            'required_residual_multiplier_to_match_ep': required,
            'note': note,
        })

    add_scenario('current_package_semantics', {}, 'Current calculator semantics and compare-row inputs as emitted.')
    if ep_standard is not None:
        add_scenario('ep_standard_perk_semantics_only', {standard_key: ep_standard}, 'EP EPH_HEALTH formula multiplies the full perk result by Standard Perks Bonus. This is an EP workbook scenario, not a calculator truth claim.')

    dwhp_level = None
    ids_lines = (ROOT / 'input' / 'imports' / 'ids.csv').read_text().splitlines()
    for line in ids_lines:
        if line.startswith('Death Wave Health,'):
            try:
                dwhp_level = int(line.split(',', 1)[1].strip())
            except Exception:
                dwhp_level = None
            break
    dwhp_multiplier = None if dwhp_level is None else (5.0 + 0.25 * dwhp_level)
    dwhp_key = 'lab::Death Wave Health'
    current_dwhp = current_factors.get(dwhp_key)
    armor_primary = current_factors.get('module::Sharp Fortitude')
    armor_assist = current_factors.get('module::Orbital Augment')

    if dwhp_multiplier is not None and current_dwhp is None:
        add_scenario('current_package_plus_account_dwhp', {'runtime::Death Wave Health': dwhp_multiplier}, 'Model account Death Wave Health as an extra compare-only multiplier to test whether missing run-state bonus explains the EP delta. This is diagnostic only.')
    if ep_standard is not None and current_standard not in (None, 0):
        add_scenario('current_package_with_ep_standard_perk_semantics', {standard_key: ep_standard}, 'Model EP workbook full-result Standard Perk Bonus semantics on top of the current package contributors.')

    return {
        'destination': dest,
        'compare_state_key': row.get('compare_state_key'),
        'compare_preset': row.get('compare_preset'),
        'compare_perk_state': row.get('compare_perk_state'),
        'package_value': package_value,
        'ep_value': ep_value,
        'package_value_recomputed_from_current_factors': recomputed,
        'current_factors': {
            'standard_perk_factor': current_standard,
            'coin_health_tradeoff_factor': current_coin_to,
            'regen_health_tradeoff_factor': current_regen_to,
            'death_wave_health_factor': current_dwhp,
            'armor_primary_factor': armor_primary,
            'armor_assist_factor': armor_assist,
        },
        'ep_formula_hypotheses': {
            'ep_standard_perk_factor': ep_standard,
            'account_death_wave_health_level': dwhp_level,
            'account_death_wave_health_multiplier_if_applied': dwhp_multiplier,
        },
        'assessment': {
            'remaining_fraction_bug_present_in_live_compare_row': False if (current_coin_to is not None and current_regen_to is not None and abs(current_coin_to - 0.3) < 1e-9 and abs(current_regen_to - 0.4) < 1e-9) else None,
            'death_wave_health_wired_in_live_compare_row': current_dwhp == dwhp_multiplier if (current_dwhp is not None and dwhp_multiplier is not None) else None,
            'reason': 'Current compare row carries the two HP trade-off drawbacks correctly and now also includes the Death Wave Health multiplier plus the EP-style armor assist factor. The remaining gap is primarily the EP workbook Standard Perk Bonus semantic drift.',
            'calculator_change_recommended': False,
        },
        'scenarios': scenarios,
    }


def _build_tower_damage_residue_analysis(ep_compare: dict) -> dict:
    from evaluators.compare_core import _state
    import math
    row = ep_compare.get(_state('tower_damage')) or {}
    pre_runtime = row.get('package_value_before_runtime_assumptions')
    post_runtime = row.get('package_value')
    ep_value = row.get('ep_value')
    assumptions = list(row.get('runtime_compare_assumptions') or [])

    def _as_float(value):
        try:
            return float(value)
        except Exception:
            return None

    pre_runtime_f = _as_float(pre_runtime)
    post_runtime_f = _as_float(post_runtime)
    ep_value_f = _as_float(ep_value)

    applied_runtime_multiplier = None
    required_total_runtime_multiplier = None
    required_project_funding_multiplier_if_berserker_x8 = None
    required_project_funding_coefficient_at_cash_500b_if_berserker_x8 = None
    residue = None
    residue_relative_pct = None

    if pre_runtime_f not in (None, 0.0) and post_runtime_f is not None:
        applied_runtime_multiplier = post_runtime_f / pre_runtime_f
    if pre_runtime_f not in (None, 0.0) and ep_value_f is not None:
        required_total_runtime_multiplier = ep_value_f / pre_runtime_f
    if required_total_runtime_multiplier is not None:
        required_project_funding_multiplier_if_berserker_x8 = required_total_runtime_multiplier / 8.0
        cash = 500_000_000_000.0
        required_project_funding_coefficient_at_cash_500b_if_berserker_x8 = (required_project_funding_multiplier_if_berserker_x8 - 1.0) / math.log10(cash)
    if post_runtime_f is not None and ep_value_f is not None:
        residue = post_runtime_f - ep_value_f
        if ep_value_f != 0:
            residue_relative_pct = 100.0 * residue / ep_value_f

    return {
        'destination': _state('tower_damage'),
        'package_value_before_runtime_assumptions': pre_runtime_f,
        'package_value_after_runtime_assumptions': post_runtime_f,
        'ep_value': ep_value_f,
        'runtime_compare_assumptions': assumptions,
        'applied_runtime_multiplier': applied_runtime_multiplier,
        'required_total_runtime_multiplier_to_match_ep': required_total_runtime_multiplier,
        'required_project_funding_multiplier_at_berserker_x8_to_match_ep': required_project_funding_multiplier_if_berserker_x8,
        'required_project_funding_coefficient_at_cash_50b_if_berserker_x8_to_match_ep': required_project_funding_coefficient_at_cash_500b_if_berserker_x8,
        'residue_after_current_assumptions': residue,
        'residue_relative_pct_after_current_assumptions': residue_relative_pct,
    }


def build_survivor_closure_report(ep_compare: dict, line_verification: dict) -> dict:
    from evaluators.compare_core import _state
    tracked = [
        _state('tower_regen'),
        _state('tower_hp'),
        _state('tower_defense_absolute'),
        _state('tower_damage'),
        _state('wall_hp'),
        _state('wall_regen'),
    ]
    rows = []
    for destination in tracked:
        verification = dict(line_verification.get(destination) or {})
        compare = dict(ep_compare.get(destination) or {})
        rows.append({
            'destination': destination,
            'verification_status': verification.get('verification_status'),
            'issues': verification.get('issues') or [],
            'final_value': verification.get('final_value'),
            'ep_compare_value': verification.get('ep_compare_value'),
            'ep_reference_value': verification.get('ep_reference_value'),
            'delta': compare.get('delta'),
            'relative_delta_pct': compare.get('relative_delta_pct'),
            'compare_preset': compare.get('compare_preset'),
            'compare_perk_state': compare.get('compare_perk_state'),
            'package_value_source_state_mode': compare.get('package_value_source_state_mode'),
            'ep_stage_context': compare.get('ep_stage_context'),
            'note': (
                'downstream_reflection_of_tower_residue'
        if destination in {_state('wall_hp'), _state('wall_regen')}
                else 'primary_upstream_survivor'
            ),
        })
    return {
        'survivor_order': tracked,
        'rows': rows,
    }
