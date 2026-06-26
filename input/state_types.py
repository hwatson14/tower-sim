from __future__ import annotations

from dataclasses import dataclass, field, asdict
from functools import lru_cache
from math import isfinite
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

import yaml

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_INPUT_CONTRACT_PATH = ROOT / 'kb' / 'global-rules' / 'contracts' / 'scenario-runtime-inputs.yaml'
_YAML_LOADER = getattr(yaml, 'CSafeLoader', yaml.SafeLoader)


@dataclass(frozen=True)
class TableSnapshot:
    header: List[str]
    rows: List[List[str]]


@dataclass(frozen=True)
class WorkshopEntrySnapshot:
    name: str
    unlocked: Optional[str]
    preset_levels: Dict[str, Optional[int]]
    preset_values: Dict[str, Optional[float]]
    max_level: Optional[int]
    category: Optional[str]


@dataclass(frozen=True)
class CardSnapshot:
    name: str
    level: Optional[int]
    mastery_unlocked: Optional[bool]
    mastery_lab_level: Optional[int]


@dataclass(frozen=True)
class UltimateWeaponSnapshot:
    name: str
    unlocked: Optional[str]
    track_levels: List[str]
    track_values: List[Optional[float]] = field(default_factory=list)


@dataclass(frozen=True)
class UwTrackSnapshot:
    uw_name: str
    track_name: str
    level: Optional[int]
    level_token: str
    resolved_value: Optional[float]


@dataclass(frozen=True)
class UwPlusTrackSnapshot:
    uw_name: str
    plus_track_name: str
    current_state: str
    display_token: str


@dataclass(frozen=True)
class BotUpgradeSnapshot:
    bot_name: str
    track_name: str
    level: Optional[int]
    resolved_value: Optional[float]
    resolved_unit: Optional[str]
    source: Optional[str] = None
    value_kind: Optional[str] = None


@dataclass(frozen=True)
class GuardianTrackSnapshot:
    guardian_name: str
    track_name: str
    level: Optional[int]
    resolved_value: Optional[float]
    resolved_unit: Optional[str]


@dataclass(frozen=True)
class WorkshopEnhancementSnapshot:
    name: str
    current_multiplier: Optional[float]
    preset_levels: Dict[str, Optional[int]]
    max_level: Optional[int]
    category: Optional[str]


@dataclass(frozen=True)
class ModuleSubstat:
    name: str
    value: Optional[str]
    raw_token: Optional[str] = None


@dataclass(frozen=True)
class ModuleSnapshot:
    name: str
    slot_type: str
    rarity: Optional[str]
    level: Optional[int]
    stat: Optional[str]
    substats: List[ModuleSubstat] = field(default_factory=list)


@dataclass(frozen=True)
class ModulePresetSelection:
    primary: Optional[str]
    assist: Optional[str]


@dataclass(frozen=True)
class PerkSelection:
    perk_id: str
    picks: int = 1


@dataclass(frozen=True)
class ModuleSystemState:
    slot_type: str
    assist_unlocked: Optional[bool]
    assist_level: Optional[int]
    rarity_cap: Optional[str]
    multiplier_cap: Optional[float]
    substat_cap: Optional[float]


@dataclass(frozen=True)
class ScenarioProjectionState:
    max_workshop: bool = False
    projected_perks: bool = False
    death_wave_health: bool = False
    berserker_damage_bonus: bool = False
    second_wind_mastery_regen: bool = False

    def to_debug_dict(self) -> Dict[str, bool]:
        return {
            'max_workshop': bool(self.max_workshop),
            'projected_perks': bool(self.projected_perks),
            'death_wave_health': bool(self.death_wave_health),
            'berserker_damage_bonus': bool(self.berserker_damage_bonus),
            'second_wind_mastery_regen': bool(self.second_wind_mastery_regen),
        }


@dataclass(frozen=True)
class AccountState:
    ids_path: Path
    labs: Dict[str, Optional[int]]
    lab_adjusters: Dict[str, Dict[str, int]]
    workshop: Dict[str, WorkshopEntrySnapshot]
    workshop_enhancements: TableSnapshot
    workshop_enhancement_tracks: Dict[str, WorkshopEnhancementSnapshot]
    ultimate_weapons: Dict[str, UltimateWeaponSnapshot]
    uw_tracks: Dict[str, List[UwTrackSnapshot]]
    uw_plus_tracks: Dict[str, UwPlusTrackSnapshot]
    relics: Dict[str, Optional[float]]
    vault: Dict[str, Any]
    bots: List[str]
    bot_unlocks: Dict[str, bool]
    bot_upgrades: Dict[str, Dict[str, int]]
    bot_upgrade_tracks: Dict[str, List[BotUpgradeSnapshot]]
    guardians: TableSnapshot
    guardian_tracks: Dict[str, List[GuardianTrackSnapshot]]
    player_meta: Dict[str, Optional[str]]
    tier_progression_waves: Dict[str, int]
    highest_tier_unlocked_number: Optional[int]
    highest_tier_unlocked_label: Optional[str]
    theme_song_coin_multiplier: Optional[float]
    cards_inventory: Dict[str, CardSnapshot]
    card_slots_unlocked: Optional[int]
    card_presets: Dict[str, List[str]]
    module_system_state: Dict[str, ModuleSystemState]
    module_presets: Dict[str, Dict[str, ModulePresetSelection]]
    modules_inventory: Dict[str, ModuleSnapshot]
    perk_presets: Dict[str, List[PerkSelection]]
    perk_preset_namespace_class: str
    active_perk_preset: Optional[str]
    active_card_preset: str
    active_module_preset: str
    default_preset: str
    raw_sections: Dict[str, List[List[str]]]
    dissonance_pbs_by_tier: Dict[str, Dict[str, int]] = field(default_factory=dict)
    manual_override_sources: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@lru_cache(maxsize=1)
def _load_runtime_input_contract() -> Dict[str, Dict[str, Any]]:
    raw = yaml.load(RUNTIME_INPUT_CONTRACT_PATH.read_text(encoding='utf-8'), Loader=_YAML_LOADER) or {}
    fields = raw.get('fields') or {}
    if not isinstance(fields, dict) or not fields:
        raise ValueError('Scenario runtime input contract must define non-empty fields.')
    out: Dict[str, Dict[str, Any]] = {}
    for field_name, spec in fields.items():
        if not isinstance(spec, dict):
            raise ValueError(f'Scenario runtime input field {field_name} must be a mapping.')
        aliases = spec.get('aliases') or []
        if not aliases:
            raise ValueError(f'Scenario runtime input field {field_name} must declare aliases.')
        out[field_name] = {
            'aliases': tuple(str(alias) for alias in aliases),
            'min': spec.get('min'),
            'min_exclusive': spec.get('min_exclusive'),
            'max': spec.get('max'),
            'max_exclusive': spec.get('max_exclusive'),
        }
    return out


@dataclass(frozen=True)
class ScenarioRuntimeInputs:
    orb_boss_hit_pct: Optional[float] = None
    orb_boss_total_damage_pct: Optional[float] = None
    orb_boss_hit_count: Optional[float] = None
    electron_total_damage_pct: Optional[float] = None
    electron_hit_count: Optional[float] = None
    orb_boss_hits_per_second: Optional[float] = None
    electron_hits_per_second: Optional[float] = None
    boss_time_to_contact_seconds: Optional[float] = None
    boss_hit_interval_seconds: Optional[float] = None
    effective_damage_reduction_pct: Optional[float] = None
    incoming_damage_multiplier: Optional[float] = None
    boss_wave_pressure_factor: Optional[float] = None
    approve_boss_wave_empirical_pressure_transform: Optional[float] = None
    flame_bot_damage_reduction_pct: Optional[float] = None
    flame_bot_boss_hit_chance_pct: Optional[float] = None
    flame_bot_duration_seconds: Optional[float] = None
    flame_bot_cooldown_seconds: Optional[float] = None
    defense_field_damage_reduction_pct: Optional[float] = None
    defense_field_duration_seconds: Optional[float] = None
    defense_field_cooldown_seconds: Optional[float] = None
    black_hole_damage_reduction_pct: Optional[float] = None
    black_hole_duration_seconds: Optional[float] = None
    black_hole_cooldown_seconds: Optional[float] = None
    pbh_encounter_uptime_fraction: Optional[float] = None
    boss_applicable_damage_per_second: Optional[float] = None
    boss_applicable_damage_factor: Optional[float] = None
    boss_edamage_target_share: Optional[float] = None
    boss_edamage_cadence_uptime_factor: Optional[float] = None
    boss_edamage_reliability_factor: Optional[float] = None
    boss_edamage_semantic_normalizer: Optional[float] = None
    death_wave_health_max_multiplier: Optional[float] = None
    death_wave_health_max_wave: Optional[float] = None
    boss_wave_interval: Optional[float] = None
    enemy_level_skip_reduction_pp: Optional[float] = None
    enemy_level_skip_decay_pct: Optional[float] = None
    enemy_level_skip_decay_interval_waves: Optional[float] = None
    enemy_level_skip_decay_start_wave: Optional[float] = None
    tower_damage_decay_pct: Optional[float] = None
    tower_damage_decay_start_wave: Optional[float] = None
    tower_health_decay_pct: Optional[float] = None
    tower_health_decay_start_wave: Optional[float] = None
    fleet_terminal_max_wave: Optional[float] = None
    elite_terminal_max_wave: Optional[float] = None
    protector_terminal_max_wave: Optional[float] = None
    armored_terminal_max_wave: Optional[float] = None
    boss_terminal_max_wave: Optional[float] = None

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> 'ScenarioRuntimeInputs':
        contract = _load_runtime_input_contract()
        values: Dict[str, Optional[float]] = {}
        for field_name, spec in contract.items():
            values[field_name] = _first_from_aliases(raw=raw, field_name=field_name, aliases=spec['aliases'], spec=spec)
        return cls(**values)

    def to_debug_dict(self) -> Dict[str, float]:
        out: Dict[str, float] = {}
        for key in _load_runtime_input_contract().keys():
            value = getattr(self, key)
            if value is not None:
                out[key] = float(value)
        return out


def projection_state_for_mode(state_mode: str) -> ScenarioProjectionState:
    normalized = str(state_mode or 'start_of_run').strip()
    if normalized == 'max_progression':
        return ScenarioProjectionState(
            max_workshop=True,
            projected_perks=True,
            death_wave_health=True,
            berserker_damage_bonus=True,
            second_wind_mastery_regen=True,
        )
    return ScenarioProjectionState()


def _first_from_aliases(*, raw: Mapping[str, Any], field_name: str, aliases: tuple[str, ...], spec: Mapping[str, Any]) -> Optional[float]:
    for key in aliases:
        if key in raw and raw[key] is not None:
            return _coerce_float(field_name=field_name, source_key=key, value=raw[key], spec=spec)
    return None


def _coerce_float(*, field_name: str, source_key: str, value: Any, spec: Mapping[str, Any]) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'Scenario runtime input {source_key} must be numeric.') from exc
    if not isfinite(out):
        raise ValueError(f'Scenario runtime input {source_key} must be finite.')
    min_value = spec.get('min')
    if min_value is not None and out < float(min_value):
        raise ValueError(f'Scenario runtime input {source_key} must be >= {float(min_value)}.')
    min_exclusive = spec.get('min_exclusive')
    if min_exclusive is not None and out <= float(min_exclusive):
        raise ValueError(f'Scenario runtime input {source_key} must be > {float(min_exclusive)}.')
    max_value = spec.get('max')
    if max_value is not None and out > float(max_value):
        raise ValueError(f'Scenario runtime input {source_key} must be <= {float(max_value)}.')
    max_exclusive = spec.get('max_exclusive')
    if max_exclusive is not None and out >= float(max_exclusive):
        raise ValueError(f'Scenario runtime input {source_key} must be < {float(max_exclusive)}.')
    return out

