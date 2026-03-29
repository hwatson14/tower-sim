from __future__ import annotations

import csv
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional, Tuple

import yaml

from qe.contracts import (
    to_legacy_destination,
    to_legacy_surface_id,
    to_v2_destination,
    to_v2_surface_id,
)
from qe.models import StatInput  # T3B: authority transferred to qe.models

ROOT = Path(__file__).resolve().parents[1]
KB = ROOT / 'kb'
KB_CONTRACTS = KB / 'global-rules' / 'contracts'
KB_TABLES = KB / 'global-rules' / 'tables'
KB_MAPPINGS_PATH = KB_CONTRACTS / 'contributor-mappings-full.yaml'
KB_CANONICAL_STATS_PATH = KB_CONTRACTS / 'canonical-stats.yaml'
KB_ALIASES_PATH = KB_CONTRACTS / 'name-aliases.yaml'
RELIC_REGISTRY_PATH = KB_TABLES / 'relic-input-registry.csv'

CARD_EFFECT_REGISTRY_PATH = KB / 'cards' / 'tables' / 'card-effect-registry.csv'
THEME_SONG_REGISTRY_PATH = KB_TABLES / 'theme-song-input-registry.csv'
LAB_APPLICATION_REGISTRY_PATH = KB / 'labs' / 'tables' / 'lab-application-registry.csv'

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
        'parser_drop_rows': set(raw.get('parser_drop_rows') or []),
        'account_metadata_rows': set(raw.get('account_metadata_rows') or []),
        'capability_policy_rows': set(raw.get('capability_policy_rows') or []),
        'governed_numeric_rows': set(raw.get('governed_numeric_rows') or []),
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


def routing_class_for_lab_name(name: str) -> str | None:
    policy = compiler_routing_policy()
    if name in policy['parser_drop_rows']:
        return 'parser_drop'
    if name in policy['account_metadata_rows']:
        return 'account_metadata'
    if name in policy['capability_policy_rows']:
        return 'capability_policy'
    if name in policy['governed_numeric_rows']:
        return 'governed_numeric'
    return None


@lru_cache(maxsize=1)
def load_card_effect_targets() -> Dict[str, Tuple[str, str]]:
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
def load_lab_application_registry() -> Dict[str, Dict[str, str]]:
    out: Dict[str, Dict[str, str]] = {}
    with LAB_APPLICATION_REGISTRY_PATH.open(newline='') as f:
        for row in csv.DictReader(f):
            name = str(row['lab_primary_name']).strip()
            out[name] = row
            out[slug_text(name)] = row
    return out


@lru_cache(maxsize=1)
def load_theme_song_registry() -> Dict[str, Tuple[str, str, str]]:
    out: Dict[str, Tuple[str, str, str]] = {}
    if not THEME_SONG_REGISTRY_PATH.exists():
        return out
    with THEME_SONG_REGISTRY_PATH.open(newline='', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            cid = (row.get('contributor_id') or '').strip()
            if cid:
                out[cid] = (
                    (row.get('destination_object_type') or '').strip(),
                    (row.get('destination_id') or '').strip(),
                    (row.get('resolver_id') or '').strip(),
                )
    return out

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

PARSER_DROP_ROWS = compiler_routing_policy()['parser_drop_rows']

ACCOUNT_METADATA_ROWS = compiler_routing_policy()['account_metadata_rows']

CAPABILITY_POLICY_ROWS = compiler_routing_policy()['capability_policy_rows']

GOVERNED_NUMERIC_ROWS = compiler_routing_policy()['governed_numeric_rows']

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

# Source-backed workshop and lab formula callables: loaded from KB table.
# Source: kb/global-rules/tables/workshop-formula-params-canonical.csv
from qe.kb_surfaces import WORKSHOP_FORMULA_VALUES, LAB_FORMULA_VALUES  # noqa: E402

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
    'waves.intro_sprint_runtime': ('runtime_mechanic_param', 'cards.intro_sprint.waves'),
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

def slug_text(text: str) -> str:
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
def compiler_routing_indexes() -> Tuple[Dict[str, Dict[str, str]], Dict[str, Dict[str, str]], Dict[str, Tuple[str, str]], Dict[str, str], Dict[Tuple[str, str], str]]:
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
                family_slug_index[(family, slug_text(parts[2].replace('_', ' ')))] = row['contributor_id']
                if family == 'module' and len(parts) >= 4:
                    family_slug_index[(family, slug_text(parts[1].replace('_', ' ') + ' ' + parts[2].replace('_', ' ')))] = row['contributor_id']

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
        alias_index[slug_text(row['alias'])] = (row['resolves_to_type'], row['resolves_to_id'])

    relic_index: Dict[str, str] = {}
    with RELIC_REGISTRY_PATH.open(newline='') as f:
        for row in csv.DictReader(f):
            contributor_id = row['contributor_id']
            parts = contributor_id.split('__')
            if len(parts) >= 4:
                key = slug_text(parts[2].replace('_', ' '))
                relic_index[key] = contributor_id
    return mapping_index, canonical_stats, alias_index, relic_index, family_slug_index


def uw_contributor_id(uw_name: str, track_name: str) -> str | None:
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

def mapping_lookup_for_family_name(family_slug_index: Dict[Tuple[str, str], str], family: str, name: str) -> Optional[str]:
    slug = slug_text(name)
    return family_slug_index.get((family, slug))



def _set_row_field(row: StatInput, field_name: str, value) -> None:
    object.__setattr__(row, field_name, value)


def bind_kb_fields(row: StatInput, contributor_id: str, mapping_index: Dict[str, Dict[str, str]], canonical_stats: Dict[str, Dict[str, str]]) -> None:
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


def bind_alias_destination(row: StatInput, alias_text: str, alias_index: Dict[str, Tuple[str, str]], canonical_stats: Dict[str, Dict[str, str]], *, note: str) -> None:
    slug = slug_text(alias_text)
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


def bind_destination(row: StatInput, destination: Tuple[str, str], canonical_stats: Dict[str, Dict[str, str]], *, note: str) -> None:
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



def bind_perk_effect_destination(row: StatInput, target_stat_id: str, canonical_stats: Dict[str, Dict[str, str]], alias_index: Dict[str, Tuple[str, str]]) -> None:
    destination = PERK_TARGET_DESTINATION_OVERRIDES.get(target_stat_id)
    if destination is not None:
        bind_destination(row, destination, canonical_stats, note=f'kb_perk_effect_routed:{target_stat_id}')
        return
    if target_stat_id in canonical_stats:
        bind_destination(row, ('canonical_stat', target_stat_id), canonical_stats, note=f'kb_perk_effect_routed:{target_stat_id}')
        return
    bind_alias_destination(row, target_stat_id.replace('_', ' '), alias_index, canonical_stats, note='kb_alias_routed_perk_target')


__all__ = [
    'compiler_routing_policy',
    'compiler_routing_indexes',
    'slug_text',
    'mapping_lookup_for_family_name',
    'bind_kb_fields',
    'bind_alias_destination',
    'bind_destination',
    'bind_perk_effect_destination',
    'uw_contributor_id',
    'routing_class_for_lab_name',
    'PARSER_DROP_ROWS',
    'ACCOUNT_METADATA_ROWS',
    'CAPABILITY_POLICY_ROWS',
    'GOVERNED_NUMERIC_ROWS',
    'UW_MECHANIC_DESTINATION_OVERRIDES',
    'UW_CONTRIBUTOR_OVERRIDES',
    'GUARDIAN_DESTINATION_OVERRIDES',
    'VAULT_BOOLEAN_FLAGS',
    'RELIC_ALIAS_OVERRIDES',
    'VAULT_NUMERIC_OVERRIDES',
    '_UW_LAB_DIRECT_DESTINATION',
    'WORKSHOP_IDS_TO_CONTRIBUTOR',
    'LAB_IDS_TO_CONTRIBUTOR',
    'CARD_TARGET_SURFACE_TO_DESTINATION',
    'LAB_APPLICATION_TARGET_TO_DESTINATION',
    'CARD_NAME_FALLBACK_DESTINATION',
    'MODULE_SUBSTAT_NAME_TO_DESTINATION',
    'ENHANCEMENT_ALIAS_OVERRIDES',
    'RELIC_CONTRIBUTOR_OVERRIDES',
    'ENHANCEMENT_CONTRIBUTOR_OVERRIDES',
    'PERK_TARGET_DESTINATION_OVERRIDES',
    'to_v2_surface_id',
    'to_legacy_surface_id',
    'to_v2_destination',
    'to_legacy_destination',
]
