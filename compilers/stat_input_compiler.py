from __future__ import annotations

import csv
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml
import pandas as pd

from models.account_state import AccountState
from models.stat_input import StatInput

ROOT = Path(__file__).resolve().parents[1]
KB = ROOT / 'kb'
KB_CONTRACTS = KB / 'global-rules' / 'contracts'
STATE_MODE_CONTRACTS_PATH = KB_CONTRACTS / 'state-modes.yaml'
COMPILER_ROUTING_POLICY_PATH = KB_CONTRACTS / 'compiler-routing-policy.yaml'


@lru_cache(maxsize=1)
def _load_compiler_routing_policy() -> dict:
    raw = yaml.safe_load(COMPILER_ROUTING_POLICY_PATH.read_text()) or {}

    def _nested_tuple_map(section: str) -> dict:
        out = {}
        for outer_key, inner in (raw.get(section) or {}).items():
            inner = inner or {}
            for inner_key, destination in inner.items():
                out[(outer_key, inner_key)] = tuple(destination)
        return out

    return {
        'non_calculator_scope_labs': set(raw.get('non_calculator_scope_labs') or []),
        'uw_mechanic_destination_overrides': _nested_tuple_map('uw_mechanic_destination_overrides'),
        'uw_contributor_overrides': {
            (outer_key, inner_key): value
            for outer_key, inner in (raw.get('uw_contributor_overrides') or {}).items()
            for inner_key, value in (inner or {}).items()
        },
        'guardian_destination_overrides': _nested_tuple_map('guardian_destination_overrides'),
        'vault_boolean_flags': {k: tuple(v) for k, v in (raw.get('vault_boolean_flags') or {}).items()},
        'relic_alias_overrides': {k: tuple(v) for k, v in (raw.get('relic_alias_overrides') or {}).items()},
        'vault_numeric_overrides': {k: tuple(v) for k, v in (raw.get('vault_numeric_overrides') or {}).items()},
    }


def compiler_routing_policy() -> dict:
    return _load_compiler_routing_policy()

def _load_state_mode_contracts() -> dict:
    raw = yaml.safe_load(STATE_MODE_CONTRACTS_PATH.read_text()) or {}
    aliases = raw.get('state_mode_aliases') or {}
    modes = raw.get('state_modes') or {}
    normalized_modes = {}
    for mode_name, spec in modes.items():
        spec = spec or {}
        normalized_modes[mode_name] = {
            'excluded_source_families': set(spec.get('excluded_source_families') or []),
            'projection_facets_applied': list(spec.get('projection_facets_applied') or []),
            'notes': list(spec.get('notes') or []),
        }
    return {
        'aliases': aliases,
        'modes': normalized_modes,
    }


def supported_state_modes() -> tuple[str, ...]:
    return tuple(_load_state_mode_contracts()['modes'].keys())


SUPPORTED_STATE_MODES = supported_state_modes()


def normalize_state_mode(state_mode: str | None) -> str:
    contracts = _load_state_mode_contracts()
    mode = (state_mode or 'start_of_run').strip()
    mode = contracts['aliases'].get(mode, mode)
    if mode not in contracts['modes']:
        raise ValueError(f'Unsupported state_mode: {state_mode}')
    return mode


def state_mode_support(state_mode: str | None) -> dict:
    mode = normalize_state_mode(state_mode)
    spec = _load_state_mode_contracts()['modes'][mode]
    return {
        'state_mode': mode,
        'supported': True,
        'projection_facets_applied': list(spec['projection_facets_applied']),
        'projection_facets_missing': [],
        'notes': list(spec['notes']),
    }


def row_in_state_mode(row: StatInput, state_mode: str | None) -> bool:
    mode = normalize_state_mode(state_mode)
    excluded = _load_state_mode_contracts()['modes'][mode]['excluded_source_families']
    return row.source_family not in excluded

KB_TABLES = KB / 'global-rules' / 'tables'

KB_MAPPINGS_PATH = KB_CONTRACTS / 'contributor-mappings-full.yaml'
KB_CANONICAL_STATS_PATH = KB_CONTRACTS / 'canonical-stats.yaml'
KB_ALIASES_PATH = KB_CONTRACTS / 'name-aliases.yaml'
LAB_VALUES_PATH = KB / 'labs' / 'tables' / 'lab-values.csv'
WORKSHOP_VALUES_PATH = KB / 'workshop' / 'tables' / 'workshop-values.csv'
WORKSHOP_VALUES_DERIVED_PATH = KB / 'workshop' / 'derived' / 'materialized' / 'workshop-values.csv'
CARD_LADDERS_PATH = KB / 'cards' / 'tables' / 'card-base-ladders.csv'
CARD_EFFECT_REGISTRY_PATH = KB / 'cards' / 'tables' / 'card-effect-registry.csv'
MODULE_SUBSTATS_TABLE_PATH = KB / 'modules' / 'tables' / 'module-substats.csv'
MODULE_UNIQUE_EFFECTS_TABLE_PATH = KB / 'modules' / 'tables' / 'module-unique-effects.csv'
MODULE_MAIN_EFFECT_BASES_PATH = KB / 'modules' / 'tables' / 'module-main-effect-bases.csv'
MODULE_MAIN_EFFECT_STEPS_PATH = KB / 'modules' / 'sources' / 'raw' / 'effective-paths' / 'sheet-exports' / 'module-base-stat-values.csv'
RELIC_REGISTRY_PATH = KB_TABLES / 'relic-input-registry.csv'
BOT_TRACK_REGISTRY_PATH = KB / 'bots' / 'tables' / 'bot-track-registry.csv'
BOT_TRACK_VALUES_PATH = KB / 'bots' / 'tables' / 'bot-upgrade-tracks-long.csv'
BOT_LABS_SUMMARY_PATH = KB / 'bots' / 'tables' / 'bot-labs-summary.yaml'
GUARDIAN_TRACK_REGISTRY_PATH = KB / 'guardians' / 'tables' / 'guardian-track-registry.csv'
UW_TRACK_REGISTRY_PATH = KB / 'ultimate-weapons' / 'tables' / 'uw-track-registry.csv'
UW_TRACK_VALUES_PATH = KB / 'ultimate-weapons' / 'tables' / 'ultimate-weapon-track-ladders.csv'
UW_PLUS_VALUES_PATH = KB / 'ultimate-weapons' / 'tables' / 'ultimate-weapon-plus-ladders.csv'
THEME_SONG_REGISTRY_PATH = KB_TABLES / 'theme-song-input-registry.csv'
PERK_ENTITY_REGISTRY_PATH = KB / 'perks' / 'tables' / 'perk-entity-registry.csv'
PERK_EFFECT_REGISTRY_PATH = KB / 'perks' / 'tables' / 'perk-effect-registry.csv'

SCOUT_GUARDIAN_TABLE_PATH = KB / 'guardians' / 'tables' / 'wiki-verified-guardian-scout-upgrades.csv'

# ── UW lab wiki-verified value tables (from UW complete branch) ──
_UW_LAB_TABLE_REGISTRY: Dict[str, Tuple[str, str]] = {
    'Lightning Amplifier - Scatter': ('ultimate-weapons/tables/wiki-verified-lightning-amplifier-scatter.csv', 'value'),
    'Swamp Radius': ('ultimate-weapons/tables/wiki-verified-swamp-radius.csv', 'value'),
    'Swamp Stun Chance': ('ultimate-weapons/tables/wiki-verified-swamp-stun-chance.csv', 'value'),
    'Swamp Stun Time': ('ultimate-weapons/tables/wiki-verified-swamp-stun-time.csv', 'value'),
    'Missile Barrage Quantity': ('ultimate-weapons/tables/wiki-verified-missile-barrage-quantity.csv', 'value'),
    'Missile Radius': ('ultimate-weapons/tables/wiki-verified-missiles-radius.csv', 'value'),
    'Inner Mine Blast Radius': ('ultimate-weapons/tables/wiki-verified-inner-mine-blast-radius.csv', 'value'),
    'Inner Mine Rotation Speed': ('ultimate-weapons/tables/wiki-verified-inner-mine-rotation-speed.csv', 'value'),
    'Recharge Missile Barrage': ('ultimate-weapons/tables/wiki-verified-recharge-missile-barrage.csv', 'value'),
    'Inner Land Mine - Chrono Jump': ('ultimate-weapons/tables/wiki-verified-inner-land-mine-chrono-jump.csv', 'value'),
    'Swamp Rend - Additional Enemies': ('ultimate-weapons/tables/wiki-verified-swamp-rend-additional-enemies.csv', 'value'),
}

# UW lab destinations for labs not yet in LAB_APPLICATION_TARGET_TO_DESTINATION
_UW_LAB_DIRECT_DESTINATION: Dict[str, Tuple[str, str]] = {
    'Lightning Amplifier - Scatter': ('mechanic_param', 'uw.chain_lightning.scatter_multiplier'),
    'Swamp Radius': ('mechanic_param', 'uw.poison_swamp.radius_m'),
    'Swamp Stun Chance': ('mechanic_param', 'uw.poison_swamp.stun_chance_pct'),
    'Swamp Stun Time': ('mechanic_param', 'uw.poison_swamp.stun_duration_seconds'),
    'Missile Barrage Quantity': ('mechanic_param', 'uw.smart_missiles.barrage_quantity'),
    'Missile Radius': ('mechanic_param', 'uw.smart_missiles.explosion_radius_m'),
    'Inner Mine Blast Radius': ('mechanic_param', 'uw.inner_land_mines.blast_radius_m'),
    'Inner Mine Rotation Speed': ('mechanic_param', 'uw.inner_land_mines.rotation_speed'),
    'Recharge Missile Barrage': ('mechanic_param', 'uw.smart_missiles.recharge_barrage_waves'),
    'Inner Land Mine - Chrono Jump': ('mechanic_param', 'uw.inner_land_mines.chrono_jump_seconds'),
    'Swamp Rend - Additional Enemies': ('mechanic_param', 'uw.poison_swamp.rend_additional_enemies'),
    # Capability labs (binary unlock)
    'Inner Mine Stun': ('capability', 'capability.uw.inner_land_mines.stun'),
    'Missile Barrage': ('capability', 'capability.uw.smart_missiles.barrage'),
    'Swamp Rend': ('capability', 'capability.uw.poison_swamp.rend'),
    'Light Speed Shots': ('capability', 'capability.tower.light_speed_shots'),
    'Double Death Ray': ('capability', 'capability.tower.double_death_ray'),
    'Garlic Thorns': ('capability', 'capability.tower.garlic_thorns'),
    # Non-UW mechanic/environment params
    'Land Mine Damage': ('mechanic_param', 'lab.land_mine_damage_multiplier'),
    'Land Mine Decay': ('mechanic_param', 'lab.land_mine_decay_seconds'),
    'Orb Boss Hit': ('mechanic_param', 'lab.orb_boss_hit_enabled'),
    'Shockwave Size': ('mechanic_param', 'lab.shockwave_size_bonus'),
    'Orbs Speed': ('mechanic_param', 'lab.orb_speed_bonus'),
    'Super Tower Bonus': ('mechanic_param', 'lab.super_tower_bonus_multiplier'),
    'Max Rend Armor Multiplier': ('canonical_stat', 'max_rend_mult'),
    # BC/environment labs
    'Death Defy Down': ('environment_param', 'bc.death_defy_down_pct'),
    'Death Ray Resistance': ('environment_param', 'bc.death_ray_resistance_pct'),
    'Energy Shields Down': ('environment_param', 'bc.energy_shields_down_pct'),
    'Energy Shield Extra Hit': ('environment_param', 'bc.energy_shield_extra_hit'),
    'Knockback Resistance': ('environment_param', 'bc.knockback_resistance_pct'),
    'Orb Resistance': ('environment_param', 'bc.orb_resistance_pct'),
    'Plasma Cannon Resistance': ('environment_param', 'bc.plasma_cannon_resistance_pct'),
    'Thorns Resistance': ('environment_param', 'bc.thorns_resistance_pct'),
    'More Enemies': ('environment_param', 'bc.more_enemies_pct'),
    'Enemy Attack Speed': ('environment_param', 'bc.enemy_attack_speed_pct'),
    'Enemy Speed': ('environment_param', 'bc.enemy_speed_pct'),
    'Enemy Level Skip Reduction': ('environment_param', 'bc.enemy_level_skip_reduction_pp'),
    'Armored Enemies': ('environment_param', 'bc.armored_enemies_blocked_hits'),
    'Boss Attack': ('environment_param', 'enemy.boss.attack_multiplier'),
    'Boss Health': ('environment_param', 'enemy.boss.health_multiplier_lab'),
    'Ranged Enemy Attack': ('environment_param', 'enemy.ranged.attack_multiplier'),
    'Ranged Enemy Health': ('environment_param', 'enemy.ranged.health_multiplier'),
    'Ranged Enemy Range': ('environment_param', 'enemy.ranged.range_multiplier'),
    'Common Enemy Attack': ('environment_param', 'enemy.common.attack_multiplier'),
    'Common Enemy Health': ('environment_param', 'enemy.common.health_multiplier'),
    'Fast Enemy Attack': ('environment_param', 'enemy.fast.attack_multiplier'),
    'Fast Enemy Health': ('environment_param', 'enemy.fast.health_multiplier'),
    'Fast Enemy Speed': ('environment_param', 'enemy.fast.speed_multiplier'),
    'Scatter Enemy Attack': ('environment_param', 'enemy.scatter.attack_multiplier'),
    'Scatter Enemy Health': ('environment_param', 'enemy.scatter.health_multiplier'),
    'Ray Enemy Attack': ('environment_param', 'enemy.ray.attack_multiplier'),
    'Ray Enemy Health': ('environment_param', 'enemy.ray.health_multiplier'),
    'Tank Enemy Attack': ('environment_param', 'enemy.tank.attack_multiplier'),
    'Tank Enemy Health': ('environment_param', 'enemy.tank.health_multiplier'),
    'Vampire Enemy Attack': ('environment_param', 'enemy.vampire.attack_multiplier'),
    'Vampire Enemy Health': ('environment_param', 'enemy.vampire.health_multiplier'),
    'Ultimate Weapon Durations': ('environment_param', 'bc.uw_duration_reduction_seconds'),
    'Protector Damage Reduction': ('mechanic_param', 'enemy.protector.damage_reduction_pct'),
    'Protector Health': ('mechanic_param', 'enemy.protector.health_multiplier'),
    'Protector Radius': ('mechanic_param', 'enemy.protector.radius_m'),
    'Second Wind Blast': ('mechanic_param', 'lab.second_wind_blast_pct'),
    'Recharge Second Wind': ('mechanic_param', 'lab.recharge_second_wind_waves'),
    'Recharge Demon Mode': ('mechanic_param', 'lab.recharge_demon_mode_waves'),
    'Recharge Nuke': ('mechanic_param', 'lab.recharge_nuke_waves'),
    # Bot labs
    'Amp Bot - Cooldown': ('mechanic_param', 'bot.amplify.cooldown_seconds'),
    'Amp Bot - Duration': ('mechanic_param', 'bot.amplify.duration_seconds'),
    'Flame Bot - Cooldown': ('mechanic_param', 'bot.flame.cooldown_seconds'),
    'Flame Bot - Burn Stack': ('runtime_mechanic_param', 'bot.flame_bot.lab_burn_stack'),
    'Gold Bot - Cooldown': ('mechanic_param', 'bot.golden.cooldown_seconds'),
    'Gold Bot - Duration': ('mechanic_param', 'bot.golden.duration_seconds'),
    'Thunder Bot - Cooldown': ('mechanic_param', 'bot.thunder.cooldown_seconds'),
    'Thunder Bot - Linger Time': ('mechanic_param', 'bot.thunder.linger_duration_seconds'),
}

# Labs that are NOT calculator scope are loaded from governed routing policy.
_NON_CALCULATOR_SCOPE_LABS = compiler_routing_policy()['non_calculator_scope_labs']

UW_MECHANIC_DESTINATION_OVERRIDES = compiler_routing_policy()['uw_mechanic_destination_overrides']

UW_CONTRIBUTOR_OVERRIDES = compiler_routing_policy()['uw_contributor_overrides']

GUARDIAN_DESTINATION_OVERRIDES = compiler_routing_policy()['guardian_destination_overrides']

VAULT_BOOLEAN_FLAGS = compiler_routing_policy()['vault_boolean_flags']

RELIC_ALIAS_OVERRIDES = compiler_routing_policy()['relic_alias_overrides']

VAULT_NUMERIC_OVERRIDES = compiler_routing_policy()['vault_numeric_overrides']

WORKSHOP_IDS_TO_CONTRIBUTOR = {
    'Damage': 'workshop__tower__damage__flat',
    'Attack Speed': 'workshop__tower__attack_speed__flat',
    'Critical Chance': 'workshop__tower__crit_chance__pct',
    'Critical Factor': 'workshop__tower__crit_multiplier__multiplier',
    'Range': 'workshop__tower__range__m',
    'Damage / Meter': 'workshop__tower__damage_per_meter__multiplier',
    'Multishot Chance': 'workshop__tower__multishot_chance__pct',
    'Multishot Targets': 'workshop__tower__multishot_targets__count',
    'Rapid Fire Chance': 'workshop__tower__rapid_fire_chance__pct',
    'Rapid Fire Duration': 'workshop__tower__rapid_fire_duration__seconds',
    'Bounce Shot Chance': 'workshop__tower__bounce_shot_chance__pct',
    'Bounce Shot Targets': 'workshop__tower__bounce_shot_targets__count',
    'Bounce Shot Range': 'workshop__tower__bounce_shot_range__m',
    'Super Critical Chance': 'workshop__tower__supercrit_chance__pct',
    'Super Critical Mult': 'workshop__tower__supercrit_multiplier__multiplier',
    'Rend Armor Chance': 'workshop__tower__rend_armor_chance__pct',
    'Rend Armor Mult': 'workshop__tower__rend_armor_multiplier__multiplier',
    'Health': 'workshop__tower__health__flat',
    'Health Regen': 'workshop__tower__regen__flat',
    'Defense %': 'workshop__tower__defense_pct__pct',
    'Defense Absolute': 'workshop__tower__defense_absolute__flat',
    'Thorn Damage': 'workshop__tower__thorns_damage__pct',
    'Lifesteal': 'workshop__tower__lifesteal__pct',
    'Knockback Chance': 'workshop__tower__knockback_chance__pct',
    'Knockback Force': 'workshop__tower__knockback_force__flat',
    'Orb Speed': 'workshop__tower__orb_speed__rpm',
    'Orbs': 'workshop__tower__orb_count__count',
    'Shockwave Size': 'workshop__tower__shockwave_size__m',
    'Shockwave Frequency': 'workshop__tower__shockwave_interval__seconds',
    'Land Mine Chance': 'workshop__tower__land_mine_chance__pct',
    'Land Mine Damage': 'workshop__tower__land_mine_damage__flat',
    'Land Mine Radius': 'workshop__tower__land_mine_radius__m',
    'Death Defy': 'workshop__tower__death_defy_chance__pct',
    'Wall Health': 'workshop__wall__health__flat',
    'Wall Rebuild': 'workshop__wall__rebuild__seconds',
    'Cash Bonus': 'workshop__tower__cash_kill_bonus__multiplier',
    'Cash / Wave': 'workshop__tower__cash_per_wave__flat',
    'Coin / Kill Bonus': 'workshop__tower__coin_kill_bonus__multiplier',
    'Coin / Wave': 'workshop__tower__coins_per_wave__flat',
    'Free Attack Upgrade': 'workshop__tower__free_attack_upgrade__pct',
    'Free Defense Upgrade': 'workshop__tower__free_defense_upgrade__pct',
    'Free Utility Upgrade': 'workshop__tower__free_utility_upgrade__pct',
    'Interest / Wave': 'workshop__tower__interest_per_wave__pct',
    'Recovery Amount': 'workshop__tower__recovery_amount__pct',
    'Max Amount': 'workshop__tower__max_recovery__multiplier',
    'Package Chance': 'workshop__tower__package_chance__pct',
    'Enemy Attack Level Skip': 'workshop__tower__enemy_attack_level_skip__pct',
    'Enemy Health Level Skip': 'workshop__tower__enemy_health_level_skip__pct',
}

LAB_IDS_TO_CONTRIBUTOR = {
    # Tower-facing labs should route through the KB lab application registry, not hardcoded guesses.
    # Keep only wall-specific extras here until they are represented in the registry.
    'Critical Factor': 'lab__tower__crit_factor__pct',
    'Coins / Kill Bonus': 'lab__tower__coins_kill_bonus__pct',
    'Wall Health': 'lab__wall__health__pct',
    'Wall Thorns': 'lab__wall__thorns_damage__pct',
    'Wall Invincibility': 'lab__wall__invincibility_duration__seconds',
    'Wall Regen': 'lab__wall__regen__flat',
    'Wall Fortification': 'lab__wall__fortification__multiplier',
}

DIRECT_WORKSHOP_TABLE_COLUMNS = {
    'Damage': 'Damage',
    'Health': 'Health',
    'Health Regen': 'HPregen',
    'Defense Absolute': 'DefAbs',
    'Damage / Meter': 'Damage / Meter',
    'Lifesteal': 'Lifesteal',
}

WORKSHOP_FORMULA_VALUES = {
    'Attack Speed': lambda level: 1.0 + 0.05 * level,
    'Defense %': lambda level: 0.7 * level,
    'Critical Chance': lambda level: 1.0 + float(level),
    'Critical Factor': lambda level: 1.2 + 0.1 * level,
    'Cash Bonus': lambda level: 1.0 + 0.01 * level,
    'Coin / Kill Bonus': lambda level: 1.0 + 0.01 * level,
    'Enemy Attack Level Skip': lambda level: 0.05 + 0.05 * level,
    'Enemy Health Level Skip': lambda level: 0.05 + 0.05 * level,
    'Package Chance': lambda level: 6.0 + 0.4 * level,
    'Range': lambda level: 26.5 + 0.5 * level,
    'Thorn Damage': lambda level: float(level),
    'Wall Health': lambda level: 0.2 + 0.001 * level,
    'Wall Rebuild': lambda level: max(0.0, 600.0 - 2.0 * level),
    'Free Attack Upgrade': lambda level: 0.5 * level,
    'Free Defense Upgrade': lambda level: 0.5 * level,
    'Free Utility Upgrade': lambda level: 0.5 * level,
    'Recovery Amount': lambda level: 14.0 + 0.4 * level,
    'Max Amount': lambda level: 1.0 + 0.031 * level,
    'Max Recovery': lambda level: 1.0 + 0.031 * level,
    'Interest / Wave': lambda level: 0.25 * level,
    'Wall Fortification': lambda level: 1.0 + ((20.0 * level) / 100.0),
    'Multishot Chance': lambda level: 0.5 * level,
    'Multishot Targets': lambda level: 2.0 + level,
    'Rapid Fire Chance': lambda level: 0.4 * level,
    'Rapid Fire Duration': lambda level: 0.6 + 0.05 * level,
    'Bounce Shot Chance': lambda level: 0.8 * level,
    'Bounce Shot Targets': lambda level: 1.0 + level,
    'Bounce Shot Range': lambda level: 2.0 + 0.1 * level,
    'Super Critical Chance': lambda level: 0.2 * level,
    'Super Critical Mult': lambda level: 1.2 + 0.1 * level,
    'Rend Armor Chance': lambda level: 0.375 * level,
    'Rend Armor Mult': lambda level: 0.0035 * (level + 1),
    'Knockback Chance': lambda level: 1.0 * level,
    'Knockback Force': lambda level: 0.4 + 0.142 * level,
    'Orb Speed': lambda level: 0.4 + 0.15 * level,
    'Orbs': lambda level: max(0.0, float(level) - 1.0),
    'Shockwave Size': lambda level: 0.6 + 0.05 * level,
    'Shockwave Frequency': lambda level: max(7.0, 20.0 - 0.15 * level),
    'Land Mine Chance': lambda level: 0.6 * level,
    'Land Mine Damage': lambda level: 1.0 + 0.1 * level,
    'Land Mine Radius': lambda level: 0.03 * level,
    'Death Defy': lambda level: 0.4 * level,
    'Cash / Wave': lambda level: 4.0 * level,
    'Coin / Wave': lambda level: 4.0 * level,
}




LAB_FORMULA_VALUES = {
    'Critical Factor': lambda level: 1.0 + 0.03 * level,
    'Coins / Kill Bonus': lambda level: 1.0 + 0.02 * level,
    'Cash Bonus': lambda level: 1.0 + 0.02 * level,
    'Defense Absolute': lambda level: 1.0 + 0.03 * level,
    'Damage / Meter': lambda level: 1.0 + 0.02 * level,
    'Wall Rebuild': lambda level: -10.0 * level,
    'Max Rend Armor Multiplier': lambda level: 0.25 * level,
}

CARD_TARGET_SURFACE_TO_CANONICAL = {
    'tower.damage_multiplier': 'tower_damage',
    'tower.attack_speed_multiplier': 'tower_attack_speed',
    'tower.health_multiplier': 'tower_hp',
    'tower.health_regen_multiplier': 'tower_regen',
    'tower.defense_pct_bonus': 'tower_defense_pct',
    'economy.coin_multiplier': 'coins_multiplier',
    'economy.cash_multiplier': 'cash_kill_multiplier',
    'free_upgrades.runtime_bonus': 'free_upgrade_multiplier',
}

CARD_TARGET_SURFACE_TO_DESTINATION = {
    'tower.damage_multiplier': ('canonical_stat', 'tower_damage'),
    'tower.attack_speed_multiplier': ('canonical_stat', 'tower_attack_speed'),
    'tower.health_multiplier': ('canonical_stat', 'tower_hp'),
    'tower.health_regen_multiplier': ('canonical_stat', 'tower_regen'),
    'tower.defense_pct_bonus': ('canonical_stat', 'tower_defense_pct'),
    'tower.crit_chance_percent_points': ('canonical_stat', 'tower_crit_chance_pct'),
    'economy.coin_multiplier': ('canonical_stat', 'coins_multiplier'),
    'economy.cash_multiplier': ('canonical_stat', 'cash_kill_multiplier'),
    'orbs.count_bonus': ('canonical_stat', 'tower_orb_count'),
    'waves.skip_chance': ('runtime_mechanic_param', 'cards.wave_skip.chance_pct'),
    'plasma_cannon.runtime_effect': ('runtime_mechanic_param', 'cards.plasma_cannon.effect_pct'),
    'economy.critical_coin_bonus': ('runtime_mechanic_param', 'cards.critical_coin.bonus_multiplier'),
}

LAB_APPLICATION_TARGET_TO_DESTINATION = {
    ('tower', 'attack_speed_multiplier'): ('canonical_stat', 'tower_attack_speed'),
    ('tower', 'cash_bonus_multiplier'): ('canonical_stat', 'cash_kill_multiplier'),
    ('tower', 'coins_per_wave_multiplier'): ('canonical_stat', 'coins_per_wave'),
    ('tower', 'damage_multiplier'): ('canonical_stat', 'tower_damage'),
    ('tower', 'defense_percent_points'): ('canonical_stat', 'tower_defense_pct'),
    ('tower', 'health_multiplier'): ('canonical_stat', 'tower_hp'),
    ('tower', 'health_regen_multiplier'): ('canonical_stat', 'tower_regen'),
    ('tower', 'range_multiplier'): ('canonical_stat', 'tower_range_m'),
    ('tower', 'recovery_package_chance_percent_points'): ('canonical_stat', 'package_chance_pct'),
    ('tower', 'super_crit_chance_percent_points'): ('canonical_stat', 'tower_supercrit_chance_pct'),
    ('tower', 'super_crit_multiplier'): ('canonical_stat', 'tower_supercrit_multiplier'),
    ('enemy_attack_level_skip', 'chance_percent_points'): ('canonical_stat', 'enemy_attack_level_skip_pct'),
    ('enemy_health_level_skip', 'chance_percent_points'): ('canonical_stat', 'enemy_health_level_skip_pct'),
    ('wall', 'fortification_pct'): ('canonical_stat', 'wall_fortification_multiplier'),
    ('wall', 'health_multiplier'): ('canonical_stat', 'wall_hp'),
    ('wall', 'regen_percent_points'): ('canonical_stat', 'wall_regen'),
    ('ultimate_weapon_chrono_field', 'duration_seconds'): ('mechanic_param', 'uw.chrono_field.duration_seconds'),
    ('ultimate_weapon_black_hole', 'coin_bonus_multiplier'): ('runtime_mechanic_param', 'uw.black_hole.coin_bonus_multiplier'),
    ('ultimate_weapon_spotlight', 'coin_bonus_multiplier'): ('runtime_mechanic_param', 'uw.spotlight.coin_bonus_multiplier'),
    ('ultimate_weapon_death_wave', 'coin_bonus_multiplier'): ('runtime_mechanic_param', 'uw.death_wave.coin_bonus_multiplier'),
    ('ultimate_weapon_black_hole', 'damage_pct_enemy_hp_per_second'): ('mechanic_param', 'uw.black_hole.damage_pct_enemy_hp_per_second'),
    ('ultimate_weapon_chain_lightning', 'max_enemy_damage_reduction_pct'): ('mechanic_param', 'uw.chain_lightning.max_enemy_damage_reduction_pct'),
    ('ultimate_weapon_chrono_field', 'damage_reduction_pct'): ('mechanic_param', 'uw.chrono_field.damage_reduction_pct'),
    ('ultimate_weapon_chrono_field', 'range_m'): ('mechanic_param', 'uw.chrono_field.range_m'),
    ('ultimate_weapon_death_wave', 'armor_strip_count'): ('mechanic_param', 'uw.death_wave.armor_strip_count'),
    ('ultimate_weapon_death_wave', 'cells_bonus_multiplier'): ('mechanic_param', 'uw.death_wave.cells_bonus_multiplier'),
    ('ultimate_weapon_death_wave', 'damage_amplifier_multiplier_per_effect_wave'): ('mechanic_param', 'uw.death_wave.damage_amplifier_multiplier_per_effect_wave'),
    ('ultimate_weapon_golden_tower', 'duration_seconds'): ('mechanic_param', 'uw.golden_tower.duration_seconds'),
    ('ultimate_weapon_golden_tower', 'bonus_multiplier'): ('mechanic_param', 'uw.golden_tower.bonus_multiplier'),
    ('ultimate_weapon_smart_missiles', 'chain_hit_damage_multiplier'): ('mechanic_param', 'uw.smart_missiles.chain_hit_damage_multiplier'),
    ('ultimate_weapon_smart_missiles', 'despawn_time_seconds'): ('mechanic_param', 'uw.smart_missiles.despawn_time_seconds'),
    ('ultimate_weapon_smart_missiles', 'explosion_radius_m'): ('mechanic_param', 'uw.smart_missiles.explosion_radius_m'),
    ('ultimate_weapon_smart_missiles', 'barrage_quantity'): ('mechanic_param', 'uw.smart_missiles.barrage_quantity'),
    ('ultimate_weapon_smart_missiles', 'recharge_barrage_waves'): ('mechanic_param', 'uw.smart_missiles.recharge_barrage_waves'),
    ('ultimate_weapon_poison_swamp', 'radius_m'): ('mechanic_param', 'uw.poison_swamp.radius_m'),
    ('ultimate_weapon_poison_swamp', 'stun_chance_pct'): ('mechanic_param', 'uw.poison_swamp.stun_chance_pct'),
    ('ultimate_weapon_poison_swamp', 'stun_duration_seconds'): ('mechanic_param', 'uw.poison_swamp.stun_duration_seconds'),
    ('ultimate_weapon_poison_swamp', 'rend_additional_enemies'): ('mechanic_param', 'uw.poison_swamp.rend_additional_enemies'),
    ('ultimate_weapon_inner_land_mines', 'blast_radius_m'): ('mechanic_param', 'uw.inner_land_mines.blast_radius_m'),
    ('ultimate_weapon_inner_land_mines', 'rotation_speed'): ('mechanic_param', 'uw.inner_land_mines.rotation_speed'),
    ('ultimate_weapon_inner_land_mines', 'chrono_jump_seconds'): ('mechanic_param', 'uw.inner_land_mines.chrono_jump_seconds'),
    ('shock', 'chance_pct'): ('mechanic_param', 'shock.chance_pct'),
    ('shock', 'damage_multiplier'): ('mechanic_param', 'shock.damage_multiplier'),
    ('ultimate_weapon_spotlight', 'missiles_frequency_seconds'): ('mechanic_param', 'uw.spotlight.missiles_frequency_seconds'),
    ('game_runtime', 'game_speed_multiplier'): ('runtime_mechanic_param', 'game_runtime.speed_multiplier'),
    ('laboratory', 'lab_speed_multiplier'): ('meta_progression_param', 'laboratory.speed_multiplier'),
    ('waves_required', 'required_waves_delta'): ('meta_progression_param', 'milestones.waves_required_delta'),
    # R36: economy labs
    ('tower', 'cash_per_wave_multiplier'): ('canonical_stat', 'cash_per_wave'),
    ('tower', 'interest_per_wave_multiplier'): ('canonical_stat', 'interest_per_wave_pct'),
    ('tower', 'recovery_amount_percent_points'): ('canonical_stat', 'recovery_amount_pct'),
    ('tower', 'max_recovery_multiplier_bonus'): ('canonical_stat', 'max_recovery_multiplier'),
    # R34: capability/environment labs
    ('ultimate_weapon_black_hole', 'extra_black_hole'): ('capability', 'capability.uw.black_hole.extra_black_hole'),
    ('ultimate_weapon_black_hole', 'disable_ranged'): ('capability', 'capability.uw.black_hole.disable_ranged'),
    ('ultimate_weapon_chain_lightning', 'shock'): ('capability', 'capability.uw.chain_lightning.shock'),
    ('ultimate_weapon_poison_swamp', 'stun'): ('capability', 'capability.uw.poison_swamp.stun'),
    ('ultimate_weapon_smart_missiles', 'explosion'): ('capability', 'capability.uw.smart_missiles.explosion'),
    ('recovery_package', 'after_boss'): ('capability', 'capability.recovery_package.after_boss'),
    ('battle_conditions', 'reduction_generic_pct'): ('environment_param', 'bc.reduction.generic_pct'),
}

CARD_NAME_FALLBACK_DESTINATION = {
    'cash': ('canonical_stat', 'cash_kill_multiplier'),
    'health regen': ('canonical_stat', 'tower_regen'),
    'enemy balance': ('environment_param', 'bc.more_enemies_pct'),
    'plasma cannon': ('capability', 'capability.plasma_cannon.enabled'),
    'recovery package chance': ('canonical_stat', 'package_chance_pct'),
    'wave accelerator': ('runtime_mechanic_param', 'cards.wave_accelerator.spawn_rate_acceleration'),
    'second wind': ('capability', 'capability.second_wind.enabled'),
    'energy shield': ('capability', 'capability.energy_shield.enabled'),
    'land mine stun': ('runtime_mechanic_param', 'cards.land_mine_stun.miss_attack_chance_pct'),
}

MODULE_SUBSTAT_NAME_TO_DESTINATION = {
    'bounce shot chance': ('canonical_stat', 'tower_bounce_shot_chance_pct'),
    'crit chance': ('canonical_stat', 'tower_crit_chance_pct'),
    'critical chance': ('canonical_stat', 'tower_crit_chance_pct'),
    'multishot targets': ('canonical_stat', 'tower_multishot_targets'),
    'super crit chance': ('canonical_stat', 'tower_supercrit_chance_pct'),
    'super critical chance': ('canonical_stat', 'tower_supercrit_chance_pct'),
    'super crit multi': ('canonical_stat', 'tower_supercrit_multiplier'),
    'super crit mult': ('canonical_stat', 'tower_supercrit_multiplier'),
    'knockback force': ('canonical_stat', 'tower_knockback_force'),
    'thorns damage': ('canonical_stat', 'tower_thorns_damage_pct'),
    'thorn damage': ('canonical_stat', 'tower_thorns_damage_pct'),
    'orb speed': ('canonical_stat', 'tower_orb_speed_rpm'),
    'orbs speed': ('canonical_stat', 'tower_orb_speed_rpm'),
    'free utility upgrade': ('canonical_stat', 'free_utility_upgrade_chance_pct'),
    'coins kill bonus': ('canonical_stat', 'coins_per_kill_bonus'),
    'coin kill bonus': ('canonical_stat', 'coins_per_kill_bonus'),
    'enemy health level skip': ('canonical_stat', 'enemy_health_level_skip_pct'),
    'enemy attack level skip': ('canonical_stat', 'enemy_attack_level_skip_pct'),
    'package chance': ('canonical_stat', 'package_chance_pct'),
    'max rend armor multi': ('canonical_stat', 'max_rend_mult'),
    'black hole duration': ('mechanic_param', 'uw.black_hole.duration_seconds'),
    'black hole cooldown': ('mechanic_param', 'uw.black_hole.cooldown_seconds'),
    'death wave quantity': ('mechanic_param', 'uw.death_wave.effect_wave_count'),
    'spotlight angle': ('mechanic_param', 'uw.spotlight.angle_degrees'),
    'spotlight bonus': ('mechanic_param', 'uw.spotlight.bonus_multiplier'),
    'chain lightning chance': ('mechanic_param', 'uw.chain_lightning.chance_pct'),
    'chain lightning quantity': ('mechanic_param', 'uw.chain_lightning.quantity'),
    'chain lightning damage': ('mechanic_param', 'uw.chain_lightning.damage_multiplier'),
    'chrono field cooldown': ('mechanic_param', 'uw.chrono_field.cooldown_seconds'),
    'chrono field speed reduction': ('mechanic_param', 'uw.chrono_field.slow_pct'),
}

ENHANCEMENT_ALIAS_OVERRIDES = {
    'damage': 'tower_damage',
    'health': 'tower_hp',
    'health regen': 'tower_regen',
    'defense absolute': 'tower_defense_absolute',
    'damage meter': 'tower_damage_per_meter_multiplier',
    'super crit multi': 'tower_supercrit_multiplier',
    'super crit mult': 'tower_supercrit_multiplier',
    'rend armor mult': 'tower_rend_armor_multiplier',
    'attack speed': 'tower_attack_speed',
    'land mine damage': 'tower_land_mine_damage',
    'wall health': 'wall_hp',
    'cash bonus': 'cash_kill_multiplier',
    'coin bonus': 'coin_bonus_multiplier',
    'cells kill bonus': 'cells_kill_multiplier',
    'free upgrades': 'free_upgrade_multiplier',
    'max rend armor multi': 'max_rend_mult',
    'recovery package': 'recovery_package_multiplier',
    'critical factor': 'tower_crit_multiplier',
    'enemy level skips': 'enemy_attack_level_skip_pct',
}


RELIC_CONTRIBUTOR_OVERRIDES = {
    'super critical chance': 'relic__tower__supercrit_chance__pct',
    'super critical mult': 'relic__tower__supercrit_multiplier__pct',
    'wall rebuild': 'relic__tower__wall_rebuild_seconds_reduction',
}

ENHANCEMENT_CONTRIBUTOR_OVERRIDES = {
    'orb size': 'enhancements__tower__orb_size__multiplier',
    'super crit multi': 'enhancements__tower__supercrit_multiplier__multiplier',
    'super critical mult': 'enhancements__tower__supercrit_multiplier__multiplier',
}

PERK_TARGET_DESTINATION_OVERRIDES = {
    'tower_hp': ('canonical_stat', 'tower_hp'),
    'tower_damage': ('canonical_stat', 'tower_damage'),
    'tower_regen': ('canonical_stat', 'tower_regen'),
    'tower_defense_absolute': ('canonical_stat', 'tower_defense_absolute'),
    'absolute_defense': ('canonical_stat', 'tower_defense_absolute'),
    'cash_bonus': ('canonical_stat', 'cash_kill_multiplier'),
    'coin_bonus': ('canonical_stat', 'coin_bonus_multiplier'),
    'interest': ('canonical_stat', 'interest_per_wave_pct'),
    'land_mine_damage': ('canonical_stat', 'tower_land_mine_damage'),
    'free_upgrade_chance_all': ('runtime_mechanic_param', 'perk.free_upgrade_chance_all_pct'),
    'def_pct': ('canonical_stat', 'tower_defense_pct'),
    'bounce_shot_count': ('canonical_stat', 'tower_bounce_shot_targets'),
    'orb_count': ('canonical_stat', 'tower_orb_count'),
    'max_game_speed': ('runtime_mechanic_param', 'perk.max_game_speed'),
    'cash_per_wave': ('canonical_stat', 'cash_per_wave'),
    'lifesteal': ('canonical_stat', 'tower_lifesteal_pct'),
    'knockback_force': ('canonical_stat', 'tower_knockback_force'),
    'uw_smart_missiles': ('runtime_mechanic_param', 'uw.smart_missiles.extra_missiles'),
    'uw_poison_swamp_radius': ('runtime_mechanic_param', 'uw.poison_swamp.radius_multiplier'),
    'uw_death_wave_waves': ('mechanic_param', 'uw.death_wave.effect_wave_count'),
    'uw_inner_land_mines_sets': ('runtime_mechanic_param', 'uw.inner_land_mines.extra_sets'),
    'uw_golden_tower_bonus': ('mechanic_param', 'uw.golden_tower.bonus_multiplier'),
    'uw_chain_lightning_damage': ('mechanic_param', 'uw.chain_lightning.damage_multiplier'),
    'uw_chrono_field_duration_seconds': ('mechanic_param', 'uw.chrono_field.duration_seconds'),
    'uw_black_hole_duration_seconds': ('mechanic_param', 'uw.black_hole.duration_seconds'),
    'uw_spotlight_damage_bonus': ('mechanic_param', 'uw.spotlight.bonus_multiplier'),
    'perk_wave_requirement': ('runtime_mechanic_param', 'perk.wave_requirement_multiplier'),
    'random_uw_unlock': ('capability', 'capability.random_uw_unlock.enabled'),
    'boss_health': ('environment_param', 'enemy.boss.health_multiplier'),
    'enemy_health': ('environment_param', 'enemy.health_multiplier'),
    'enemy_damage': ('environment_param', 'enemy.damage_multiplier'),
    'enemy_speed': ('environment_param', 'enemy.speed_multiplier'),
    'boss_speed': ('environment_param', 'enemy.boss.speed_multiplier'),
    'enemy_kill_cash': ('runtime_mechanic_param', 'perk.enemy_kill_cash_multiplier'),
    'ranged_enemy_damage': ('environment_param', 'enemy.ranged.damage_multiplier'),
    'ranged_enemy_attack_distance': ('environment_param', 'enemy.ranged.attack_distance_rule'),
}

def _slug(text: str) -> str:
    text = text.lower().strip()
    text = text.replace('&', ' and ')
    text = text.replace('%', ' pct ')
    text = re.sub(r'\s+', ' ', text)
    text = text.replace(' / ', ' ')
    text = text.replace('/', ' ')
    text = text.replace('-', ' ')
    text = text.replace('_', ' ')
    text = text.replace('+', ' ')
    text = re.sub(r'[^a-z0-9 ]+', '', text)
    return re.sub(r'\s+', ' ', text).strip()


@lru_cache(maxsize=1)
def _load_mapping_index() -> Tuple[Dict[str, Dict[str, str]], Dict[str, Dict[str, str]], Dict[str, Tuple[str, str]], Dict[str, str], Dict[Tuple[str, str], str]]:
    mapping_data = yaml.safe_load(KB_MAPPINGS_PATH.read_text())
    mapping_index: Dict[str, Dict[str, str]] = {}
    family_slug_index: Dict[Tuple[str, str], str] = {}
    for family, rows in mapping_data['source_families'].items():
        for row in rows:
            mapping_index[row['contributor_id']] = {
                'source_family': family,
                'destination_object_type': row['destination_object_type'],
                'destination_id': row['destination_id'],
                'resolver_id': row['resolver'],
            }
            parts = row['contributor_id'].split('__')
            if len(parts) >= 4:
                family_slug_index[(family, _slug(parts[2].replace('_', ' ')))] = row['contributor_id']
                if family == 'module' and len(parts) >= 4:
                    family_slug_index[(family, _slug(parts[1].replace('_', ' ') + ' ' + parts[2].replace('_', ' ')))] = row['contributor_id']

    stats = yaml.safe_load(KB_CANONICAL_STATS_PATH.read_text())
    canonical_stats: Dict[str, Dict[str, str]] = {}
    for domain, entries in stats['domains'].items():
        for entry in entries:
            canonical_stats[entry['id']] = {
                'domain': domain,
                'unit': entry['unit'],
                'resolver': entry['resolver'],
            }

    alias_data = yaml.safe_load(KB_ALIASES_PATH.read_text())
    alias_index: Dict[str, Tuple[str, str]] = {}
    for row in alias_data['alias_groups'].get('object_aliases', []):
        alias_index[_slug(row['alias'])] = (row['resolves_to_type'], row['resolves_to_id'])

    relic_index: Dict[str, str] = {}
    with RELIC_REGISTRY_PATH.open(newline='') as f:
        for row in csv.DictReader(f):
            contributor_id = row['contributor_id']
            parts = contributor_id.split('__')
            if len(parts) >= 4:
                key = _slug(parts[2].replace('_', ' '))
                relic_index[key] = contributor_id
    return mapping_index, canonical_stats, alias_index, relic_index, family_slug_index


@lru_cache(maxsize=1)
def _load_lab_values() -> Dict[Tuple[str, int], float]:
    out: Dict[Tuple[str, int], float] = {}
    with LAB_VALUES_PATH.open(newline='') as f:
        for row in csv.DictReader(f):
            try:
                name = str(row['lab_primary_name']).strip()
                level = int(row['level'])
                value = float(row['value'])
            except (ValueError, TypeError):
                continue
            out[(name, level)] = value
            out[(_slug(name), level)] = value
    return out



@lru_cache(maxsize=1)
def _load_lab_summary_lookup() -> Dict[str, Dict[str, float | str]]:
    path = KB / 'labs' / 'tables' / 'lab-track-summary.csv'
    if not path.exists():
        return {}
    df = pd.read_csv(path)
    out: Dict[str, Dict[str, float | str]] = {}
    for _, row in df.iterrows():
        name = str(row.get('lab_primary_name', '')).strip()
        try:
            payload = {
                'level_min': float(row.get('level_min', 0)),
                'level_max': float(row.get('level_max', 0)),
                'value_min': float(row.get('value_min', 0)),
                'linear_step': float(row.get('linear_step', 0)),
                'formula_family': str(row.get('formula_family', '')).strip().lower(),
            }
        except (TypeError, ValueError):
            continue
        out[name] = payload
        out[_slug(name)] = payload
    return out


def _lab_value_with_fallback(name: str, level: int | None, lab_values: Dict[Tuple[str, int], float], lab_summary: Dict[str, Dict[str, float | str]]) -> float | None:
    if level is None:
        return None
    direct = lab_values.get((name, level))
    if direct is None:
        direct = lab_values.get((_slug(name), level))
    if direct is not None:
        return direct
    if name in LAB_FORMULA_VALUES:
        try:
            return LAB_FORMULA_VALUES[name](level)
        except Exception:
            return None
    summary = lab_summary.get(name) or lab_summary.get(_slug(name))
    if not summary:
        return None
    if str(summary.get('formula_family', '')).lower() != 'linear':
        return None
    try:
        level_min = int(float(summary.get('level_min', 1)))
        value_min = float(summary.get('value_min', 0.0))
        linear_step = float(summary.get('linear_step', 0.0))
        return value_min + (level - level_min) * linear_step
    except (TypeError, ValueError):
        return None

@lru_cache(maxsize=1)
def _load_workshop_value_lookup() -> Dict[Tuple[str, int], float]:
    out: Dict[Tuple[str, int], float] = {}
    # Prefer the derived materialized table because it contains the full workshop ladders
    # for the published core stats. The older flat table in kb/workshop/tables tops out at
    # low levels and silently causes the engine to fall back to raw level numbers.
    with WORKSHOP_VALUES_DERIVED_PATH.open(newline='') as f:
        reader = csv.reader(f)
        header = next(reader)
        pairs = []
        for i in range(0, len(header), 2):
            if i + 1 < len(header) and header[i+1]:
                pairs.append((i, header[i+1]))
        normalized = {'HPregen': 'Health Regen'}
        for row in reader:
            for i, col in pairs:
                if i + 1 >= len(row):
                    continue
                try:
                    level = int(float(row[i]))
                    value = float(row[i+1])
                except (ValueError, TypeError):
                    continue
                ids_name = normalized.get(col, col)
                out[(ids_name, level)] = value
    # Keep the old direct table as a fallback only.
    if WORKSHOP_VALUES_PATH.exists():
        df = pd.read_csv(WORKSHOP_VALUES_PATH)
        pairs = [
            ('Level', 'Damage', 'Damage'),
            ('Level.1', 'Health', 'Health'),
            ('Level.2', 'HPregen', 'Health Regen'),
            ('Level.3', 'DefAbs', 'Defense Absolute'),
            ('Level.4', 'Damage / Meter', 'Damage / Meter'),
            ('Level.5', 'Lifesteal', 'Lifesteal'),
        ]
        for level_col, value_col, ids_name in pairs:
            if level_col not in df.columns or value_col not in df.columns:
                continue
            for _, r in df[[level_col, value_col]].dropna().iterrows():
                try:
                    level = int(float(r[level_col]))
                    value = float(r[value_col])
                except (ValueError, TypeError):
                    continue
                if (ids_name, level) not in out:
                    out[(ids_name, level)] = value
    return out


@lru_cache(maxsize=1)
def _load_card_ladders() -> Dict[Tuple[str, int], Dict[str, str]]:
    out: Dict[Tuple[str, int], Dict[str, str]] = {}
    with CARD_LADDERS_PATH.open(newline='') as f:
        for row in csv.DictReader(f):
            try:
                out[(row['canonical_name'], int(row['base_level']))] = row
            except (ValueError, TypeError):
                continue

    cards_cache_dir = KB / 'cards' / 'sources' / 'raw' / 'repo-cache' / 'wiki'
    for path in sorted(cards_cache_dir.glob('cards-*.csv')):
        with path.open(newline='') as f:
            rows = list(csv.reader(f))
        if not rows:
            continue
        header = rows[0]
        level_columns = [(idx, cell) for idx, cell in enumerate(header) if str(cell).strip().lower().startswith('lv.')]
        for row in rows[1:]:
            if len(row) < 3:
                continue
            canonical_name = str(row[1]).strip()
            if not canonical_name:
                continue
            for idx, cell in level_columns:
                if idx >= len(row):
                    continue
                raw = str(row[idx]).strip()
                if not raw:
                    continue
                try:
                    level = int(str(cell).replace('Lv.', '').strip())
                except (TypeError, ValueError):
                    continue
                key = (canonical_name, level)
                if key in out:
                    continue
                cleaned = raw.replace('%', '').replace('x', '').replace('?', '').strip()
                if cleaned.startswith('.'):
                    cleaned = '0' + cleaned
                try:
                    float(cleaned)
                except ValueError:
                    continue
                out[key] = {
                    'card_id': _slug(canonical_name).replace(' ', '_').upper(),
                    'canonical_name': canonical_name,
                    'base_level': str(level),
                    'raw_value': cleaned,
                    'unit': 'percent' if '%' in raw else 'raw_number',
                    'source_surface': str(path),
                    'source_url': 'https://the-tower-idle-tower-defense.fandom.com/wiki/Cards',
                    'verification_status': 'bundled_raw_wiki_cache_fallback',
                }
    return out


@lru_cache(maxsize=1)
def _load_card_effect_targets() -> Dict[str, Tuple[str, str]]:
    out: Dict[str, Tuple[str, str]] = {}
    with CARD_EFFECT_REGISTRY_PATH.open(newline='') as f:
        for row in csv.DictReader(f):
            if row.get('layer') != 'base_card':
                continue
            target = row.get('target_surface', '').strip()
            destination = CARD_TARGET_SURFACE_TO_DESTINATION.get(target)
            if destination:
                out[row['card_id']] = destination
    return out


@lru_cache(maxsize=1)
def _load_lab_application_registry() -> Dict[str, Dict[str, str]]:
    out: Dict[str, Dict[str, str]] = {}
    path = KB / 'labs' / 'tables' / 'lab-application-registry.csv'
    with path.open(newline='') as f:
        for row in csv.DictReader(f):
            name = str(row['lab_primary_name']).strip()
            out[name] = row
            out[_slug(name)] = row
    return out



@lru_cache(maxsize=1)
def _load_bot_track_values() -> Dict[Tuple[str, str, int], float]:
    out: Dict[Tuple[str, str, int], float] = {}
    with BOT_TRACK_VALUES_PATH.open(newline='') as f:
        for row in csv.DictReader(f):
            try:
                out[(row['bot_name'], row['track_name'], int(row['level']))] = float(row['track_value'])
            except (ValueError, TypeError):
                continue
    return out


@lru_cache(maxsize=1)
def _load_bot_lab_rules() -> Dict[str, Dict[str, float | str]]:
    data = yaml.safe_load(BOT_LABS_SUMMARY_PATH.read_text(encoding='utf-8')) or {}
    out: Dict[str, Dict[str, float | str]] = {}
    for key, payload in (data.get('bot_labs') or {}).items():
        out[key] = payload or {}
    return out


BOT_UPGRADE_BINDINGS = {
    ('Golden Bot', 'Duration'): ('bot_upgrade__golden_bot__duration__seconds', 'duration_seconds'),
    ('Golden Bot', 'Cooldown'): ('bot_upgrade__golden_bot__cooldown__seconds', 'cooldown_seconds'),
    ('Golden Bot', 'Bonus'): ('bot_upgrade__golden_bot__bonus__multiplier', 'bonus_multiplier_x'),
    ('Golden Bot', 'Range'): ('bot_upgrade__golden_bot__range__m', 'range_meters'),
    ('Amplify Bot', 'Duration'): ('bot_upgrade__amplify_bot__duration__seconds', 'duration_seconds'),
    ('Amplify Bot', 'Cooldown'): ('bot_upgrade__amplify_bot__cooldown__seconds', 'cooldown_seconds'),
    ('Amplify Bot', 'Bonus'): ('bot_upgrade__amplify_bot__bonus__multiplier', 'bonus_multiplier_x'),
    ('Amplify Bot', 'Range'): ('bot_upgrade__amplify_bot__range__m', 'range_meters'),
    ('Flame Bot', 'Cooldown'): ('bot_upgrade__flame_bot__cooldown__seconds', 'cooldown_seconds'),
    ('Flame Bot', 'Damage'): ('bot_upgrade__flame_bot__damage__multiplier', 'damage_multiplier_x'),
    ('Flame Bot', 'Damage R.'): ('bot_upgrade__flame_bot__damage_reduction__pct', 'damage_reduction_pct'),
    ('Flame Bot', 'Range'): ('bot_upgrade__flame_bot__range__m', 'range_meters'),
    ('Thunder Bot', 'Duration'): ('bot_upgrade__thunder_bot__duration__seconds', 'duration_seconds'),
    ('Thunder Bot', 'Cooldown'): ('bot_upgrade__thunder_bot__cooldown__seconds', 'cooldown_seconds'),
    ('Thunder Bot', 'Range'): ('bot_upgrade__thunder_bot__range__m', 'range_meters'),
    ('Thunder Bot', 'Linger'): ('bot_upgrade__thunder_bot__linger_slow__pct', 'linger_seconds'),
}

BOT_RANGE_CANONICALS = [
    ('mechanic_param', 'bot.global.range_bonus_m'),
    ('mechanic_param', 'bot.golden.range_m'),
    ('mechanic_param', 'bot.amplify.range_m'),
    ('mechanic_param', 'bot.flame.range_m'),
    ('mechanic_param', 'bot.thunder.range_m'),
]

BOT_LAB_BINDINGS = {
    'Amp Bot - Cooldown': ('amplify_bot_cooldown', -1.0),
    'Amp Bot - Duration': ('amplify_bot_duration', 0.5),
    'Flame Bot - Cooldown': ('flame_bot_cooldown', -1.0),
    'Gold Bot - Cooldown': ('golden_bot_cooldown', -1.0),
    'Gold Bot - Duration': ('golden_bot_duration', 0.5),
    'Thunder Bot - Cooldown': ('thunder_bot_cooldown', -1.0),
    'Thunder Bot - Linger Time': ('thunder_bot_linger_time', 0.5),
}


@lru_cache(maxsize=1)
def _load_guardian_track_values() -> Dict[Tuple[str, str, int], float]:
    out: Dict[Tuple[str, str, int], float] = {}
    with GUARDIAN_TRACK_REGISTRY_PATH.open(newline='') as f:
        for row in csv.DictReader(f):
            try:
                out[(row['guardian_name'], row['track_attribute'], int(row['level']))] = float(row['value'])
            except (ValueError, TypeError):
                continue
    return out


@lru_cache(maxsize=1)
def _load_uw_track_values() -> Dict[Tuple[str, str, int], float]:
    out: Dict[Tuple[str, str, int], float] = {}
    with UW_TRACK_VALUES_PATH.open(newline='') as f:
        for row in csv.DictReader(f):
            try:
                out[(row['uw_name'], row['track_name'], int(row['level_index']))] = float(row['value'])
            except (ValueError, TypeError):
                continue
    return out




@lru_cache(maxsize=1)
def _load_theme_song_registry() -> Dict[str, Tuple[str, str, str]]:
    out: Dict[str, Tuple[str, str, str]] = {}
    path = THEME_SONG_REGISTRY_PATH
    if not path.exists():
        return out
    with path.open(newline='', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            cid = (row.get('contributor_id') or '').strip()
            if cid:
                out[cid] = ((row.get('destination_object_type') or '').strip(), (row.get('destination_id') or '').strip(), (row.get('resolver_id') or '').strip())
    return out

@lru_cache(maxsize=1)
def _load_uw_plus_values() -> Dict[Tuple[str, str, int], float]:
    out: Dict[Tuple[str, str, int], float] = {}
    with UW_PLUS_VALUES_PATH.open(newline='') as f:
        for row in csv.DictReader(f):
            try:
                out[(row['uw_name'], row['plus_track_name'], int(row['level_index']))] = float(row['value'])
            except (ValueError, TypeError):
                continue
    return out


@lru_cache(maxsize=1)
def _load_uw_track_order() -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {}
    seen: set[tuple[str, str]] = set()
    with UW_TRACK_VALUES_PATH.open(newline='') as f:
        for row in csv.DictReader(f):
            key = (row['uw_name'], row['track_name'])
            if key in seen:
                continue
            seen.add(key)
            out.setdefault(row['uw_name'], []).append(row['track_name'])
    if out.get('Golden Tower') == ['Multiplier', 'Cooldown']:
        out['Golden Tower'] = ['Multiplier', 'Duration', 'Cooldown']
    return out


@lru_cache(maxsize=1)
def _load_uw_lab_wiki_values() -> Dict[Tuple[str, int], float]:
    """Load all wiki-verified UW lab value tables into a unified (lab_name, level) -> value lookup."""
    out: Dict[Tuple[str, int], float] = {}
    for lab_name, (rel_path, value_col) in _UW_LAB_TABLE_REGISTRY.items():
        path = KB / rel_path
        if not path.exists():
            continue
        with path.open(newline='') as f:
            for row in csv.DictReader(f):
                try:
                    level = int(row['level'])
                    raw = str(row[value_col]).strip().replace('%', '').replace('x', '').replace('X', '').replace('#', '').replace('+', '')
                    if raw:
                        out[(lab_name, level)] = float(raw)
                except (ValueError, TypeError, KeyError):
                    continue
    return out


@lru_cache(maxsize=1)
def _load_guardian_scout_values() -> Dict[Tuple[str, int], float]:
    out: Dict[Tuple[str, int], float] = {}
    with SCOUT_GUARDIAN_TABLE_PATH.open(newline='') as f:
        for row in csv.DictReader(f):
            level = int(row['level'])
            for key, col in [('Cooldown','cooldown_seconds'),('Range Bonus','range_bonus_multiplier'),('Duration','duration_seconds')]:
                try:
                    val = float(row[col])
                except (ValueError, TypeError):
                    continue
                out[(key, level)] = val
    return out



def _uw_contributor_id(uw_name: str, track_name: str) -> str | None:
    mapping = {
        ('Chain Lightning', 'Damage'): 'uw_upgrade__chain_lightning__damage__multiplier',
        ('Chain Lightning', 'Quantity'): 'uw_upgrade__chain_lightning__quantity__count',
        ('Chain Lightning', 'Chance'): 'uw_upgrade__chain_lightning__chance__pct',
        ('Smart Missiles', 'Damage'): 'uw_upgrade__smart_missiles__damage__multiplier',
        ('Smart Missiles', 'Quantity'): 'uw_upgrade__smart_missiles__quantity__count',
        ('Smart Missiles', 'Cooldown'): 'uw_upgrade__smart_missiles__cooldown__seconds',
        ('Death Wave', 'Damage'): 'uw_upgrade__death_wave__damage__multiplier',
        ('Death Wave', 'Quantity'): 'uw_upgrade__death_wave__effect_wave_count__count',
        ('Death Wave', 'Cooldown'): 'uw_upgrade__death_wave__cooldown__seconds',
        ('Golden Tower', 'Multiplier'): 'uw_upgrade__golden_tower__bonus__multiplier',
        ('Golden Tower', 'Duration'): 'uw_upgrade__golden_tower__duration__seconds',
        ('Golden Tower', 'Cooldown'): 'uw_upgrade__golden_tower__cooldown__seconds',
        ('Black Hole', 'Size'): 'uw_upgrade__black_hole__size__m',
        ('Black Hole', 'Duration'): 'uw_upgrade__black_hole__duration__seconds',
        ('Black Hole', 'Cooldown'): 'uw_upgrade__black_hole__cooldown__seconds',
        ('Spotlight', 'Multiplier'): 'uw_upgrade__spotlight__bonus__multiplier',
        ('Spotlight', 'Angle'): 'uw_upgrade__spotlight__angle__degrees',
        ('Spotlight', 'Quantity'): 'uw_upgrade__spotlight__count__count',
        ('Chrono Field', 'Duration'): 'uw_upgrade__chrono_field__duration__seconds',
        ('Chrono Field', 'Cooldown'): 'uw_upgrade__chrono_field__cooldown__seconds',
        ('Chrono Field', 'Speed Reduction'): 'uw_upgrade__chrono_field__slow__pct',
        ('Inner Land Mines', 'Quantity'): 'uw_upgrade__inner_land_mines__quantity__count',
        ('Inner Land Mines', 'Damage'): 'uw_upgrade__inner_land_mines__damage__multiplier',
        ('Inner Land Mines', 'Cooldown'): 'uw_upgrade__inner_land_mines__cooldown__seconds',
        ('Poison Swamp', 'Damage'): 'uw_upgrade__poison_swamp__damage__multiplier',
        ('Poison Swamp', 'Duration'): 'uw_upgrade__poison_swamp__duration__seconds',
        ('Poison Swamp', 'Cooldown'): 'uw_upgrade__poison_swamp__cooldown__seconds',
    }
    return mapping.get((uw_name, track_name))

def _mapping_lookup_for_family_name(family_slug_index: Dict[Tuple[str, str], str], family: str, name: str) -> Optional[str]:
    slug = _slug(name)
    return family_slug_index.get((family, slug))



@lru_cache(maxsize=1)
def _load_module_substat_values() -> Dict[Tuple[str, str, str], Tuple[float, str]]:
    df = pd.read_csv(KB / 'modules' / 'tables' / 'module-substats.csv')
    out: Dict[Tuple[str, str, str], Tuple[float, str]] = {}
    for _, row in df.iterrows():
        slot = str(row.get('slot', '')).strip().lower()
        substat = str(row.get('substat', '')).strip()
        rarity = str(row.get('rarity', '')).strip()
        try:
            value = float(row.get('value'))
        except (TypeError, ValueError):
            continue
        unit = str(row.get('unit', '')).strip().lower()
        out[(slot, substat, rarity)] = (value, unit)
    return out




def _normalize_module_unique_rarity(rarity: str) -> str:
    r = (rarity or '').strip().lower()
    if r.startswith('epic'):
        return 'epic'
    if r.startswith('legendary'):
        return 'legendary'
    if r.startswith('mythic'):
        return 'mythic'
    if r.startswith('ancestral'):
        return 'ancestral'
    return r




@lru_cache(maxsize=1)
def _load_module_main_effect_bases() -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {}
    if not MODULE_MAIN_EFFECT_BASES_PATH.exists():
        return out
    df = pd.read_csv(MODULE_MAIN_EFFECT_BASES_PATH)
    for _, row in df.iterrows():
        rarity = str(row.get('rarity', '')).strip()
        if not rarity:
            continue
        vals = {}
        for slot in ('cannon', 'armor', 'generator', 'core'):
            try:
                vals[slot] = float(row.get(f'{slot}_base'))
            except (TypeError, ValueError):
                continue
        out[rarity] = vals
    return out


@lru_cache(maxsize=1)
def _load_module_main_effect_steps() -> Dict[str, list[tuple[int, float]]]:
    out: Dict[str, list[tuple[int, float]]] = {'cannon': [], 'armor': [], 'generator': [], 'core': []}
    if not MODULE_MAIN_EFFECT_STEPS_PATH.exists():
        return out
    with MODULE_MAIN_EFFECT_STEPS_PATH.open(newline='') as f:
        rows = list(csv.reader(f))
    capture = False
    for row in rows:
        if not row:
            continue
        key = str(row[0]).strip()
        if key == 'Increase / lvl':
            capture = True
            continue
        if not capture:
            continue
        if key == '300.0':
            break
        try:
            level = int(float(key))
        except (TypeError, ValueError):
            continue
        for idx, slot in enumerate(('cannon', 'armor', 'generator', 'core'), start=1):
            try:
                inc = float(row[idx])
            except (TypeError, ValueError):
                continue
            out[slot].append((level, inc))
    return out


def _normalize_module_base_rarity(rarity: str | None) -> tuple[str | None, int]:
    value = str(rarity or '').strip()
    if not value:
        return None, 0
    match = re.match(r'^(Ancestral)(?:\s+(\d)\*)?$', value)
    if match:
        return 'Ancestral', int(match.group(2) or 0)
    return value, 0


def _module_main_effect_multiplier(slot_type: str, rarity: str | None, level: int | None) -> float | None:
    base_rarity, stars = _normalize_module_base_rarity(rarity)
    if not base_rarity or level is None:
        return None
    bases = _load_module_main_effect_bases().get(base_rarity)
    if not bases:
        return None
    try:
        base = float(bases[slot_type])
    except Exception:
        return None
    step_rows = _load_module_main_effect_steps().get(slot_type, [])
    total = base
    next_levels = [lvl for lvl, _ in step_rows[1:]] + [300]
    for (start, inc), nxt in zip(step_rows, next_levels):
        if level <= start:
            continue
        total += (min(level, nxt) - start) * inc
    star_factor = 1.0 + 0.04 * stars
    return round(total * star_factor + 1.0, 3)

@lru_cache(maxsize=1)
def _load_module_unique_effect_values() -> Dict[Tuple[str, str], Tuple[float, str]]:
    out: Dict[Tuple[str, str], Tuple[float, str]] = {}
    if not MODULE_UNIQUE_EFFECTS_TABLE_PATH.exists():
        return out
    df = pd.read_csv(MODULE_UNIQUE_EFFECTS_TABLE_PATH)
    rarity_columns = ('epic', 'legendary', 'mythic', 'ancestral')
    for _, row in df.iterrows():
        module_slug = _slug(str(row.get('module', '')).strip())
        measure = str(row.get('measure', '')).strip().lower()
        if not module_slug:
            continue
        for rarity in rarity_columns:
            try:
                value = float(row.get(rarity))
            except (TypeError, ValueError):
                continue
            out[(module_slug, rarity)] = (value, measure)
    return out


@lru_cache(maxsize=1)
def _load_assist_efficiency_lookup() -> Dict[int, float]:
    out: Dict[int, float] = {}
    path = KB / 'modules' / 'tables' / 'assist-stone-levels.csv'
    if not path.exists():
        return out
    df = pd.read_csv(path)
    for _, row in df.iterrows():
        try:
            level = int(row.get('stone_level'))
            frac = float(row.get('assist_efficiency_frac'))
        except (TypeError, ValueError):
            continue
        out[level] = frac
    return out


@lru_cache(maxsize=1)
def _load_perk_entities() -> Dict[str, Dict[str, object]]:
    out: Dict[str, Dict[str, object]] = {}
    if not PERK_ENTITY_REGISTRY_PATH.exists():
        return out
    with PERK_ENTITY_REGISTRY_PATH.open(newline='') as f:
        for row in csv.DictReader(f):
            perk_id = row.get('perk_id', '').strip()
            if not perk_id:
                continue
            try:
                max_picks = int(row.get('max_picks', '1'))
            except (TypeError, ValueError):
                max_picks = 1
            out[perk_id] = {
                'perk_name': row.get('perk_name', '').strip(),
                'category': row.get('category', '').strip(),
                'max_picks': max_picks,
                'stacking_type': row.get('stacking_type', '').strip(),
                'effect_count': row.get('effect_count', '').strip(),
                'status': row.get('status', '').strip(),
            }
    return out


@lru_cache(maxsize=1)
def _load_perk_effects() -> Dict[str, List[Dict[str, str]]]:
    out: Dict[str, List[Dict[str, str]]] = {}
    if not PERK_EFFECT_REGISTRY_PATH.exists():
        return out
    with PERK_EFFECT_REGISTRY_PATH.open(newline='') as f:
        for row in csv.DictReader(f):
            perk_id = row.get('perk_id', '').strip()
            if not perk_id:
                continue
            out.setdefault(perk_id, []).append(row)
    return out


@lru_cache(maxsize=1)
def _load_module_substat_units() -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not MODULE_SUBSTATS_TABLE_PATH.exists():
        return out
    with MODULE_SUBSTATS_TABLE_PATH.open(newline='') as f:
        for row in csv.DictReader(f):
            name = row.get('substat', '').strip()
            unit = row.get('unit', '').strip().lower()
            if name and unit and name not in out:
                out[name] = unit
    return out


def _make_instance_contributor_id(base_id: str | None, *, source_name: str, role: str | None = None, sub_name: str | None = None) -> str | None:
    if not base_id:
        return base_id
    parts = [base_id, _slug(source_name)]
    if role:
        parts.append(_slug(role))
    if sub_name:
        parts.append(_slug(sub_name))
    return '@@'.join(parts)


def _set_row_field(row: StatInput, field_name: str, value) -> None:
    object.__setattr__(row, field_name, value)


def _bind_kb_fields(row: StatInput, contributor_id: str, mapping_index: Dict[str, Dict[str, str]], canonical_stats: Dict[str, Dict[str, str]]) -> None:
    if contributor_id not in mapping_index:
        raise KeyError(f'Contributor id {contributor_id!r} not found in KB mapping index.')
    info = mapping_index[contributor_id]
    destination_id = info['destination_id']
    if info['destination_object_type'] == 'canonical_stat' and destination_id not in canonical_stats:
        raise KeyError(f'Destination id {destination_id!r} missing from canonical stats registry.')
    _set_row_field(row, 'contributor_id', contributor_id)
    _set_row_field(row, 'destination_object_type', info['destination_object_type'])
    _set_row_field(row, 'destination_id', destination_id)
    _set_row_field(row, 'resolver_id', info['resolver_id'])
    _set_row_field(row, 'kb_mapped', True)


def _bind_alias_destination(row: StatInput, alias_text: str, alias_index: Dict[str, Tuple[str, str]], canonical_stats: Dict[str, Dict[str, str]], *, note: str) -> None:
    slug = _slug(alias_text)
    if slug in ENHANCEMENT_ALIAS_OVERRIDES:
        _set_row_field(row, 'destination_object_type', 'canonical_stat')
        _set_row_field(row, 'destination_id', ENHANCEMENT_ALIAS_OVERRIDES[slug])
        _set_row_field(row, 'resolver_id', canonical_stats.get(row.destination_id, {}).get('resolver'))
        _set_row_field(row, 'kb_mapped', row.destination_id in canonical_stats)
        _set_row_field(row, 'notes', note)
        return
    match = alias_index.get(slug)
    if match is None:
        _set_row_field(row, 'notes', note + '_alias_missing')
        return
    _set_row_field(row, 'destination_object_type', match[0])
    _set_row_field(row, 'destination_id', match[1])
    if row.destination_object_type == 'canonical_stat':
        _set_row_field(row, 'resolver_id', canonical_stats.get(row.destination_id, {}).get('resolver'))
        _set_row_field(row, 'kb_mapped', row.destination_id in canonical_stats)
    _set_row_field(row, 'notes', note)


def _bind_destination(row: StatInput, destination: Tuple[str, str], canonical_stats: Dict[str, Dict[str, str]], *, note: str) -> None:
    _set_row_field(row, 'destination_object_type', destination[0])
    _set_row_field(row, 'destination_id', destination[1])
    if row.destination_object_type == 'canonical_stat':
        _set_row_field(row, 'resolver_id', canonical_stats.get(row.destination_id, {}).get('resolver'))
        _set_row_field(row, 'kb_mapped', row.destination_id in canonical_stats)
    elif row.destination_object_type in {'runtime_mechanic_param', 'mechanic_param', 'meta_progression_param', 'environment_param'}:
        _set_row_field(row, 'resolver_id', 'standard_scalar_param')
        _set_row_field(row, 'kb_mapped', True)
    elif row.destination_object_type in {'capability', 'account_flag'}:
        _set_row_field(row, 'resolver_id', 'capability_passthrough')
        _set_row_field(row, 'kb_mapped', True)
    _set_row_field(row, 'notes', note)



TRADE_OFF_BENEFIT_EFFECT_INDEXES = {
    'PERK_X1_50_TOWER_DAMAGE_BUT_BOSSES_HAVE_8X_HEALTH': {'1'},
    'PERK_X1_80_COINS_BUT_TOWER_MAX_HEALTH_70': {'1'},
    'PERK_ENEMIES_HAVE_50_HEALTH_BUT_TOWER_HEALTH_REGEN_AND_LIFESTEAL_90': {'1'},
    'PERK_ENEMIES_DAMAGE_50_BUT_TOWER_DAMAGE_50': {'1'},
    'PERK_RANGED_ENEMIES_ATTACK_DISTANCE_REDUCED_BUT_TOWER_RANGED_ENEMIES_DAMAGE_X3': {'1'},
    'PERK_ENEMIES_SPEED_40_BUT_ENEMIES_DAMAGE_X2_5': {'1'},
    'PERK_X12_00_CASH_PER_WAVE_BUT_ENEMY_KILL_DON_T_GIVE_CASH': {'1'},
    'PERK_TOWER_HEALTH_REGEN_X8_00_BUT_TOWER_MAX_MAX_HEALTH_60': {'1'},
    'PERK_BOSS_HEALTH_70_BUT_BOSS_SPEED_50': {'1'},
    'PERK_LIFESTEAL_X2_50_BUT_KNOCKBACK_FORCE_70': {'1'},
}

TRADE_OFF_LAB_SCALED_BENEFIT_EFFECT_INDEXES = {
    perk_id: indexes.copy()
    for perk_id, indexes in TRADE_OFF_BENEFIT_EFFECT_INDEXES.items()
}
TRADE_OFF_LAB_SCALED_BENEFIT_EFFECT_INDEXES['PERK_RANGED_ENEMIES_ATTACK_DISTANCE_REDUCED_BUT_TOWER_RANGED_ENEMIES_DAMAGE_X3'] = set()


def _active_perk_selections(account_state: AccountState, preset: str) -> List[tuple[str, int]]:
    preset_keys = [preset]
    if account_state.active_perk_preset:
        preset_keys.append(account_state.active_perk_preset)
    preset_keys.append('default')
    seen: set[str] = set()
    out: List[tuple[str, int]] = []
    for key in preset_keys:
        if not key or key in seen:
            continue
        seen.add(key)
        for selection in account_state.perk_presets.get(key, []):
            if selection.perk_id and selection.picks > 0:
                out.append((selection.perk_id, selection.picks))
    return out


def _perk_lab_state(account_state: AccountState) -> Dict[str, float]:
    standard_bonus_level = int(account_state.labs.get('Standard Perks Bonus') or 0)
    tradeoff_bonus_level = int(account_state.labs.get('Improve Trade-off Perks') or 0)
    return {
        'standard_bonus_multiplier': 1.0 + (standard_bonus_level / 100.0),
        'tradeoff_bonus_multiplier': 1.0 + (tradeoff_bonus_level / 100.0),
    }


def _scaled_perk_value(*, perk_meta: Dict[str, object], perk_id: str, operation: str, raw_value: str, picks: int, effect_index: str, perk_lab_state: Dict[str, float], perk_effect_meta: Optional[Dict[str, object]] = None):
    base_value = _perk_value_from_effect(operation, raw_value)
    if not isinstance(base_value, (int, float)):
        return base_value
    effect_meta = perk_effect_meta or {}
    category = str(perk_meta.get('category') or '').strip().lower()
    picks = max(1, int(picks))
    spb_applies = str(effect_meta.get('spb_applies') or '').strip().lower()
    spb_formula_class = str(effect_meta.get('spb_formula_class') or '').strip().lower()
    integrality_policy = str(effect_meta.get('integrality_policy') or '').strip().lower()
    if category == 'standard':
        standard_mult = float(perk_lab_state.get('standard_bonus_multiplier', 1.0) or 1.0)
        spb_enabled = spb_applies != 'no'
        if operation == 'multiplier' and float(base_value) > 1.0:
            if spb_formula_class == 'multiplicative' or not spb_formula_class:
                return (1.0 + ((float(base_value) - 1.0) * picks)) * (standard_mult if spb_enabled else 1.0)
            return (1.0 + ((float(base_value) - 1.0) * picks))
        if operation == 'remaining_fraction':
            delta = float(base_value) - 1.0
            return 1.0 + (delta * picks * (standard_mult if spb_enabled else 1.0))
        if operation in {'percentage_points_add', 'count_add', 'seconds_add', 'raw_add'}:
            scaled = float(base_value) * picks * (standard_mult if spb_enabled else 1.0)
            if integrality_policy == 'round_final':
                return float(round(scaled))
            return scaled
    if category == 'trade_off' and effect_index in TRADE_OFF_LAB_SCALED_BENEFIT_EFFECT_INDEXES.get(perk_id, set()):
        improve_mult = float(perk_lab_state.get('tradeoff_bonus_multiplier', 1.0) or 1.0)
        if operation == 'multiplier' and float(base_value) > 1.0:
            return float(base_value) * improve_mult
        if operation == 'remaining_fraction' and 0.0 <= float(base_value) <= 1.0:
            reduction = 1.0 - float(base_value)
            improved = min(0.999999, reduction * improve_mult)
            return 1.0 - improved
        if operation == 'percentage_points_add':
            return float(base_value) * improve_mult
    return base_value


def _perk_value_type_for_operation(operation: str) -> str:
    return {
        'multiplier': 'multiplier',
        'remaining_fraction': 'multiplier',
        'percentage_points_add': 'pct',
        'count_add': 'flat',
        'seconds_add': 'flat',
        'raw_add': 'flat',
        'set_to': 'resolved_value',
        'special_unlock': 'bool',
        'special_reduction': 'raw_text',
    }.get(operation, 'resolved_value')


def _perk_value_from_effect(operation: str, raw_value: str):
    if operation == 'special_unlock':
        return True
    if operation == 'special_reduction':
        return raw_value
    try:
        return float(raw_value)
    except (TypeError, ValueError):
        return raw_value


def _bind_perk_effect_destination(row: StatInput, target_stat_id: str, canonical_stats: Dict[str, Dict[str, str]], alias_index: Dict[str, Tuple[str, str]]) -> None:
    destination = PERK_TARGET_DESTINATION_OVERRIDES.get(target_stat_id)
    if destination is not None:
        _bind_destination(row, destination, canonical_stats, note=f'kb_perk_effect_routed:{target_stat_id}')
        return
    if target_stat_id in canonical_stats:
        _bind_destination(row, ('canonical_stat', target_stat_id), canonical_stats, note=f'kb_perk_effect_routed:{target_stat_id}')
        return
    _bind_alias_destination(row, target_stat_id.replace('_', ' '), alias_index, canonical_stats, note='kb_alias_routed_perk_target')


def _normalized_multiplier(value: float) -> float:
    # Supports inputs represented as 0.05 (+5%) or 1.14 (x1.14).
    return value if value > 1.0 else 1.0 + value


def _append(out: List[StatInput], row: StatInput) -> None:
    out.append(row)


def compile_stat_inputs(account_state: AccountState, *, preset_name: str | None = None, state_mode: str = 'start_of_run', card_preset_name: str | None = None, module_preset_name: str | None = None, perk_preset_name: str | None = None, perks_enabled: bool | None = None) -> List[StatInput]:
    preset = preset_name or account_state.default_preset
    card_preset = card_preset_name or getattr(account_state, 'active_card_preset', None) or preset
    module_preset = module_preset_name or getattr(account_state, 'active_module_preset', None) or preset
    active_perk_preset = getattr(account_state, 'active_perk_preset', None)
    perk_preset = perk_preset_name or active_perk_preset or preset
    if perks_enabled is None:
        perks_enabled = bool(active_perk_preset)
    state_mode = normalize_state_mode(state_mode)
    mapping_index, canonical_stats, alias_index, relic_index, family_slug_index = _load_mapping_index()
    lab_values = _load_lab_values()
    lab_summary = _load_lab_summary_lookup()
    workshop_values = _load_workshop_value_lookup()
    card_ladders = _load_card_ladders()
    card_effect_targets = _load_card_effect_targets()
    module_substat_units = _load_module_substat_units()
    perk_entities = _load_perk_entities()
    perk_effects = _load_perk_effects()
    module_substat_values = _load_module_substat_values()
    module_unique_effect_values = _load_module_unique_effect_values()
    assist_efficiency_lookup = _load_assist_efficiency_lookup()
    lab_application_registry = _load_lab_application_registry()
    uw_lab_wiki_values = _load_uw_lab_wiki_values()
    bot_track_values = _load_bot_track_values()
    bot_lab_rules = _load_bot_lab_rules()
    guardian_track_values = _load_guardian_track_values()
    uw_track_values = _load_uw_track_values()
    uw_plus_values = _load_uw_plus_values()
    theme_song_registry = _load_theme_song_registry()
    uw_track_order = _load_uw_track_order()
    guardian_scout_values = _load_guardian_scout_values()
    out: List[StatInput] = []

    # Labs: exact KB ladders where available; otherwise use the bundled lab application registry.
    for name, level in account_state.labs.items():
        row = StatInput(stat_name=name, source_family='lab', source_name=name, value=level, value_type='level', stage='account_state', provenance='IDS::Labs')
        contributor_id = LAB_IDS_TO_CONTRIBUTOR.get(name)
        if contributor_id is not None:
            _bind_kb_fields(row, contributor_id, mapping_index, canonical_stats)
            lab_value = _lab_value_with_fallback(name, level, lab_values, lab_summary)
            if name == 'Wall Invincibility' and level == 0:
                lab_value = 0.0
            if name == 'Wall Thorns' and level is not None and lab_value is None:
                lab_value = level / 100.0
            if lab_value is not None:
                _set_row_field(row, 'value', lab_value)
                _set_row_field(row, 'value_type', 'resolved_value')
        else:
            app = lab_application_registry.get(name) or lab_application_registry.get(_slug(name))
            if app is not None:
                destination = LAB_APPLICATION_TARGET_TO_DESTINATION.get((app['target_entity'], app['target_attribute']))
                if destination is not None:
                    _bind_destination(row, destination, canonical_stats, note='kb_lab_application_registry_routed')
                    operation_type = str(app.get('operation_type', '')).strip().lower()
                    if operation_type in {'enable', 'set_bool', 'set_boolean'}:
                        _set_row_field(row, 'value', bool(level and float(level) > 0))
                        _set_row_field(row, 'value_type', 'bool')
                    else:
                        lab_value = _lab_value_with_fallback(name, level, lab_values, lab_summary)
                        if lab_value is not None:
                            _set_row_field(row, 'value', lab_value)
                            _set_row_field(row, 'value_type', 'resolved_value')
                    if name == 'Missiles Explosion' and bool(level and float(level) > 0):
                        split_row = StatInput(**{field: getattr(row, field) for field in StatInput.__dataclass_fields__.keys()})
                        _set_row_field(split_row, 'stat_name', 'Missiles Explosion::Base Radius')
                        _set_row_field(split_row, 'source_family', 'lab')
                        _set_row_field(split_row, 'source_name', 'Missiles Explosion')
                        _set_row_field(split_row, 'value', 0.30)
                        _set_row_field(split_row, 'value_type', 'resolved_value')
                        _bind_destination(split_row, ('mechanic_param', 'uw.smart_missiles.explosion_radius_m'), canonical_stats, note='kb_lab_unlock_base_radius_split:missiles_explosion')
                        _append(out, split_row)
                    if name == 'Missile Barrage' and bool(level and float(level) > 0):
                        split_row = StatInput(**{field: getattr(row, field) for field in StatInput.__dataclass_fields__.keys()})
                        _set_row_field(split_row, 'stat_name', 'Missile Barrage::Base Quantity')
                        _set_row_field(split_row, 'source_family', 'lab')
                        _set_row_field(split_row, 'source_name', 'Missile Barrage')
                        _set_row_field(split_row, 'value', 20.0)
                        _set_row_field(split_row, 'value_type', 'resolved_value')
                        _bind_destination(split_row, ('mechanic_param', 'uw.smart_missiles.barrage_quantity'), canonical_stats, note='kb_lab_unlock_base_quantity_split:missile_barrage')
                        _append(out, split_row)
                    if name == 'Poison Swamp Stun' and bool(level and float(level) > 0):
                        split_row = StatInput(**{field: getattr(row, field) for field in StatInput.__dataclass_fields__.keys()})
                        _set_row_field(split_row, 'stat_name', 'Poison Swamp Stun::Base Chance')
                        _set_row_field(split_row, 'source_family', 'lab')
                        _set_row_field(split_row, 'source_name', 'Poison Swamp Stun')
                        _set_row_field(split_row, 'value', 5.0)
                        _set_row_field(split_row, 'value_type', 'resolved_value')
                        _bind_destination(split_row, ('mechanic_param', 'uw.poison_swamp.stun_chance_pct'), canonical_stats, note='kb_lab_unlock_base_chance_split:poison_swamp_stun')
                        _append(out, split_row)
                        split_row = StatInput(**{field: getattr(row, field) for field in StatInput.__dataclass_fields__.keys()})
                        _set_row_field(split_row, 'stat_name', 'Poison Swamp Stun::Base Duration')
                        _set_row_field(split_row, 'source_family', 'lab')
                        _set_row_field(split_row, 'source_name', 'Poison Swamp Stun')
                        _set_row_field(split_row, 'value', 1.0)
                        _set_row_field(split_row, 'value_type', 'resolved_value')
                        _bind_destination(split_row, ('mechanic_param', 'uw.poison_swamp.stun_duration_seconds'), canonical_stats, note='kb_lab_unlock_base_duration_split:poison_swamp_stun')
                        _append(out, split_row)
                else:
                    _set_row_field(row, 'notes', 'kb_lab_application_registry_unhandled_target')
            else:
                if name == 'Wall Rebuild':
                    _bind_destination(row, ('canonical_stat', 'wall_rebuild_seconds'), canonical_stats, note='kb_manual_wall_rebuild_lab_routed')
                    lab_value = _lab_value_with_fallback(name, level, lab_values, lab_summary)
                    if lab_value is not None:
                        _set_row_field(row, 'value', lab_value)
                        _set_row_field(row, 'value_type', 'resolved_value')
                elif name == 'Extra Extra Orbs':
                    _bind_destination(row, ('canonical_stat', 'tower_orb_count'), canonical_stats, note='kb_manual_extra_extra_orbs_lab_routed')
                    if level is not None:
                        _set_row_field(row, 'value', float(level))
                        _set_row_field(row, 'value_type', 'resolved_value')
                elif name == 'Defense Absolute':
                    _bind_destination(row, ('canonical_stat', 'tower_defense_absolute'), canonical_stats, note='kb_manual_defense_absolute_lab_routed')
                    lab_value = _lab_value_with_fallback(name, level, lab_values, lab_summary)
                    if lab_value is not None:
                        _set_row_field(row, 'value', lab_value)
                        _set_row_field(row, 'value_type', 'resolved_value')
                elif name == 'Damage / Meter':
                    _bind_destination(row, ('canonical_stat', 'tower_damage_per_meter_multiplier'), canonical_stats, note='kb_manual_damage_per_meter_lab_routed')
                    lab_value = _lab_value_with_fallback(name, level, lab_values, lab_summary)
                    if lab_value is not None:
                        _set_row_field(row, 'value', lab_value)
                        _set_row_field(row, 'value_type', 'resolved_value')
                elif name == 'Death Wave Health':
                    dw_state = account_state.ultimate_weapons.get('Death Wave')
                    if str(getattr(dw_state, 'unlocked', '')).strip().lower() == 'true' and level is not None:
                        _bind_destination(row, ('canonical_stat', 'tower_hp'), canonical_stats, note='kb_manual_death_wave_health_lab_routed')
                        _set_row_field(row, 'value', 5.0 + 0.25 * float(level))
                        _set_row_field(row, 'value_type', 'multiplier')
                        _set_row_field(row, 'notes', 'kb_manual_death_wave_health_lab_routed:ep_formula_eph_health_dwhp_multiplier')
                    else:
                        _set_row_field(row, 'notes', 'death_wave_health_present_but_uw_not_owned_or_level_missing')
                else:
                    dest = _UW_LAB_DIRECT_DESTINATION.get(name)
                    if dest is not None:
                        _bind_destination(row, dest, canonical_stats, note=f'kb_uw_lab_direct_routed:{name}')
                        if dest[0] == 'capability':
                            _set_row_field(row, 'value', bool(level and float(level) > 0))
                            _set_row_field(row, 'value_type', 'bool')
                            _set_row_field(row, 'notes', f'kb_lab_capability_{"resolved" if row.value else "locked"}:{name}')
                        elif name == 'Max Rend Armor Multiplier' and level is not None:
                            _set_row_field(row, 'value', 0.25 * float(level))
                            _set_row_field(row, 'value_type', 'resolved_value')
                            _set_row_field(row, 'notes', 'kb_lab_formula_verified:Max Rend Armor Multiplier:+0.25_per_level')
                        elif name in BOT_LAB_BINDINGS and level is not None:
                            rule_key, fallback_step = BOT_LAB_BINDINGS[name]
                            rule = bot_lab_rules.get(rule_key, {})
                            per_level = rule.get('effect_per_level_seconds')
                            if per_level is None:
                                per_level = fallback_step
                            _set_row_field(row, 'value', float(level) * float(per_level))
                            _set_row_field(row, 'value_type', 'resolved_value')
                            _set_row_field(row, 'notes', f'kb_bot_lab_formula_verified:{name}')
                        else:
                            wiki_val = uw_lab_wiki_values.get((name, level)) if level is not None else None
                            if wiki_val is not None:
                                _set_row_field(row, 'value', wiki_val)
                                _set_row_field(row, 'value_type', 'resolved_value')
                                _set_row_field(row, 'notes', f'kb_uw_lab_wiki_verified:{name}')
                            elif level is not None and level > 0:
                                _set_row_field(row, 'value', float(level))
                                _set_row_field(row, 'value_type', 'level')
                                _set_row_field(row, 'notes', f'kb_lab_routed_level_pending_value:{name}')
                    elif name in _NON_CALCULATOR_SCOPE_LABS:
                        _set_row_field(row, 'notes', f'non_calculator_scope:{name}')
                    else:
                        _set_row_field(row, 'notes', 'kb_routing_pending_for_lab_label')
        _append(out, row)

    # Workshop: exact contributor routing + value lookup where the KB contains ladders.
    for name, entry in account_state.workshop.items():
        level = entry.max_level if state_mode == 'max_progression' and entry.max_level is not None else entry.preset_levels.get(preset)
        row = StatInput(stat_name=name, source_family='workshop', source_name=name, value=level, value_type='level', stage='loadout_resolved', preset_name=preset, provenance='IDS::WS')
        if state_mode == 'max_progression' and entry.max_level is not None:
            _set_row_field(row, 'notes', 'state_mode=max_progression:using_workshop_max_level')
        contributor_id = WORKSHOP_IDS_TO_CONTRIBUTOR.get(name)
        if contributor_id is not None:
            _bind_kb_fields(row, contributor_id, mapping_index, canonical_stats)
            if level is not None and (name, level) in workshop_values:
                _set_row_field(row, 'value', workshop_values[(name, level)])
                _set_row_field(row, 'value_type', 'resolved_value')
            elif level is not None and name in WORKSHOP_FORMULA_VALUES:
                _set_row_field(row, 'value', WORKSHOP_FORMULA_VALUES[name](level))
                _set_row_field(row, 'value_type', 'resolved_value')
                _set_row_field(row, 'notes', (row.notes or '') + ':kb_workshop_summary_formula_derived')
            else:
                _set_row_field(row, 'notes', ((row.notes or '') + ':unresolved_workshop_level_no_value_formula').strip(':'))
        else:
            _set_row_field(row, 'notes', 'kb_routing_pending_for_workshop_label')
        _append(out, row)

    # Enhancements: IDS already exposes the effective multiplier/value. Route by alias only where canonical stat exists.
    for cells in account_state.workshop_enhancements.rows:
        if not cells or not cells[0].strip():
            continue
        name = cells[0].strip()
        alias_name = name.rstrip('+').strip()
        value = None
        for idx in [1, 2, 3]:
            if idx < len(cells):
                try:
                    value = float(cells[idx])
                    break
                except (ValueError, TypeError):
                    continue
        if value is None:
            continue
        row = StatInput(stat_name=name, source_family='enhancement', source_name=name, value=value, value_type='resolved_value', stage='account_state', provenance='IDS::WS+')
        contributor_id = ENHANCEMENT_CONTRIBUTOR_OVERRIDES.get(_slug(alias_name))
        if contributor_id:
            _bind_kb_fields(row, contributor_id, mapping_index, canonical_stats)
            _set_row_field(row, 'notes', 'kb_contributor_override_enhancement')
        else:
            _bind_alias_destination(row, alias_name, alias_index, canonical_stats, note='kb_alias_routed_enhancement')
        alias_slug = _slug(alias_name)
        if alias_slug == 'enemy level skips':
            for extra_id in ('enhancements__tower__enemy_attack_level_skip__multiplier', 'enhancements__tower__enemy_health_level_skip__multiplier'):
                extra = StatInput(stat_name=name, source_family='enhancement', source_name=name, value=value, value_type='resolved_value', stage='account_state', provenance='IDS::WS+', notes='kb_dual_routed_enhancement')
                _bind_kb_fields(extra, extra_id, mapping_index, canonical_stats)
                _append(out, extra)
        if alias_slug == 'coin bonus':
            extra = StatInput(stat_name=name, source_family='enhancement', source_name=name, value=value, value_type='resolved_value', stage='account_state', provenance='IDS::WS+', notes='kb_dual_routed_enhancement:coins_per_kill_spillover')
            _bind_destination(extra, ('canonical_stat', 'coins_per_kill_bonus'), canonical_stats, note='kb_dual_routed_enhancement:coins_per_kill_spillover')
            if row.value_type == 'resolved_value' and isinstance(row.value, (int, float)) and 0.0 <= float(row.value) <= 1.0:
                dest = row.destination_id or ''
                if dest.endswith('_pct') or dest.endswith('.chance_pct') or dest.endswith('.slow_pct') or dest.endswith('.damage_reduction_pct'):
                    _set_row_field(row, 'value', float(row.value) * 100.0)
                    _set_row_field(row, 'notes', f"{row.notes or 'ids_uw_current_value_preserved'}; normalized_fraction_to_pct_points")
            _append(out, row)
            _append(out, extra)
            continue
        if alias_slug == 'rend armor mult':
            extra = StatInput(stat_name=name, source_family='enhancement', source_name=name, value=value, value_type='resolved_value', stage='account_state', provenance='IDS::WS+', notes='kb_dual_routed_enhancement:max_rend_surface')
            _bind_destination(extra, ('canonical_stat', 'max_rend_mult'), canonical_stats, note='kb_dual_routed_enhancement:max_rend_surface')
            _append(out, extra)
        else:
            _append(out, row)

    # Theme/song passive bonus: fold the bundled cosmetic coin multiplier into the calculator coin surface.
    if getattr(account_state, 'theme_song_coin_multiplier', None) is not None:
        row = StatInput(stat_name='Theme Song Coin Bonus', source_family='theme_song', source_name='Themes & Songs', value=account_state.theme_song_coin_multiplier, value_type='resolved_value', stage='account_state', provenance='IDS::Themes & Songs', notes='kb_theme_song_preserved_on_cosmetic_helper_surface', contributor_id='theme_song__global__coin_bonus__multiplier')
        _bind_kb_fields(row, 'theme_song__global__coin_bonus__multiplier', mapping_index, canonical_stats)
        _append(out, row)

    # Player-meta helper surfaces used by KB-aligned all-coin composition.
    player_meta = getattr(account_state, 'player_meta', {}) or {}
    helper_meta_specs = [
        ('Disable Ads', 'player_stuff__flag__disable_ads__boolean', 'bool'),
        ('Starter Pack', 'player_stuff__flag__starter_pack__boolean', 'bool'),
        ('Epic Pack', 'player_stuff__flag__epic_pack__boolean', 'bool'),
        ('Farming Tier', 'player_stuff__profile__farming_tier__enum', 'raw_text'),
        ('Coin Multiplier', 'player_stuff__derived__coin_multiplier__enum', 'raw_text'),
    ]
    for meta_name, contributor_id, value_type in helper_meta_specs:
        raw_value = player_meta.get(meta_name)
        if raw_value is None:
            continue
        value = raw_value
        if value_type == 'bool':
            value = str(raw_value).strip().lower() in {'true', '1', 'yes', 'unlocked'}
        row = StatInput(stat_name=meta_name, source_family='player_stuff', source_name=meta_name, value=value, value_type=value_type, stage='account_state', provenance='IDS::Player & Stuff')
        _bind_kb_fields(row, contributor_id, mapping_index, canonical_stats)
        _append(out, row)

    # Relics: registry-only direct values from IDS. These are already account-state effects, not spend levels.
    for name, value in account_state.relics.items():
        if value is None or name in {'Relics', 'Total Bonuses', 'Misc.', 'Event Relics', 'Guild Relics', 'Other Relics', 'Total Relics'}:
            continue
        if _slug(name) == 'bot range':
            for dest in BOT_RANGE_CANONICALS:
                row = StatInput(stat_name=name, source_family='relic', source_name=name, value=value, value_type='resolved_value', stage='account_state', provenance='IDS::Relics')
                _bind_destination(row, dest, canonical_stats, note='kb_bot_range_relic_promoted')
                _append(out, row)
            continue
        row = StatInput(stat_name=name, source_family='relic', source_name=name, value=value, value_type='resolved_value', stage='account_state', provenance='IDS::Relics')
        contributor_id = relic_index.get(_slug(name)) or RELIC_CONTRIBUTOR_OVERRIDES.get(_slug(name))
        if contributor_id:
            _bind_kb_fields(row, contributor_id, mapping_index, canonical_stats)
        else:
            override_dest = RELIC_ALIAS_OVERRIDES.get(_slug(name))
            if override_dest is not None:
                _bind_destination(row, override_dest, canonical_stats, note='kb_relic_override_routed')
            else:
                _bind_alias_destination(row, name, alias_index, canonical_stats, note='kb_alias_routed_relic')
        _append(out, row)

    # Vault: preserve exact scalar values and unlock booleans.
    for name, value in account_state.vault.items():
        if _slug(name) == 'bot range':
            for dest in BOT_RANGE_CANONICALS:
                row = StatInput(stat_name=name, source_family='vault', source_name=name, value=value, value_type='resolved_value', stage='account_state', provenance='IDS::Vault')
                _bind_destination(row, dest, canonical_stats, note='kb_bot_range_vault_promoted')
                _append(out, row)
            continue
        value_type = 'bool' if isinstance(value, bool) else ('resolved_value' if isinstance(value, (int, float)) else 'raw_text')
        row = StatInput(stat_name=name, source_family='vault', source_name=name, value=value, value_type=value_type, stage='account_state', provenance='IDS::Vault')
        contributor_id = _mapping_lookup_for_family_name(family_slug_index, 'vault', name)
        if contributor_id:
            _bind_kb_fields(row, contributor_id, mapping_index, canonical_stats)
        else:
            numeric_override = VAULT_NUMERIC_OVERRIDES.get(_slug(name)) if not isinstance(value, bool) else None
            fallback_dest = VAULT_BOOLEAN_FLAGS.get(_slug(name)) if isinstance(value, bool) else None
            if numeric_override is not None:
                _bind_destination(row, numeric_override, canonical_stats, note='kb_vault_numeric_override_routed')
            elif fallback_dest is not None:
                _bind_destination(row, fallback_dest, canonical_stats, note='kb_vault_boolean_flag_routed')
            else:
                _bind_alias_destination(row, name, alias_index, canonical_stats, note='kb_alias_routed_vault')
        _append(out, row)

    bot_slug_map = {
        'gold bot': 'golden',
        'golden bot': 'golden',
        'amp bot': 'amplify',
        'amplify bot': 'amplify',
        'flame bot': 'flame',
        'thunder bot': 'thunder',
    }
    owned_bot_aliases = set()
    for name in account_state.bots:
        key = _slug(str(name)).replace('_', ' ')
        owned_bot_aliases.add(key)
        owned_bot_aliases.add(key.replace('golden', 'gold'))
        owned_bot_aliases.add(key.replace('amplify', 'amp'))
    for source_name, bot_slug in bot_slug_map.items():
        unlock_row = StatInput(
            stat_name=f'{source_name.title()}::Unlocked',
            source_family='bot_unlock',
            source_name=source_name.title(),
            value=(source_name in owned_bot_aliases),
            value_type='bool',
            stage='account_state',
            provenance='IDS::Bots',
            notes='ids_bot_unlock_flag_preserved',
        )
        _set_row_field(unlock_row, 'destination_object_type', 'capability')
        _set_row_field(unlock_row, 'destination_id', f'bot.{bot_slug}.owned')
        _set_row_field(unlock_row, 'resolver_id', 'standard_bool')
        _set_row_field(unlock_row, 'kb_mapped', True)
        _append(out, unlock_row)

    # Bots: route medal-funded tracks into mechanic_param canonicals via KB contributor mappings.
    for bot_name, upgrades in account_state.bot_upgrades.items():
        for attr, level in upgrades.items():
            binding = BOT_UPGRADE_BINDINGS.get((bot_name, attr))
            contributor_id, track_name = binding if binding is not None else (None, None)
            resolved = bot_track_values.get((bot_name, track_name, level)) if track_name is not None and level is not None else None
            row = StatInput(stat_name=f'{bot_name}::{attr}', source_family='bot', source_name=bot_name, value=resolved if resolved is not None else level, value_type='resolved_value' if resolved is not None else 'level', stage='account_state', provenance='IDS::Bots', notes='kb_bot_track_resolved' if resolved is not None else 'runtime_surface_preserved_pending_bot_track_lookup')
            if contributor_id is not None:
                _bind_kb_fields(row, contributor_id, mapping_index, canonical_stats)
                _set_row_field(row, 'kb_mapped', resolved is not None)
            else:
                _set_row_field(row, 'destination_object_type', 'runtime_mechanic_param')
                _set_row_field(row, 'destination_id', f'bot.{_slug(bot_name).replace(' ', '_')}.{track_name or _slug(attr).replace(' ', '_')}')
                _set_row_field(row, 'resolver_id', 'standard_scalar_param')
                _set_row_field(row, 'kb_mapped', resolved is not None)
            _append(out, row)

    if account_state.guardians.rows:
        current_guardian = None
        for row_cells in account_state.guardians.rows:
            name = row_cells[0].strip() if len(row_cells) > 0 else ''
            attr = row_cells[2].strip() if len(row_cells) > 2 else ''
            display = row_cells[4].strip() if len(row_cells) > 4 else ''
            if name and name not in {'true', 'false'}:
                current_guardian = name
            if current_guardian and attr and display:
                level_token = display.split('|', 1)[0].strip()
                try:
                    level = int(float(level_token))
                except ValueError:
                    level = None
                guardian_attr_map = {
                    'cooldown': 'cooldown',
                    'duration': 'duration',
                    'range bonus': 'range_bonus',
                    'cash bonus': 'cash_bonus',
                    'recovery amount': 'recovery_amount',
                    'max recovery': 'max_recovery',
                    'percentage': 'percentage',
                    'multiplier': 'multiplier',
                    'targets': 'targets',
                    'find chance': 'find_chance',
                    'double find chance': 'double_find_chance',
                }
                g_attr = guardian_attr_map.get(_slug(attr), _slug(attr).replace(' ', '_'))
                resolved = guardian_track_values.get((current_guardian, g_attr, level)) if level is not None else None
                if resolved is None and current_guardian == 'Scout' and level is not None:
                    resolved = guardian_scout_values.get((attr, level))
                row = StatInput(stat_name=f'{current_guardian}::{attr}', source_family='guardian', source_name=current_guardian, value=resolved if resolved is not None else level, value_type='resolved_value' if resolved is not None else 'level', stage='account_state', provenance='IDS::Guardians', notes='kb_guardian_track_resolved' if resolved is not None else 'runtime_surface_preserved_pending_guardian_track_lookup')
                destination = GUARDIAN_DESTINATION_OVERRIDES.get((current_guardian, attr))
                if destination is not None:
                    _bind_destination(row, destination, canonical_stats, note='kb_guardian_override_routed')
                else:
                    _set_row_field(row, 'destination_object_type', 'runtime_mechanic_param')
                    _set_row_field(row, 'destination_id', f'guardian.{_slug(current_guardian).replace(' ', '_')}.{g_attr}')
                    _set_row_field(row, 'resolver_id', 'standard_scalar_param')
                    _set_row_field(row, 'kb_mapped', resolved is not None)
                _append(out, row)

    # UWs and UW+: resolve exact track values from bundled ladders and registry-driven track order.
    for uw_name, uw in account_state.ultimate_weapons.items():
        uw_slug = _slug(uw_name).replace(' ', '_')
        unlocked_bool = str(getattr(uw, 'unlocked', '')).strip().lower() == 'true'
        unlock_row = StatInput(
            stat_name=f'{uw_name}::Unlocked',
            source_family='uw_unlock',
            source_name=uw_name,
            value=unlocked_bool,
            value_type='bool',
            stage='account_state',
            provenance='IDS::UWs',
            notes='ids_uw_unlock_flag_preserved',
        )
        _set_row_field(unlock_row, 'destination_object_type', 'capability')
        _set_row_field(unlock_row, 'destination_id', f'uw.{uw_slug}.owned')
        _set_row_field(unlock_row, 'resolver_id', 'standard_bool')
        _set_row_field(unlock_row, 'kb_mapped', True)
        _append(out, unlock_row)

        tracks = uw_track_order.get(uw_name, [])
        for idx, raw_level in enumerate(uw.track_levels):
            try:
                level = int(str(raw_level).strip())
            except ValueError:
                level = None
            track_name = tracks[idx] if idx < len(tracks) else f'track_{idx+1}'
            ids_actual_value = uw.track_values[idx] if idx < len(uw.track_values) else None
            resolved = ids_actual_value if ids_actual_value is not None else (uw_track_values.get((uw_name, track_name, level)) if level is not None else None)
            if resolved is None and level is not None and uw_name == 'Golden Tower' and track_name == 'Duration':
                resolved = 15.0 + float(level)
            note = 'ids_uw_current_value_preserved' if ids_actual_value is not None else ('kb_uw_track_resolved' if resolved is not None else 'runtime_surface_preserved_pending_uw_track_lookup')
            row = StatInput(stat_name=f'{uw_name}::{track_name}', source_family='uw', source_name=uw_name, value=resolved if resolved is not None else level, value_type='resolved_value' if resolved is not None else 'level', stage='account_state', provenance='IDS::UWs', notes=note)
            contributor_id = UW_CONTRIBUTOR_OVERRIDES.get((uw_name, track_name)) or _uw_contributor_id(uw_name, track_name)
            if contributor_id in mapping_index:
                _bind_kb_fields(row, contributor_id, mapping_index, canonical_stats)
            else:
                destination = UW_MECHANIC_DESTINATION_OVERRIDES.get((uw_name, track_name))
                if destination is not None:
                    _bind_destination(row, destination, canonical_stats, note='kb_uw_override_routed')
                else:
                    _set_row_field(row, 'destination_object_type', 'mechanic_param')
                    _set_row_field(row, 'destination_id', f'uw.{_slug(uw_name).replace(' ', '_')}.{_slug(track_name).replace(' ', '_')}')
                    _set_row_field(row, 'resolver_id', 'standard_scalar_param')
                    _set_row_field(row, 'kb_mapped', resolved is not None)
            if row.value_type == 'resolved_value' and isinstance(row.value, (int, float)) and 0.0 <= float(row.value) <= 1.0:
                dest = row.destination_id or ''
                if dest.endswith('_pct') or dest.endswith('.chance_pct') or dest.endswith('.slow_pct') or dest.endswith('.damage_reduction_pct'):
                    _set_row_field(row, 'value', float(row.value) * 100.0)
                    _set_row_field(row, 'notes', f"{row.notes or 'ids_uw_current_value_preserved'}; normalized_fraction_to_pct_points")
            _append(out, row)
    for track_name, track in account_state.uw_plus_tracks.items():
        level = None
        token = track.display_token.split('|',1)[0].strip() if track.display_token else ''
        if token.lower().startswith('lo'):
            level = 0
        else:
            try:
                level = int(token)
            except ValueError:
                level = None
        resolved = uw_plus_values.get((track.uw_name, track.plus_track_name, level)) if level is not None else None
        row = StatInput(stat_name=track_name, source_family='uw_plus', source_name=track.uw_name, value=resolved if resolved is not None else (0.0 if level == 0 else track.display_token), value_type='resolved_value' if resolved is not None or level == 0 else 'display_token', stage='account_state', provenance='IDS::UWs', notes='kb_uw_plus_track_resolved' if resolved is not None else ('kb_uw_plus_locked_level0' if level == 0 else 'runtime_surface_preserved_pending_uw_plus_lookup'))
        if level is not None:
            _set_row_field(row, 'destination_object_type', 'mechanic_param')
            _set_row_field(row, 'destination_id', f'uw_plus.{_slug(track.uw_name).replace(' ', '_')}.{_slug(track.plus_track_name).replace(' ', '_')}')
            _set_row_field(row, 'resolver_id', 'standard_scalar_param')
            _set_row_field(row, 'kb_mapped', True)
        _append(out, row)

    # Cards: only active preset cards contribute. Use exact base ladder rows and alias routing.
    active_cards = account_state.card_presets.get(card_preset, [])
    for card_name in active_cards:
        snap = account_state.cards_inventory.get(card_name)
        if snap is None or snap.level is None:
            continue
        ladder = card_ladders.get((card_name, snap.level))
        value = None
        if ladder is not None:
            try:
                value = float(ladder['raw_value'])
            except (ValueError, TypeError):
                value = None
        row = StatInput(stat_name=card_name, source_family='card', source_name=card_name, value=value if value is not None else snap.level, value_type='resolved_value' if value is not None else 'level', stage='loadout_resolved', preset_name=card_preset, provenance='IDS::Cards')
        card_id = (ladder or {}).get('card_id') if ladder else None
        destination = card_effect_targets.get(card_id or '')
        if card_id == 'FREE_UPGRADES':
            for target_id in ('free_attack_upgrade_chance_pct', 'free_defense_upgrade_chance_pct', 'free_utility_upgrade_chance_pct'):
                split_row = StatInput(**{field: getattr(row, field) for field in StatInput.__dataclass_fields__.keys()})
                _bind_destination(split_row, ('canonical_stat', target_id), canonical_stats, note=f'kb_card_effect_registry_split_routed:{card_id}')
                _append(out, split_row)
            continue
        if destination is not None:
            _bind_destination(row, destination, canonical_stats, note=f'kb_card_effect_registry_routed:{card_id}')
        else:
            fallback_destination = CARD_NAME_FALLBACK_DESTINATION.get(_slug(card_name))
            if fallback_destination is not None:
                _bind_destination(row, fallback_destination, canonical_stats, note='kb_card_name_fallback_routed')
            else:
                _bind_alias_destination(row, card_name, alias_index, canonical_stats, note='kb_alias_routed_card')
        if row.destination_object_type == 'capability' and row.destination_id and row.destination_id.endswith('.enabled'):
            _set_row_field(row, 'value', True)
            _set_row_field(row, 'value_type', 'bool')
        if row.destination_id == 'tower_orb_count' and card_name == 'Extra Orb':
            _set_row_field(row, 'value', 1.0)
            _set_row_field(row, 'value_type', 'resolved_value')
            _set_row_field(row, 'notes', (row.notes or '') + ':extra_orb_card_count_bonus')
        _append(out, row)


    # Perks: run-scoped selected modifiers owned by KB perk registries.
    perk_lab_state = _perk_lab_state(account_state)
    selected_perks = _active_perk_selections(account_state, perk_preset) if perks_enabled else []
    for perk_id, requested_picks in selected_perks:
        perk_meta = perk_entities.get(perk_id, {})
        perk_name = str(perk_meta.get('perk_name') or perk_id)
        max_picks = int(perk_meta.get('max_picks') or 1)
        applied_picks = max(0, min(requested_picks, max_picks))
        effects = perk_effects.get(perk_id, [])
        if applied_picks <= 0:
            continue
        for effect in effects:
            operation = effect.get('operation', '').strip()
            raw_value = effect.get('effect_value', '').strip()
            target_stat_id = effect.get('target_stat_id', '').strip()
            effect_index = effect.get('effect_index', '').strip()
            value = _scaled_perk_value(
                perk_meta=perk_meta,
                perk_effect_meta=effect,
                perk_id=perk_id,
                operation=operation,
                raw_value=raw_value,
                picks=applied_picks,
                effect_index=effect_index,
                perk_lab_state=perk_lab_state,
            )
            value_type = _perk_value_type_for_operation(operation)
            row = StatInput(
                stat_name=f"{perk_name}::effect_{effect_index}",
                source_family='perk',
                source_name=perk_name,
                value=value,
                value_type=value_type,
                stage='run_selected',
                preset_name=perk_preset,
                provenance='KB::Perks',
                notes=f"perk_id={perk_id};picks={applied_picks};operation={operation};target={target_stat_id};standard_perk_bonus_mult={perk_lab_state['standard_bonus_multiplier']:.4f};tradeoff_bonus_mult={perk_lab_state['tradeoff_bonus_multiplier']:.4f}",
                contributor_id=f"perk::{perk_id}::effect_{effect_index}",
            )
            if target_stat_id == 'free_upgrade_chance_all':
                _bind_perk_effect_destination(row, target_stat_id, canonical_stats, alias_index)
                _append(out, row)
                for split_target in ('free_attack_upgrade_chance_pct', 'free_defense_upgrade_chance_pct', 'free_utility_upgrade_chance_pct'):
                    split_row = StatInput(**{field: getattr(row, field) for field in StatInput.__dataclass_fields__.keys()})
                    _bind_destination(split_row, ('canonical_stat', split_target), canonical_stats, note='kb_perk_effect_split_routed:free_upgrade_chance_all')
                    _append(out, split_row)
                continue
            if target_stat_id and target_stat_id != 'ranged_enemy_attack_distance':
                _bind_perk_effect_destination(row, target_stat_id, canonical_stats, alias_index)
            _append(out, row)

    # Modules: parse selected modules and surface main stat/substats. Route substats by canonical aliases only.
    for slot_type, selection in account_state.module_presets.get(module_preset, {}).items():
        slot_state = account_state.module_system_state.get(slot_type)
        assist_level = slot_state.assist_level if slot_state else None
        lookup_eff = assist_efficiency_lookup.get(assist_level or -1)
        assist_multiplier_eff = (slot_state.multiplier_cap if slot_state and slot_state.multiplier_cap is not None else lookup_eff) if slot_state else lookup_eff
        assist_substat_eff = (slot_state.substat_cap if slot_state and slot_state.substat_cap is not None else lookup_eff) if slot_state else lookup_eff
        for role, mod_name in [('primary', selection.primary), ('assist', selection.assist)]:
            if not mod_name:
                continue
            mod = account_state.modules_inventory.get(mod_name)
            if mod is None:
                _append(out, StatInput(stat_name=f'{slot_type}::{role}', source_family='module', source_name=mod_name, value=None, value_type='missing_inventory', stage='loadout_resolved', preset_name=module_preset, provenance='IDS::Modules', notes='selected_module_missing_from_inventory_parse'))
                continue
            if mod.stat is not None:
                try:
                    main_value = float(mod.stat)
                except (ValueError, TypeError):
                    main_value = None
                if role == 'assist' and assist_level is not None and assist_multiplier_eff is not None:
                    full_assist_main = _module_main_effect_multiplier(slot_type, mod.rarity, assist_level)
                    if full_assist_main is not None:
                        main_value = 1.0 + (full_assist_main - 1.0) * assist_multiplier_eff
                    elif main_value is not None:
                        main_value = 1.0 + (main_value - 1.0) * assist_multiplier_eff
                unique_rarity = _normalize_module_unique_rarity(str(mod.rarity))
                if role == 'assist' and slot_state and getattr(slot_state, 'rarity_cap', None):
                    unique_rarity = _normalize_module_unique_rarity(str(slot_state.rarity_cap))
                unique_lookup = module_unique_effect_values.get((_slug(mod_name), unique_rarity))
                unique_value = unique_lookup[0] if unique_lookup is not None else main_value
                unique_measure = unique_lookup[1] if unique_lookup is not None else ''
                if role == 'assist' and unique_value is not None and assist_multiplier_eff is not None:
                    if unique_measure == 'count':
                        # Quantity-style assist unique contributions use slot rarity-cap values and remain integer-like.
                        # Do not multiply the count by assist efficiency; the weaker assist variant is represented by
                        # the assist rarity cap itself (e.g. Epic Orbital Augment -> 2 electrons).
                        unique_value = float(int(unique_value))
                    else:
                        unique_value = unique_value * assist_multiplier_eff
                unique_value_type = 'multiplier_display' if unique_measure == 'multiplier' else ('pct' if unique_measure == 'pct' else ('count' if unique_measure == 'count' else ('duration_seconds' if unique_measure == 'seconds' else ('resolved_value' if unique_measure in {'m', 'raw'} else ('multiplier_display' if unique_value is not None else 'raw_text')))))
                row = StatInput(stat_name=f'{mod_name}::main', source_family='module', source_name=mod_name, value=main_value if main_value is not None else mod.stat, value_type='multiplier_display' if main_value is not None else 'raw_text', stage='loadout_resolved', preset_name=module_preset, provenance='IDS::Modules', notes=(f'module_{role}_main_effect' + (f':assist_multiplier_eff={assist_multiplier_eff}' if role == 'assist' and assist_multiplier_eff is not None else '')))
                base_contributor = {
                    'cannon': 'module__cannon__damage__pct',
                    'armor': 'module__armor__health__pct',
                    'generator': 'module__generator__coins_kill_bonus__pct',
                    'core': 'module__core__ultimate_weapon_damage__pct',
                }.get(slot_type)
                unique_contributor = _mapping_lookup_for_family_name(family_slug_index, 'module', mod_name)
                if base_contributor and main_value is not None:
                    _bind_kb_fields(row, base_contributor, mapping_index, canonical_stats)
                    _set_row_field(row, 'notes', (row.notes or '') + ':kb_module_base_routed')
                    _set_row_field(row, 'contributor_id', _make_instance_contributor_id(row.contributor_id, source_name=mod_name, role=role))
                elif unique_contributor and main_value is not None:
                    _bind_kb_fields(row, unique_contributor, mapping_index, canonical_stats)
                    _set_row_field(row, 'notes', (row.notes or '') + ':kb_module_unique_routed')
                    _set_row_field(row, 'contributor_id', _make_instance_contributor_id(row.contributor_id, source_name=mod_name, role=role))
                _append(out, row)
                if mod_name == 'Sharp Fortitude' and main_value is not None and role == 'primary':
                    for unique_contributor_id, note in [
                        ('module__armor__wall_health__pct', 'kb_manual_sharp_fortitude_wall_hp_routed'),
                        ('module__armor__wall_regen__pct', 'kb_manual_sharp_fortitude_wall_regen_routed'),
                    ]:
                        sf_row = StatInput(
                            stat_name=f'{mod_name}::unique',
                            source_family='module',
                            source_name=mod_name,
                            value=unique_value,
                            value_type=unique_value_type,
                            stage='loadout_resolved',
                            preset_name=preset,
                            provenance='IDS::Modules',
                            notes=f'module_{role}_unique_effect:{note}',
                        )
                        _bind_kb_fields(sf_row, unique_contributor_id, mapping_index, canonical_stats)
                        _set_row_field(sf_row, 'contributor_id', _make_instance_contributor_id(sf_row.contributor_id, source_name=mod_name, role=role, sub_name='unique'))
                        _append(out, sf_row)
                if unique_contributor and main_value is not None and base_contributor and unique_contributor != base_contributor:
                    unique_row = StatInput(stat_name=f'{mod_name}::unique', source_family='module', source_name=mod_name, value=unique_value, value_type=unique_value_type, stage='loadout_resolved', preset_name=module_preset, provenance='IDS::Modules', notes=f'module_{role}_unique_effect')
                    _bind_kb_fields(unique_row, unique_contributor, mapping_index, canonical_stats)
                    _set_row_field(unique_row, 'contributor_id', _make_instance_contributor_id(unique_row.contributor_id, source_name=mod_name, role=role, sub_name='unique'))
                    _append(out, unique_row)
                if mod_name == 'Singularity Harness' and unique_value is not None:
                    sh_row = StatInput(stat_name=f'{mod_name}::unique', source_family='module', source_name=mod_name, value=unique_value, value_type=unique_value_type, stage='loadout_resolved', preset_name=module_preset, provenance='IDS::Modules', notes=f'module_{role}_unique_effect:kb_manual_singularity_harness_bot_range_routed')
                    _bind_destination(sh_row, ('mechanic_param', 'bot.global.range_bonus_m'), canonical_stats, note='kb_manual_singularity_harness_bot_range_routed')
                    _set_row_field(sh_row, 'contributor_id', _make_instance_contributor_id('module__generator__singularity_harness__bot_range_bonus_m', source_name=mod_name, role=role, sub_name='bot_range_bonus'))
                    _append(out, sh_row)
            for sub in mod.substats:
                numeric = None
                value_type = 'raw_text'
                display = str(sub.value or '').strip()
                token = str(sub.raw_token or '').strip()
                if not display and not token:
                    continue
                try:
                    kb_unit = module_substat_units.get(sub.name, '')
                    rarity_key = str(mod.rarity).strip()
                    exact = module_substat_values.get((slot_type.lower(), sub.name, rarity_key))
                    exact_unit = exact[1] if exact is not None else ''
                    if '%' in display:
                        numeric = float(display.replace('+', '').replace('%', '').replace('?', '').strip())
                        if role == 'assist' and assist_substat_eff is not None:
                            numeric = numeric * assist_substat_eff
                        value_type = 'percent_display'
                    elif 'x' in display.lower():
                        numeric = float(display.replace('+', '').replace('x', '').replace('X', '').strip())
                        if role == 'assist' and assist_substat_eff is not None:
                            numeric = numeric * assist_substat_eff
                        value_type = 'multiplier_display'
                    else:
                        base = token or display
                        numeric = float(str(base).replace('+', '').replace('m', '').replace('s', '').replace('?', '').strip())
                        if role == 'assist' and assist_substat_eff is not None:
                            numeric = numeric * assist_substat_eff
                        inferred_unit = kb_unit or exact_unit
                        if inferred_unit == 'percent':
                            value_type = 'percent_display'
                        else:
                            value_type = 'resolved_value'
                except ValueError:
                    pass
                row = StatInput(stat_name=sub.name, source_family='module_substat', source_name=mod_name, value=numeric if numeric is not None else sub.value, value_type=value_type if numeric is not None else 'raw_text', stage='loadout_resolved', preset_name=module_preset, provenance='IDS::Modules', notes=(f'module_{role}_substat' + (f':assist_substat_eff={assist_substat_eff}' if role == 'assist' and assist_substat_eff is not None else '')))
                destination = MODULE_SUBSTAT_NAME_TO_DESTINATION.get(_slug(sub.name))
                if destination is not None:
                    _bind_destination(row, destination, canonical_stats, note=f'kb_exact_routed_module_substat_{role}')
                else:
                    _bind_alias_destination(row, sub.name, alias_index, canonical_stats, note=f'kb_alias_routed_module_substat_{role}')
                if row.contributor_id:
                    _set_row_field(row, 'contributor_id', _make_instance_contributor_id(row.contributor_id, source_name=mod_name, role=role, sub_name=sub.name))
                _append(out, row)

    return [row for row in out if row_in_state_mode(row, state_mode)]
