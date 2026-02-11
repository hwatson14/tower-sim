from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from tower_sim.loaders.table_paths import resolve_table_path
from typing import Dict, Iterable, List, Optional, Tuple

from tower_sim.engines.stat_engine import StatInput
from tower_sim.engines.stat_input_compiler import compile_full_stat_inputs, compile_workshop_values_at_wave
from tower_sim.engines.stat_snapshots import AtWaveSnapshot, StatSnapshotError, build_at_wave_snapshot
from tower_sim.loaders.perk_timeline_loader import apply_perk_timeline_to_inputs
from tower_sim.loaders.bc_heat_loader import HeatDataError, load_tournament_heat_table
from tower_sim.libs.wave_damage_strict import EnemyWaveDamageLib
from tower_sim.registry.combat_stat_contract import required_combat_stat_ids
from tower_sim.registry.stat_registry import Phase
from tower_sim.engines.wave_engine import RunWaveState, SkipRamp, make_wave_state


TOURNAMENT_HEAT_BC_IDS: Tuple[str, ...] = (
    "death_ray_resistance:",
    "knockback_resistance:",
    "orb_resistance:",
    "plasma_cannon_resistance:",
    "thorns_resistance:",
)

TOURNAMENT_HEAT_BC_TO_STATS: Dict[str, Tuple[str, ...]] = {
    "orb_resistance:": ("orb_damage_mult",),
    "death_ray_resistance:": ("death_ray_damage_mult",),
    "thorns_resistance:": ("thorns_damage_mult",),
    "plasma_cannon_resistance:": ("plasma_cannon_damage_mult",),
    "knockback_resistance:": ("knockback_mult",),
}

@dataclass(frozen=True)
class CombatStatContribution:
    stat_id: str
    source: str
    value: float


@dataclass(frozen=True)
class CombatStatSnapshot:
    values: Dict[str, float]
    contributions: Dict[str, List[CombatStatContribution]]


@dataclass(frozen=True)
class CanonicalStatInputBuild:
    stat_inputs: List[StatInput]
    blocked_core_overrides: List[str]
    invalid_stat_inputs: List[str]
    missing_required_stat_inputs: List[str]
    compiled_missing: List[str]
    core_stat_override_policy: str


def build_canonical_stat_inputs(
    *,
    problem_spec,
    ids_snapshot,
    registry,
) -> CanonicalStatInputBuild:
    spec_inputs = [spec.to_stat_input() for spec in problem_spec.stat_inputs]
    compiled = compile_full_stat_inputs(ids_snapshot)
    strict_core_stat_overrides = not bool(
        getattr(problem_spec.scenario, "allow_core_stat_overrides", False)
    )
    merged_inputs, blocked = _merge_stat_inputs(
        spec_inputs,
        compiled.stat_inputs,
        strict_core_stat_overrides=strict_core_stat_overrides,
    )
    filtered_inputs, invalid = _filter_known_stat_inputs(merged_inputs, registry)
    missing_required = _missing_required_stat_inputs(filtered_inputs)
    return CanonicalStatInputBuild(
        stat_inputs=filtered_inputs,
        blocked_core_overrides=blocked,
        invalid_stat_inputs=invalid,
        missing_required_stat_inputs=missing_required,
        compiled_missing=sorted(compiled.missing),
        core_stat_override_policy=(
            "strict_fail_closed" if strict_core_stat_overrides else "explicit_override_mode"
        ),
    )


def derive_canonical_combat_snapshot(
    engine_result,
    wave_snapshot: Optional[AtWaveSnapshot],
) -> Tuple[Optional[CombatStatSnapshot], List[str]]:
    """Derive canonical combat survivability stats for MAX_WAVE consumption.

    Source precedence is deterministic and fail-closed:
    1) at-wave snapshot value if present
    2) START_OF_RUN statbook value
    3) missing -> fail-closed marker
    """

    if engine_result is None:
        return None, ["stat_engine"]
    start_stats = engine_result.run_stats.get(Phase.START_OF_RUN)
    if start_stats is None:
        return None, ["start_stats"]

    snapshot_values = wave_snapshot.values if wave_snapshot is not None else {}
    values: Dict[str, float] = {}
    contributions: Dict[str, List[CombatStatContribution]] = {}
    missing: List[str] = []

    for stat_id in required_combat_stat_ids():
        from_wave = snapshot_values.get(stat_id)
        if from_wave is not None:
            value = float(from_wave)
            values[stat_id] = value
            contributions[stat_id] = [
                CombatStatContribution(
                    stat_id=stat_id,
                    source="at_wave_snapshot",
                    value=value,
                )
            ]
            continue

        from_start = start_stats.values.get(stat_id)
        if from_start is not None:
            value = float(from_start)
            values[stat_id] = value
            contributions[stat_id] = [
                CombatStatContribution(
                    stat_id=stat_id,
                    source="start_of_run",
                    value=value,
                )
            ]
            continue

        missing.append(stat_id)

    if missing:
        return None, [f"stat:{stat_id}" for stat_id in missing]

    return CombatStatSnapshot(values=values, contributions=contributions), []


def _missing_required_stat_inputs(stat_inputs: Iterable[StatInput]) -> List[str]:
    required = {
        "eals_pct",
        "ehls_pct",
        "orb_damage_mult",
        "death_ray_damage_mult",
        "plasma_cannon_damage_mult",
        "knockback_mult",
        *required_combat_stat_ids(),
    }
    present = {stat_input.stat_id for stat_input in stat_inputs}
    return [f"stat_input:{stat_id}" for stat_id in sorted(required - present)]


def _merge_stat_inputs(
    spec_inputs: List[StatInput],
    compiled_inputs: List[StatInput],
    *,
    strict_core_stat_overrides: bool,
) -> Tuple[List[StatInput], List[str]]:
    existing = {(item.stat_id, item.phase): item for item in spec_inputs}
    merged = list(spec_inputs)
    blocked: List[str] = []
    for item in compiled_inputs:
        key = (item.stat_id, item.phase)
        if key in existing:
            if (
                strict_core_stat_overrides
                and item.phase == Phase.START_OF_RUN
                and item.stat_id in required_combat_stat_ids()
            ):
                blocked.append(f"{item.stat_id}@{item.phase.value}")
            continue
        merged.append(item)
    return merged, sorted(set(blocked))


def _filter_known_stat_inputs(
    stat_inputs: List[StatInput],
    registry,
) -> Tuple[List[StatInput], List[str]]:
    filtered: List[StatInput] = []
    invalid: List[str] = []
    for item in stat_inputs:
        try:
            registry.validate_stat_id(item.stat_id)
        except Exception:  # noqa: BLE001
            invalid.append(item.stat_id)
            continue
        filtered.append(item)
    return filtered, sorted(set(invalid))




@lru_cache(maxsize=1)
def cached_tournament_heat_table(scale_path: str, registry_path: str):
    return load_tournament_heat_table(Path(scale_path), Path(registry_path))


def resolve_wave_state_for_wave(
    scenario,
    wave: int,
) -> Tuple[Optional[RunWaveState], List[str]]:
    missing: List[str] = []
    if scenario.eals_ramp is None:
        missing.append("skip_ramp:eals")
    if scenario.ehls_ramp is None:
        missing.append("skip_ramp:ehls")
    if missing:
        return None, missing
    eals = SkipRamp(
        start=scenario.eals_ramp.start,
        end=scenario.eals_ramp.end,
        ramp_waves=scenario.eals_ramp.ramp_waves,
    )
    ehls = SkipRamp(
        start=scenario.ehls_ramp.start,
        end=scenario.ehls_ramp.end,
        ramp_waves=scenario.ehls_ramp.ramp_waves,
    )
    return make_wave_state(wave, eals, ehls), []


def build_canonical_wave_row(
    problem_spec,
    registry,
    *,
    wave: int,
) -> Tuple[Optional[Dict[str, object]], List[str]]:
    wave_state, wave_missing = resolve_wave_state_for_wave(problem_spec.scenario, wave)
    if wave_missing or wave_state is None:
        return None, wave_missing

    row: Dict[str, object] = {
        "wave": int(wave),
        "enemy_attack_wave": int(wave_state.W_attack),
        "enemy_health_wave": int(wave_state.W_health),
    }

    if problem_spec.scenario.mode != "tournament":
        return row, []

    table_path = resolve_table_path("heat_scale_long")
    registry_path = resolve_table_path("heat_bc_registry")
    try:
        table = cached_tournament_heat_table(str(table_path), str(registry_path))
    except (HeatDataError, FileNotFoundError):
        return None, ["heat_tables"]

    league = (problem_spec.scenario.league or "").strip().lower()
    if not league:
        return None, ["heat_league"]

    bc_values: Dict[str, float] = {}
    heat_magnitudes: Dict[str, float] = {}
    missing_heat_ids: List[str] = []
    for bc_id in TOURNAMENT_HEAT_BC_IDS:
        try:
            value = table.value_at(league=league, wave_actual=wave, bc_id=bc_id).value_num
        except HeatDataError:
            missing_heat_ids.append(f"heat_bc_value:{bc_id}")
            continue
        bc_values[bc_id] = float(value)
        for stat_id in TOURNAMENT_HEAT_BC_TO_STATS[bc_id]:
            registry.validate_stat_id(stat_id)
            heat_magnitudes[stat_id] = float(value)

    if missing_heat_ids:
        return None, sorted(set(missing_heat_ids))

    row["battle_conditions"] = bc_values
    row["heat_magnitudes"] = heat_magnitudes
    return row, []


def resolve_canonical_heat_magnitudes(
    *,
    problem_spec,
    registry,
    wave: int,
) -> Tuple[Optional[Dict[str, float]], Optional[Dict[str, object]], List[str]]:
    scenario = problem_spec.scenario
    if scenario.mode != "tournament":
        return None, None, []
    if scenario.league is None:
        return None, None, ["heat_league"]
    row, row_missing = build_canonical_wave_row(problem_spec, registry, wave=wave)
    if row_missing or row is None:
        return None, row, row_missing
    return row.get("heat_magnitudes"), row, []


__all__ = [
    "CanonicalStatInputBuild",
    "TOURNAMENT_HEAT_BC_IDS",
    "TOURNAMENT_HEAT_BC_TO_STATS",
    "CombatStatContribution",
    "CombatStatSnapshot",
    "build_canonical_stat_inputs",
    "resolve_wave_state_for_wave",
    "resolve_canonical_heat_magnitudes",
    "cached_tournament_heat_table",
    "build_canonical_wave_row",
    "wave_state_from_row",
    "build_canonical_wave_snapshot",
    "canonical_stat_inputs_for_wave",
    "default_wave_damage_tier",
    "derive_canonical_combat_snapshot",
    "resolve_canonical_wave_damage",
    "resolve_canonical_wave_damage_for_attack_wave",
    "validate_boss_survivability_spec",
]


def canonical_stat_inputs_for_wave(
    *,
    registry,
    stat_inputs: List[StatInput],
    scenario,
    wave: int,
) -> Tuple[List[StatInput], Dict[str, object]]:
    if scenario.mode == "tournament":
        return stat_inputs, {"enabled": False, "reason": "tournament_mode"}
    return apply_perk_timeline_to_inputs(
        registry=registry,
        stat_inputs=stat_inputs,
        perk_timeline_path=getattr(scenario, "perk_timeline_path", None),
        current_wave=wave,
    )




def wave_state_from_row(wave_row: Dict[str, object]) -> RunWaveState:
    if (
        "wave" not in wave_row
        or "enemy_attack_wave" not in wave_row
        or "enemy_health_wave" not in wave_row
    ):
        raise StatSnapshotError(
            "Wave row missing required keys: wave/enemy_attack_wave/enemy_health_wave"
        )
    return RunWaveState(
        W_actual=int(wave_row["wave"]),
        W_attack=int(wave_row["enemy_attack_wave"]),
        W_health=int(wave_row["enemy_health_wave"]),
    )


def build_canonical_wave_snapshot(
    *,
    ids_snapshot,
    wave: int,
    stat_inputs: List[StatInput],
    engine_result,
    registry,
    tier_rules,
    run_context,
    heat_magnitudes,
    wave_row: Dict[str, object],
):
    workshop_at_wave, workshop_missing = compile_workshop_values_at_wave(ids_snapshot, wave=wave)
    if workshop_missing:
        return None, workshop_missing
    snapshot = build_at_wave_snapshot(
        stat_inputs=stat_inputs,
        engine_result=engine_result,
        registry=registry,
        tier_rules=tier_rules,
        battle_conditions=None,
        wave_state=wave_state_from_row(wave_row),
        wave=wave,
        run_context=run_context,
        heat_magnitudes=heat_magnitudes,
        per_wave_overrides=workshop_at_wave,
    )
    return snapshot, []

def resolve_canonical_wave_damage(
    *,
    problem_spec,
    wave_state,
) -> Tuple[Optional[float], List[str], Dict[str, object]]:
    diagnostics: Dict[str, object] = {}
    missing: List[str] = []
    scenario = problem_spec.scenario
    wave_tier = scenario.wave_damage_tier
    if wave_tier is None:
        wave_tier = default_wave_damage_tier(scenario)
    if wave_tier is None:
        missing.append("wave_damage_tier")
        return None, missing, diagnostics

    lib = EnemyWaveDamageLib.from_repo_tables()
    wave = scenario.wave if wave_state is None else wave_state.W_attack
    try:
        damage = lib.wave_damage(wave_tier, wave)
    except KeyError as exc:
        missing.append("wave_damage_table")
        diagnostics["wave_damage_error"] = str(exc)
        return None, missing, diagnostics
    diagnostics["wave_damage_tier"] = wave_tier
    diagnostics["wave_damage_wave"] = wave
    diagnostics["wave_damage"] = damage
    return damage, missing, diagnostics


def default_wave_damage_tier(scenario) -> Optional[str]:
    if scenario.mode == "farming":
        return f"Tier {scenario.tier}"
    if scenario.league:
        return scenario.league
    return None


def validate_boss_survivability_spec(problem_spec: object) -> Tuple[List[str], Dict[str, str]]:
    diagnostics: Dict[str, str] = {}
    missing: List[str] = []
    spec = getattr(problem_spec.scenario, "boss_survivability", None)
    if spec is None:
        missing.append("boss_survivability")
        return missing, diagnostics

    boss = spec.boss
    tower = spec.tower
    if boss.hp is not None and boss.hp <= 0:
        diagnostics["boss_hp"] = "non_positive"
    if boss.attack <= 0:
        diagnostics["boss_attack"] = "non_positive"
    if boss.attack_interval <= 0:
        diagnostics["boss_attack_interval"] = "non_positive"
    if boss.enrage_mult is not None and boss.enrage_mult <= 0:
        diagnostics["boss_enrage_mult"] = "non_positive"
    if tower.dr_frac < 0 or tower.dr_frac > 1:
        diagnostics["tower_dr_frac"] = "out_of_range"
    if tower.regen_per_sec < 0:
        diagnostics["tower_regen_per_sec"] = "negative"
    if tower.shields < 0:
        diagnostics["tower_shields"] = "negative"

    if diagnostics:
        missing.append("boss_survivability_invalid")
    return missing, diagnostics


def resolve_canonical_wave_damage_for_attack_wave(
    *,
    problem_spec,
    attack_wave: int,
) -> Tuple[Optional[float], List[str]]:
    missing: List[str] = []
    scenario = problem_spec.scenario
    wave_tier = scenario.wave_damage_tier
    if wave_tier is None:
        wave_tier = default_wave_damage_tier(scenario)
    if wave_tier is None:
        missing.append("wave_damage_tier")
        return None, missing
    lib = EnemyWaveDamageLib.from_repo_tables()
    try:
        damage = lib.wave_damage(wave_tier, int(attack_wave))
    except KeyError:
        missing.append("wave_damage_table")
        return None, missing
    return damage, []
