from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

import yaml

from tower_sim.run.problem_spec import (
    BossStatsSpec,
    BossSurvivabilitySpec,
    ProblemSpec,
    ScenarioSpec,
    SkipRampSpec,
    StatInputSpec,
    TowerDefenseSpec,
)
from tower_sim.registry.stat_registry import Phase


def load_problem_spec(path: Path) -> ProblemSpec:
    data = _load_raw_spec(path)
    if not isinstance(data, dict):
        raise ValueError("Problem spec must be a mapping at the top level.")
    return _parse_problem_spec(data)


def parse_problem_spec_data(data: Mapping[str, Any]) -> ProblemSpec:
    if not isinstance(data, Mapping):
        raise ValueError("Problem spec must be a mapping at the top level.")
    return _parse_problem_spec(data)


def _load_raw_spec(path: Path) -> Any:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return json.loads(path.read_text())
    if suffix in {".yaml", ".yml"}:
        return yaml.safe_load(path.read_text())
    raise ValueError(f"Unsupported spec extension: {path.suffix}")


def _parse_problem_spec(data: Mapping[str, Any]) -> ProblemSpec:
    _validate_keys(data, required={"scenario", "stat_inputs"}, optional={"evaluator"})
    scenario = _parse_scenario(data["scenario"])
    stat_inputs = _parse_stat_inputs(data["stat_inputs"])
    evaluator = str(data.get("evaluator", "max_wave"))
    return ProblemSpec(scenario=scenario, stat_inputs=stat_inputs, evaluator=evaluator)


def _parse_scenario(data: Mapping[str, Any]) -> ScenarioSpec:
    _validate_keys(
        data,
        required={"mode", "tier"},
        optional={
            "league",
            "wave",
            "wave_damage_tier",
            "eals_ramp",
            "ehls_ramp",
            "boss_survivability",
            "perk_timeline_path",
        },
    )
    mode = str(data["mode"])
    tier = int(data["tier"])
    league = _optional_str(data.get("league"))
    wave = int(data.get("wave", 1))
    wave_damage_tier = _optional_str(data.get("wave_damage_tier"))
    eals_ramp = _parse_skip_ramp(data.get("eals_ramp"), "eals_ramp")
    ehls_ramp = _parse_skip_ramp(data.get("ehls_ramp"), "ehls_ramp")
    boss_survivability = _parse_boss_survivability(data.get("boss_survivability"))
    perk_timeline_path = _optional_str(data.get("perk_timeline_path"))
    return ScenarioSpec(
        mode=mode,
        tier=tier,
        league=league,
        wave=wave,
        wave_damage_tier=wave_damage_tier,
        eals_ramp=eals_ramp,
        ehls_ramp=ehls_ramp,
        boss_survivability=boss_survivability,
        perk_timeline_path=perk_timeline_path,
    )


def _parse_skip_ramp(data: Any, field_name: str) -> Optional[SkipRampSpec]:
    if data is None:
        return None
    if not isinstance(data, Mapping):
        raise ValueError(f"{field_name} must be a mapping.")
    _validate_keys(data, required={"start", "end"}, optional={"ramp_waves"})
    return SkipRampSpec(
        start=float(data["start"]),
        end=float(data["end"]),
        ramp_waves=int(data.get("ramp_waves", 1000)),
    )


def _parse_stat_inputs(data: Any) -> List[StatInputSpec]:
    if not isinstance(data, list):
        raise ValueError("stat_inputs must be a list of mappings.")
    return [_parse_stat_input(item) for item in data]


def _parse_stat_input(data: Mapping[str, Any]) -> StatInputSpec:
    _validate_keys(
        data,
        required={"stat_id", "phase"},
        optional={
            "base_value",
            "loadout_delta",
            "enhancement_multiplier",
            "tier_rule_delta",
            "tier_rule_multiplier",
            "derived_value",
            "provenance",
        },
    )
    phase = _parse_phase(data["phase"])
    return StatInputSpec(
        stat_id=str(data["stat_id"]),
        phase=phase,
        base_value=_optional_float(data.get("base_value")),
        loadout_delta=_optional_float(data.get("loadout_delta")),
        enhancement_multiplier=_optional_float(data.get("enhancement_multiplier")),
        tier_rule_delta=_optional_float(data.get("tier_rule_delta")),
        tier_rule_multiplier=_optional_float(data.get("tier_rule_multiplier")),
        derived_value=_optional_float(data.get("derived_value")),
        provenance=_optional_str(data.get("provenance")),
    )


def _parse_boss_survivability(data: Any) -> Optional[BossSurvivabilitySpec]:
    if data is None:
        return None
    if not isinstance(data, Mapping):
        raise ValueError("boss_survivability must be a mapping.")
    _validate_keys(data, required={"boss", "tower", "combat_params", "bc_params"}, optional=set())
    boss = _parse_boss_stats(data["boss"])
    tower = _parse_tower_defense(data["tower"])
    combat_params = _parse_params(data["combat_params"], "combat_params")
    bc_params = _parse_params(data["bc_params"], "bc_params")
    return BossSurvivabilitySpec(
        boss=boss,
        tower=tower,
        combat_params=combat_params,
        bc_params=bc_params,
    )


def _parse_boss_stats(data: Any) -> BossStatsSpec:
    if not isinstance(data, Mapping):
        raise ValueError("boss stats must be a mapping.")
    _validate_keys(
        data,
        required={"hp", "attack", "attack_interval", "enrage_mult"},
        optional=set(),
    )
    return BossStatsSpec(
        hp=float(data["hp"]),
        attack=float(data["attack"]),
        attack_interval=float(data["attack_interval"]),
        enrage_mult=float(data["enrage_mult"]),
    )


def _parse_tower_defense(data: Any) -> TowerDefenseSpec:
    if not isinstance(data, Mapping):
        raise ValueError("tower defense must be a mapping.")
    _validate_keys(
        data,
        required={"dr_frac", "regen_per_sec", "shields"},
        optional=set(),
    )
    return TowerDefenseSpec(
        dr_frac=float(data["dr_frac"]),
        regen_per_sec=float(data["regen_per_sec"]),
        shields=float(data["shields"]),
    )


def _parse_params(data: Any, name: str) -> Dict[str, Any]:
    if not isinstance(data, Mapping):
        raise ValueError(f"{name} must be a mapping.")
    if any(key.strip() == "" for key in data.keys() if isinstance(key, str)):
        raise ValueError(f"{name} contains empty keys.")
    return dict(data)


def _parse_phase(value: Any) -> Phase:
    if not isinstance(value, str):
        raise ValueError(f"Phase must be a string, got {value!r}")
    for phase in Phase:
        if phase.value == value:
            return phase
    raise ValueError(f"Unknown phase: {value!r}")


def _optional_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    return float(value)


def _optional_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    return str(value)


def _validate_keys(
    data: Mapping[str, Any],
    *,
    required: Iterable[str],
    optional: Iterable[str],
) -> None:
    if not isinstance(data, Mapping):
        raise ValueError("Expected mapping in spec loader.")
    required_set = set(required)
    optional_set = set(optional)
    missing = required_set - set(data.keys())
    if missing:
        raise ValueError(f"Missing required keys: {sorted(missing)}")
    unknown = set(data.keys()) - required_set - optional_set
    if unknown:
        raise ValueError(f"Unknown keys in spec: {sorted(unknown)}")


def spec_as_dict(spec: ProblemSpec) -> Dict[str, Any]:
    return asdict(spec)
