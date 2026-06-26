"""Scenario projection simulator. AUTHORITY (T4).

Owns: mode_id, BC selection, heat/env overlays, boss cadence, resistances,
      environment overlays, and other world/scenario assumptions.
Extracted from: engine/scenario_engine.py (T4).

KB sources:
  - kb/tournaments/tables/tier-battle-conditions.csv
  - kb/tournaments/tables/battle-condition-magnitudes.csv
  - kb/tournaments/tables/battle-condition-behavior-reference.csv
  - kb/tournaments/tables/battle-condition-reduction-lab.csv
  - kb/tournaments/tables/battle-condition-group-{2,3,4}-reduction-lab.csv
  - kb/tournaments/tables/note-derived-battle-condition-groups.csv
  - kb/enemies/tables/boss-hit-interval.csv
  - kb/enemies/tables/wiki-advanced-analysis-spawn-rate-wave-thresholds.csv
  - kb/enemies/tables/wiki-verified-elite-spawn-thresholds.csv
  - kb/enemies/tables/wiki-verified-fleet-spawn-thresholds.csv
  - kb/enemies/tables/wiki-verified-boss-summary.csv
  - kb/combat/contracts/enemy-class-interaction-matrix.csv

Ownership boundary (split architecture):
  Owns: mode_id, BC selection, heat/env overlays, boss cadence, resistances,
        environment overlays, and other world/scenario assumptions.
  Does not own: cooldown math, uptime, overlap, sync, shared-cycle timing,
        canonical stat recomputation, workshop state, wave progression, boss TTK.
"""
from __future__ import annotations

import csv
import math
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from qe.contracts import normalize_surface_id_to_contract
from qe.models import StatInput, StatRow

ROOT = Path(__file__).resolve().parents[1]


def normalize_els_reduction_to_fraction(value: float | None) -> float:
    """Return an absolute EALS/EHLS probability subtraction.

    KB tables store late-tier reductions as fractions of 1, while older
    user-facing inputs may provide display percentage points. Tournament
    magnitudes are signed penalties, so normalize them by magnitude.
    """
    v = abs(float(value or 0.0))
    if v > 1.0:
        return v / 100.0
    return v


def _canon(destination_id: str) -> str:
    return normalize_surface_id_to_contract(f'canonical_stat::{destination_id}')


def _mech(destination_id: str) -> str:
    return normalize_surface_id_to_contract(f'mechanic_param::{destination_id}')


def _runtime(destination_id: str) -> str:
    return normalize_surface_id_to_contract(f'runtime_mechanic_param::{destination_id}')


def _env(destination_id: str) -> str:
    return normalize_surface_id_to_contract(f'environment_param::{destination_id}')


# ═══════════════════════════════════════════════════════════════════════
#  Data models
# ═══════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class ScenarioConfig:
    """Fixed-for-run scenario selection inputs."""
    mode_id: str                               # farming | tournament | milestone
    tier: int = 14                             # farming/milestone active tier (14-21)
    league: Optional[str] = None               # tournament league
    tournament_wave: int = 0                   # tournament wave for BC magnitude lookup
    current_wave: int = 0                      # current/target wave for late-run overlays such as v28 Overheat

    # BC reduction lab levels (4 groups per KB note-derived-battle-condition-groups.csv)
    #   Group 1: PC/orb/thorns/DR/knockback resistance + more_bosses
    #   Group 2: armored_enemies, enemy_speed, more_enemies, enemy_attack_speed
    #   Group 3: enemy ultimates
    #   Group 4: UW durations, death_defy_down, energy_shields_down, enemy_level_skip
    bc_reduction_group1_pct: float = 0.0
    bc_reduction_group2_pct: float = 0.0
    bc_reduction_group3_pct: float = 0.0
    bc_reduction_group4_pct: float = 0.0

    # UW base params from stat engine (mechanic_param surfaces)
    bh_base_duration_s: float = 0.0
    bh_base_cooldown_s: float = 0.0
    cf_base_duration_s: float = 0.0
    cf_base_cooldown_s: float = 0.0
    cf_slow_pct: float = 0.0
    # CF damage reduction: separate lab mechanic from slow.
    # KB: unlock lab grants base 10%, Reduction % lab (30 levels) adds 10.5%→25%.
    # Wiki: "Reduces damage taken by the tower when chrono field is active."
    # Wiki: "The reduction is taken on the enemy damage after defense absolute."
    # Total = base + lab value. Stat engine should eventually emit this directly.
    cf_damage_reduction_pct: float = 0.0
    gt_base_duration_s: float = 0.0
    gt_base_cooldown_s: float = 0.0

    # UW perk adds from stat engine (runtime_mechanic_param surfaces)
    bh_perk_duration_add_s: float = 0.0
    bh_perk_cooldown_add_s: float = 0.0
    cf_perk_duration_add_s: float = 0.0

    # Environment params from stat engine
    env_enemy_damage_multiplier: float = 1.0
    env_boss_health_multiplier: float = 1.0
    env_boss_speed_multiplier: float = 1.0

    # Bot base params from stat engine
    bot_amplify_duration_s: float = 0.0
    bot_amplify_cooldown_s: float = 0.0
    bot_golden_duration_s: float = 0.0
    bot_golden_cooldown_s: float = 0.0
    bot_thunder_duration_s: float = 0.0
    bot_thunder_cooldown_s: float = 0.0
    # Flame bot: no duration, activation-based permanent debuff
    bot_flame_cooldown_s: float = 0.0
    bot_flame_damage_reduction_pct: float = 0.0

    # Orb/electron raw params from stat engine
    tower_orb_count: int = 0
    tower_orb_speed_rpm: float = 0.0
    electron_count: int = 0


@dataclass
class ScenarioSurfaces:
    """All emitted fixed-for-run scenario-adjusted effect surfaces."""
    mode_id: str = ""

    # ── BC resistance multipliers (group 1) ──
    # KB: tier-battle-conditions.csv / battle-condition-magnitudes.csv
    # Effective = after BC reduction group 1 lab applied.
    bc_plasma_cannon_resistance: float = 1.0
    bc_orb_resistance: float = 1.0
    bc_thorns_resistance: float = 1.0
    bc_death_ray_resistance: float = 1.0
    bc_knockback_resistance: float = 1.0

    # ── BC environmental modifiers (group 2) ──
    # KB: "Enemy attack speed is increased by x%"
    # KB: "Enemies move x% faster"
    # KB: "x% more enemies spawn"
    bc_enemy_attack_speed_increase_pct: float = 0.0
    bc_enemy_speed_increase_pct: float = 0.0
    bc_more_enemies_pct: float = 0.0
    bc_armored_enemies_blocked_hits: float = 0.0

    # ── BC UW/utility penalties (group 4) ──
    # KB: "Reduce durations of CF, GT, Poison Swamp, and BH by Xs"
    bc_uw_duration_reduction_s: float = 0.0
    bc_enemy_level_skip_reduction_pp: float = 0.0
    # KB: death_defy_down reduces death defy chance by magnitude (negative pp)
    # KB: energy_shields_down reduces energy shield effectiveness by magnitude (fraction)
    bc_death_defy_down_pp: float = 0.0
    bc_energy_shields_down_fraction: float = 0.0

    # v28 Overheat late-run limiter
    overheat_visible_after_any_tier_wave: int = 4500
    overheat_start_wave: int = 0
    overheat_active: bool = False
    overheat_enemy_skip_decay_active: bool = False
    overheat_damage_decay_active: bool = False
    overheat_health_decay_active: bool = False
    overheat_more_fleets_active: bool = False
    overheat_more_elites_active: bool = False
    overheat_damage_decay_steps: int = 0
    overheat_health_decay_steps: int = 0
    overheat_extra_fleets: int = 0
    overheat_extra_elites: int = 0

    # ── Boss wave interval ──
    # KB: wiki-verified-boss-summary.csv: every 10 waves default
    # KB: tier-battle-conditions.csv: more_bosses overrides per tier
    # KB: battle-condition-magnitudes.csv: more_bosses = 6 in tournament
    boss_wave_interval: int = 10

    # ── Boss hit interval (adjusted by enemy_attack_speed BC) ──
    # KB: boss-hit-interval.csv: 2.0s base
    # Formula: base_interval / (1 + bc_enemy_attack_speed_increase_pct / 100)
    boss_hit_interval_seconds: float = 2.0

    # ── Boss class inherent resistances (not BC-driven) ──
    # KB: enemy-class-interaction-matrix.csv
    boss_thorns_effectiveness: float = 0.5       # KB: 0.5_effectiveness, HIGH
    boss_electron_effectiveness: float = 0.25    # KB: 0.25_effectiveness, HIGH

    # ── Environment overlays (pass-through from stat engine) ──
    env_enemy_damage_multiplier: float = 1.0
    env_boss_health_multiplier: float = 1.0
    env_boss_speed_multiplier: float = 1.0

    # ── Timing-owned fields intentionally excluded ──
    # Effective durations/cooldowns, uptime fractions, overlap/sync surfaces,
    # and uptime-weighted average effects now belong to simulators/timing.py.

    # ── Orb/electron raw params (pass-through for progression engine) ──
    # BLOCKED: no governed cadence surface. Progression engine consumes raw params.
    tower_orb_count: int = 0
    tower_orb_speed_rpm: float = 0.0
    orb_boss_hit_rate_status: str = "BLOCKED__no_governed_cadence_surface"
    electron_count: int = 0
    electron_boss_hit_rate_status: str = "BLOCKED__no_governed_cadence_surface"

    # ── Deferred BC surfaces (not emitted, documented for completeness) ──
    # Group 3 enemy ultimates: boss_ultimate, protector_ultimate, tank_ultimate,
    #   fast_ultimate, basic_ultimate variants, scatter/ray/vampire_ultimate.
    #   Not boss-v1-relevant for wall survival model. Deferred to v2.
    # mass_enforcement: T17+ tier BC, mostly MISSING in KB. Deferred.
    deferred_bc_note: str = "group3_enemy_ultimates_and_mass_enforcement_deferred_to_v2"
    unsupported_terminal_pressures: tuple[str, ...] = field(default_factory=tuple)

    # ── Diagnostics ──
    bc_source: str = ""
    surfaces_status: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}


@dataclass(frozen=True)
class FarmingThroughputSurfaces:
    target_farming_wave: float = 0.0
    waves_per_run_effective: float = 0.0
    runs_per_day_effective: float = 0.0
    waves_per_day_effective: float = 0.0
    bosses_per_day_effective: float = 0.0


# ═══════════════════════════════════════════════════════════════════════
#  KB loaders
# ═══════════════════════════════════════════════════════════════════════


@lru_cache(maxsize=1)
def _load_tier_battle_conditions() -> Dict[int, Dict[str, Dict[str, str]]]:
    """Returns: {tier: {bc_id: {kind, value, unit}}}"""
    path = ROOT / "kb" / "tournaments" / "tables" / "tier-battle-conditions.csv"
    out: Dict[int, Dict[str, Dict[str, str]]] = {}
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            tier = int(row["tier"])
            out.setdefault(tier, {})[row["bc"]] = {
                "kind": row["kind"], "value": row["value"], "unit": row["unit"],
            }
    return out


@lru_cache(maxsize=1)
def _load_tournament_bc_magnitudes() -> Dict[str, Dict[int, float]]:
    """Returns: {bc_id: {wave: magnitude}}. Uniform across leagues."""
    path = ROOT / "kb" / "tournaments" / "tables" / "battle-condition-magnitudes.csv"
    out: Dict[str, Dict[int, float]] = {}
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            out.setdefault(row["bc_id"], {})[int(row["wave"])] = float(row["magnitude"])
    return out


@lru_cache(maxsize=1)
def _load_tournament_league_rules() -> Dict[str, Dict[str, str]]:
    """Returns normalized Champion/Legend tournament league rules."""
    path = ROOT / "kb" / "tournaments" / "tables" / "tournament-league-rules.csv"
    out: Dict[str, Dict[str, str]] = {}
    with path.open(newline="") as f:
        rows = (line for line in f if line.strip() and not line.lstrip().startswith("#"))
        for row in csv.DictReader(rows):
            league = str(row.get("league") or "").strip().lower()
            if league:
                out[league] = dict(row)
    return out


def tournament_tier_for_league(league: object) -> int | None:
    normalized = str(league or "").strip().lower()
    if normalized.endswith("s"):
        normalized = normalized[:-1]
    row = _load_tournament_league_rules().get(normalized)
    if not row:
        return None
    try:
        tier = int(float(row.get("tier_number") or 0))
    except (TypeError, ValueError):
        return None
    return tier if tier > 0 else None


@lru_cache(maxsize=1)
def _load_boss_enemy_class_resistances() -> Dict[str, float]:
    """Returns: {mechanic: effectiveness_fraction} for boss class."""
    path = ROOT / "kb" / "combat" / "contracts" / "enemy-class-interaction-matrix.csv"
    out: Dict[str, float] = {}
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            if row.get("enemy_class") == "boss":
                behavior = row.get("behavior", "")
                if behavior.endswith("_effectiveness"):
                    try:
                        out[row["mechanic"]] = float(behavior.replace("_effectiveness", ""))
                    except ValueError:
                        pass
    return out


def _row_float(row: Mapping[str, str], key: str, default: float = 0.0) -> float:
    raw = str(row.get(key) or "").replace(",", "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _row_int(row: Mapping[str, str], key: str, default: int = 0) -> int:
    return int(round(_row_float(row, key, float(default))))


@lru_cache(maxsize=1)
def _load_elite_spawn_thresholds() -> tuple[dict[str, object], ...]:
    path = ROOT / "kb" / "enemies" / "tables" / "wiki-verified-elite-spawn-thresholds.csv"
    rows: list[dict[str, object]] = []
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            rows.append(
                {
                    "spawn_slot": str(row.get("spawn_slot") or ""),
                    "displayed_chance_pct": _row_float(row, "displayed_chance_pct"),
                    "tier_waves": {
                        tier: _row_int(row, f"t{tier}_wave")
                        for tier in range(1, 22)
                    },
                    "source_page": str(row.get("source_page") or ""),
                    "source_status": str(row.get("source_status") or ""),
                }
            )
    return tuple(rows)


@lru_cache(maxsize=1)
def _load_fleet_spawn_thresholds() -> dict[int, dict[str, object]]:
    path = ROOT / "kb" / "enemies" / "tables" / "wiki-verified-fleet-spawn-thresholds.csv"
    rows: dict[int, dict[str, object]] = {}
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            tier = _row_int(row, "tier")
            if tier <= 0:
                continue
            rows[tier] = {
                "tier": tier,
                "regular_first_spawn_wave": _row_int(row, "regular_first_spawn_wave"),
                "regular_frequency_waves": _row_int(row, "regular_frequency_waves"),
                "regular_count_per_event": _row_float(row, "regular_count_per_event"),
                "bonus_first_spawn_wave": _row_int(row, "bonus_first_spawn_wave"),
                "bonus_frequency_waves": _row_int(row, "bonus_frequency_waves"),
                "bonus_count_per_event": _row_float(row, "bonus_count_per_event"),
                "source_page": str(row.get("source_page") or ""),
                "source_status": str(row.get("source_status") or ""),
                "notes": str(row.get("notes") or ""),
            }
    return rows


@lru_cache(maxsize=1)
def _load_normal_spawn_rate_wave_thresholds() -> tuple[dict[str, object], ...]:
    path = (
        ROOT
        / "kb"
        / "enemies"
        / "tables"
        / "wiki-advanced-analysis-spawn-rate-wave-thresholds.csv"
    )
    rows: list[dict[str, object]] = []
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            rows.append(
                {
                    "spawn_rate_display": _row_float(row, "spawn_rate_display"),
                    "standard_wave": _row_int(row, "standard_wave"),
                    "source_page": str(row.get("source_page") or ""),
                    "source_image": str(row.get("source_image") or ""),
                    "source_status": str(row.get("source_status") or ""),
                    "notes": str(row.get("notes") or ""),
                }
            )
    return tuple(sorted(rows, key=lambda row: int(row["standard_wave"])))


def _rounded_spawn_rate_threshold_wave(
    *,
    standard_wave: int,
    wave_accelerator_spawn_rate_acceleration: float,
) -> int:
    multiplier = max(1.0, float(wave_accelerator_spawn_rate_acceleration or 1.0))
    return max(1, int(math.floor((float(standard_wave) / multiplier) + 0.5)))


def normal_spawn_rate_pressure_driver(
    *,
    wave: int,
    enemy_balance_spawn_multiplier: float = 1.0,
    wave_accelerator_spawn_rate_acceleration: float = 1.0,
    more_enemies_pct: float = 0.0,
) -> dict[str, object]:
    """Return source-backed normal spawn-rate band, not a terminal formula."""
    wave_number = max(0, int(wave))
    accelerator = max(1.0, float(wave_accelerator_spawn_rate_acceleration or 1.0))
    effective_standard_wave = float(wave_number) * accelerator
    rows = _load_normal_spawn_rate_wave_thresholds()
    selected: dict[str, object] | None = None
    next_row: dict[str, object] | None = None
    for row in rows:
        if float(row["standard_wave"]) <= effective_standard_wave:
            selected = dict(row)
            continue
        next_row = dict(row)
        break
    if selected is None and rows:
        selected = dict(rows[0])
    spawn_rate = float((selected or {}).get("spawn_rate_display") or 0.0)
    enemy_balance = max(0.0, float(enemy_balance_spawn_multiplier or 1.0))
    more_enemies_multiplier = 1.0 + (max(0.0, float(more_enemies_pct or 0.0)) / 100.0)
    pressure_index = spawn_rate * enemy_balance * more_enemies_multiplier
    threshold_standard_wave = int((selected or {}).get("standard_wave") or 0)
    next_standard_wave = int((next_row or {}).get("standard_wave") or 0)
    return {
        "wave": wave_number,
        "displayed_spawn_rate": spawn_rate,
        "threshold_standard_wave": threshold_standard_wave or None,
        "threshold_actual_wave_with_wave_accelerator": (
            _rounded_spawn_rate_threshold_wave(
                standard_wave=threshold_standard_wave,
                wave_accelerator_spawn_rate_acceleration=accelerator,
            )
            if threshold_standard_wave
            else None
        ),
        "next_displayed_spawn_rate": (
            float(next_row.get("spawn_rate_display")) if next_row else None
        ),
        "next_threshold_standard_wave": next_standard_wave or None,
        "next_threshold_actual_wave_with_wave_accelerator": (
            _rounded_spawn_rate_threshold_wave(
                standard_wave=next_standard_wave,
                wave_accelerator_spawn_rate_acceleration=accelerator,
            )
            if next_standard_wave
            else None
        ),
        "effective_standard_wave_with_wave_accelerator": effective_standard_wave,
        "wave_accelerator_spawn_rate_acceleration": accelerator,
        "enemy_balance_spawn_multiplier": enemy_balance,
        "bc_more_enemies_pct": max(0.0, float(more_enemies_pct or 0.0)),
        "normal_spawn_rate_pressure_index": pressure_index,
        "source_tables": [
            "kb/enemies/tables/wiki-advanced-analysis-spawn-rate-wave-thresholds.csv",
        ],
        "source_status": (selected or {}).get("source_status") or "missing_source_row",
        "formula_status": "source_spawn_rate_curve_available_terminal_pressure_transform_missing",
    }


def _elite_spawn_band(*, tier: int, wave: int, spawn_slot: str) -> dict[str, object]:
    tier_number = min(21, max(1, int(tier)))
    wave_number = max(0, int(wave))
    candidates: list[dict[str, object]] = []
    for row in _load_elite_spawn_thresholds():
        if row["spawn_slot"] != spawn_slot:
            continue
        threshold = int(dict(row["tier_waves"]).get(tier_number, 0) or 0)
        if threshold <= wave_number:
            candidates.append({**row, "threshold_wave": threshold})
    if not candidates:
        return {
            "spawn_slot": spawn_slot,
            "displayed_chance_pct": 0.0,
            "threshold_wave": None,
            "source_status": "not_yet_active_for_wave",
        }
    selected = max(
        candidates,
        key=lambda row: (float(row["displayed_chance_pct"]), int(row["threshold_wave"] or 0)),
    )
    return {
        "spawn_slot": spawn_slot,
        "displayed_chance_pct": float(selected["displayed_chance_pct"]),
        "threshold_wave": int(selected["threshold_wave"]),
        "source_page": selected.get("source_page"),
        "source_status": selected.get("source_status"),
    }


def elite_spawn_pressure_driver(
    *,
    tier: int,
    wave: int,
    enemy_balance_mastery_double_elite_chance_pct: float = 0.0,
) -> dict[str, object]:
    """Return source-backed elite pressure-driver bands, not a terminal formula."""
    single = _elite_spawn_band(tier=tier, wave=wave, spawn_slot="single")
    double = _elite_spawn_band(tier=tier, wave=wave, spawn_slot="double")
    mastery_pct = max(0.0, float(enemy_balance_mastery_double_elite_chance_pct or 0.0))
    pressure_index_pct = (
        float(single.get("displayed_chance_pct") or 0.0)
        + float(double.get("displayed_chance_pct") or 0.0)
        + mastery_pct
    )
    return {
        "tier": int(tier),
        "wave": int(wave),
        "single_elite_displayed_chance_pct": single.get("displayed_chance_pct"),
        "single_elite_threshold_wave": single.get("threshold_wave"),
        "double_elite_displayed_chance_pct": double.get("displayed_chance_pct"),
        "double_elite_threshold_wave": double.get("threshold_wave"),
        "enemy_balance_mastery_double_elite_chance_pct": mastery_pct,
        "elite_pressure_index_pct": pressure_index_pct,
        "source_tables": ["kb/enemies/tables/wiki-verified-elite-spawn-thresholds.csv"],
        "formula_status": "source_spawn_curve_available_terminal_pressure_transform_missing",
    }


def _fleet_component_pressure(
    *,
    wave: int,
    first_spawn_wave: int,
    frequency_waves: int,
    count_per_event: float,
) -> dict[str, object]:
    related_enemy_group_min = 10.0
    related_enemy_group_max = 14.0
    related_enemy_group_expected = (related_enemy_group_min + related_enemy_group_max) / 2.0
    wave_number = max(0, int(wave))
    first = int(first_spawn_wave or 0)
    frequency = int(frequency_waves or 0)
    count = max(0.0, float(count_per_event or 0.0))
    active = first > 0 and frequency > 0 and wave_number >= first
    events_elapsed = ((wave_number - first) // frequency) + 1 if active else 0
    events_per_wave = count / float(frequency) if active else 0.0
    return {
        "active": bool(active),
        "first_spawn_wave": first or None,
        "frequency_waves": frequency or None,
        "count_per_event": count,
        "events_elapsed_by_wave": int(events_elapsed),
        "events_per_wave_pressure": events_per_wave,
        "related_enemy_group_count_min": related_enemy_group_min,
        "related_enemy_group_count_max": related_enemy_group_max,
        "related_enemy_group_expected_count": related_enemy_group_expected,
        "related_enemy_group_expected_enemies_per_wave_pressure": (
            events_per_wave * related_enemy_group_expected
        ),
    }


def fleet_spawn_pressure_driver(*, tier: int, wave: int) -> dict[str, object]:
    """Return source-backed fleet schedule pressure, not a terminal formula."""
    tier_number = min(21, max(1, int(tier)))
    row = dict(_load_fleet_spawn_thresholds().get(tier_number) or {})
    regular = _fleet_component_pressure(
        wave=int(wave),
        first_spawn_wave=int(row.get("regular_first_spawn_wave") or 0),
        frequency_waves=int(row.get("regular_frequency_waves") or 0),
        count_per_event=float(row.get("regular_count_per_event") or 0.0),
    )
    bonus = _fleet_component_pressure(
        wave=int(wave),
        first_spawn_wave=int(row.get("bonus_first_spawn_wave") or 0),
        frequency_waves=int(row.get("bonus_frequency_waves") or 0),
        count_per_event=float(row.get("bonus_count_per_event") or 0.0),
    )
    events_per_wave = (
        float(regular["events_per_wave_pressure"])
        + float(bonus["events_per_wave_pressure"])
    )
    related_enemies_per_wave = (
        float(regular["related_enemy_group_expected_enemies_per_wave_pressure"])
        + float(bonus["related_enemy_group_expected_enemies_per_wave_pressure"])
    )
    return {
        "tier": tier_number,
        "wave": int(wave),
        "regular": regular,
        "bonus": bonus,
        "fleet_events_per_wave_pressure": events_per_wave,
        "fleet_related_enemy_group_expected_enemies_per_wave_pressure": related_enemies_per_wave,
        "fleet_related_enemy_group_count_range": [10, 14],
        "source_tables": [
            "kb/enemies/tables/wiki-verified-fleet-spawn-thresholds.csv",
            "kb/enemies/sources/wiki-fleet-and-special-interactions.md",
        ],
        "source_status": row.get("source_status") or "missing_source_row",
        "formula_status": "source_spawn_schedule_available_terminal_pressure_transform_missing",
    }


def non_boss_pressure_driver_probe(
    *,
    tier: int,
    wave: int,
    scenario_surfaces: Mapping[str, object] | None = None,
    enemy_balance_spawn_multiplier: float = 1.0,
    wave_accelerator_spawn_rate_acceleration: float = 1.0,
    enemy_balance_mastery_double_elite_chance_pct: float = 0.0,
) -> dict[str, object]:
    """Expose source-backed pressure drivers without claiming terminal closure."""
    surfaces = dict(scenario_surfaces or {})
    more_enemies_pct = max(0.0, float(surfaces.get("bc_more_enemies_pct") or 0.0))
    spawn_multiplier = (
        max(0.0, float(enemy_balance_spawn_multiplier or 1.0))
        * max(0.0, float(wave_accelerator_spawn_rate_acceleration or 1.0))
        * (1.0 + more_enemies_pct / 100.0)
    )
    normal_spawn_rate = normal_spawn_rate_pressure_driver(
        wave=wave,
        enemy_balance_spawn_multiplier=enemy_balance_spawn_multiplier,
        wave_accelerator_spawn_rate_acceleration=wave_accelerator_spawn_rate_acceleration,
        more_enemies_pct=more_enemies_pct,
    )
    elite = elite_spawn_pressure_driver(
        tier=tier,
        wave=wave,
        enemy_balance_mastery_double_elite_chance_pct=enemy_balance_mastery_double_elite_chance_pct,
    )
    fleet = fleet_spawn_pressure_driver(tier=tier, wave=wave)
    return {
        "tier": int(tier),
        "wave": int(wave),
        "status": "driver_inputs_available_terminal_transform_missing",
        "enemy_spawn_rate_multiplier_pressure": spawn_multiplier,
        "enemy_balance_spawn_multiplier": float(enemy_balance_spawn_multiplier or 1.0),
        "wave_accelerator_spawn_rate_acceleration": float(
            wave_accelerator_spawn_rate_acceleration or 1.0
        ),
        "bc_more_enemies_pct": more_enemies_pct,
        "normal_spawn_rate_pressure": normal_spawn_rate,
        "elite_spawn_pressure": elite,
        "fleet_spawn_pressure": fleet,
        "normal_enemy_spawn_rate_curve_available": True,
        "normal_enemy_spawn_count_curve_available": False,
        "source_backed_curve_coverage": {
            "normal_spawn_rate_curve_by_wave_and_wave_accelerator": True,
            "elite_spawn_curve_by_tier_and_wave": True,
            "fleet_spawn_curve_by_tier_and_wave": True,
            "fleet_related_enemy_group_count_range": True,
            "normal_enemy_spawn_count_curve_by_tier_wave_and_spawn_phase": False,
        },
        "missing_terminal_formula_links": [
            "enemy_balance_spawn_multiplier_to_normal_spawn_pressure_weight",
            "wave_accelerator_mastery_spawn_acceleration_to_spawn_pressure_weight",
            "normal_spawn_rate_value_to_terminal_pressure",
            "elite_spawn_pressure_weight_to_terminal_pressure",
            "fleet_spawn_pressure_weight_to_terminal_pressure",
            "normal_elite_fleet_pressure_composition_rule",
            "pressure_to_terminal_max_wave_or_boss_pressure_factor_transform",
        ],
    }


def non_boss_pressure_driver_source_summary() -> dict[str, object]:
    """Summarize KB-backed pressure-driver source coverage for product diagnostics."""
    normal_spawn_rate_rows = _load_normal_spawn_rate_wave_thresholds()
    elite_rows = _load_elite_spawn_thresholds()
    fleet_rows = _load_fleet_spawn_thresholds()
    return {
        "owner": "simulators.scenario",
        "status": "source_driver_curves_partially_available_terminal_transform_missing",
        "source_backed_curve_coverage": {
            "normal_spawn_rate_curve_by_wave_and_wave_accelerator": bool(
                normal_spawn_rate_rows
            ),
            "elite_spawn_curve_by_tier_and_wave": bool(elite_rows),
            "fleet_spawn_curve_by_tier_and_wave": bool(fleet_rows),
            "fleet_related_enemy_group_count_range": bool(fleet_rows),
            "normal_enemy_spawn_count_curve_by_tier_wave_and_spawn_phase": False,
        },
        "source_table_counts": {
            "normal_spawn_rate_wave_threshold_rows": len(normal_spawn_rate_rows),
            "elite_spawn_threshold_rows": len(elite_rows),
            "fleet_spawn_tier_rows": len(fleet_rows),
        },
        "kb_sources": [
            "enemies.table.wiki_advanced_analysis_spawn_rate_wave_thresholds",
            "enemies.table.wiki_verified_elite_spawn_thresholds",
            "enemies.table.wiki_verified_fleet_spawn_thresholds",
            "enemies.source.wiki_fleet_and_special_interactions",
            "cards.table.card_masteries::Enemy Balance",
            "cards.table.card_masteries::Wave Accelerator",
            "tournaments.table.battle_condition_magnitudes::more_enemies",
        ],
        "missing_terminal_formula_links": [
            "enemy_balance_spawn_multiplier_to_normal_spawn_pressure_weight",
            "wave_accelerator_mastery_spawn_acceleration_to_spawn_pressure_weight",
            "normal_spawn_rate_value_to_terminal_pressure",
            "elite_spawn_pressure_weight_to_terminal_pressure",
            "fleet_spawn_pressure_weight_to_terminal_pressure",
            "normal_elite_fleet_pressure_composition_rule",
            "pressure_to_terminal_max_wave_or_boss_pressure_factor_transform",
        ],
    }


_TIER_BC_UNSUPPORTED_TERMINAL_PRESSURE_IDS: Dict[str, str] = {
    "protectors_ultimate": "protector_ultimate_deferred",
    "boss_ultimate": "boss_ultimate_deferred",
    "basics_ultimate": "basic_ultimate_deferred",
    "fasts_ultimate": "fast_ultimate_deferred",
    "scatter_ultimate": "scatter_ultimate_deferred",
    "ray_ultimate": "ray_ultimate_deferred",
    "vampire_ultimate": "vampire_ultimate_deferred",
    "mass_enforcement": "mass_enforcement_deferred",
}


def _tier_bc_entry_is_present(entry: Dict[str, str] | None) -> bool:
    if not entry:
        return False
    return bool(str(entry.get("kind") or "").strip() or str(entry.get("value") or "").strip())


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def _unsupported_terminal_pressures_for_scenario(
    *,
    config: ScenarioConfig,
    scenario: ScenarioSurfaces,
    tier_bcs: Dict[int, Dict[str, Dict[str, str]]],
    is_tournament: bool,
) -> tuple[str, ...]:
    pressures: list[str] = []
    if scenario.bc_armored_enemies_blocked_hits > 0.0:
        _append_unique(pressures, "armored_enemies_blocked_hits")
    if 0.0 < scenario.bc_knockback_resistance < 1.0:
        _append_unique(pressures, "knockback_resistance_non_boss_pressure")
    if scenario.bc_enemy_speed_increase_pct > 0.0:
        _append_unique(pressures, "enemy_speed_non_boss_pressure")
    if scenario.bc_enemy_attack_speed_increase_pct > 0.0:
        _append_unique(pressures, "enemy_attack_speed_non_boss_pressure")
    if scenario.bc_more_enemies_pct > 0.0:
        _append_unique(pressures, "more_enemies_non_boss_pressure")
    if scenario.bc_death_defy_down_pp != 0.0:
        _append_unique(pressures, "death_defy_down_terminal_pressure")
    if scenario.bc_energy_shields_down_fraction > 0.0:
        _append_unique(pressures, "energy_shields_down_terminal_pressure")
    if scenario.overheat_more_fleets_active:
        _append_unique(pressures, "overheat_more_fleets_terminal_pressure")
    if scenario.overheat_more_elites_active:
        _append_unique(pressures, "overheat_more_elites_terminal_pressure")
    if not is_tournament:
        tier_conditions = tier_bcs.get(int(config.tier), {})
        for bc_id, pressure_id in _TIER_BC_UNSUPPORTED_TERMINAL_PRESSURE_IDS.items():
            if _tier_bc_entry_is_present(tier_conditions.get(bc_id)):
                _append_unique(pressures, pressure_id)
    return tuple(pressures)


# ═══════════════════════════════════════════════════════════════════════
#  BC resolution helpers
# ═══════════════════════════════════════════════════════════════════════


def _interpolate_bc_magnitude(curve: Dict[int, float], wave: int) -> float:
    """Step interpolation: value at highest threshold <= wave."""
    if not curve:
        return 0.0
    active = None
    for w in sorted(curve.keys()):
        if w <= wave:
            active = curve[w]
        else:
            break
    return active if active is not None else curve[min(curve.keys())]


def _reduce_resistance_multiplier(raw: float, reduction_pct: float) -> float:
    """Apply BC reduction lab to a resistance multiplier.

    Penalty = 1 - raw. Reduced penalty = penalty * (1 - reduction/100).
    Effective = 1 - reduced_penalty. Moves toward 1.0.
    """
    if raw >= 1.0:
        return raw
    penalty = 1.0 - raw
    return 1.0 - penalty * max(0.0, 1.0 - reduction_pct / 100.0)


def _reduce_additive_magnitude(raw: float, reduction_pct: float) -> float:
    """Apply BC reduction lab to an additive magnitude.

    Effective = raw * (1 - reduction/100). Moves toward 0.
    """
    return raw * max(0.0, 1.0 - reduction_pct / 100.0)


def _tier_bc_float(tier_bcs: Dict[int, Dict[str, Dict[str, str]]], tier: int,
                    bc_id: str, default: float = 0.0) -> float:
    """Read a tier BC value as float, or default."""
    bc = tier_bcs.get(tier, {}).get(bc_id)
    if bc and bc["value"]:
        try:
            return float(bc["value"])
        except ValueError:
            pass
    return default


# ═══════════════════════════════════════════════════════════════════════
#  Uptime computation
# ═══════════════════════════════════════════════════════════════════════


def _uptime(duration: float, cooldown: float) -> float:
    """uptime = duration / (duration + cooldown), clamped [0, 1]."""
    total = duration + cooldown
    if total <= 0 or duration <= 0:
        return 0.0
    return max(0.0, min(1.0, duration / total))


def overheat_start_wave_for_tier(tier: int) -> int:
    """v28 normal-tier Overheat starts: T1 W15000, T10 W12750, T20 W10250."""
    return max(0, 15000 - 250 * max(0, int(tier) - 1))


def overheat_enemy_skip_decay_schedule() -> Dict[int, float]:
    """Source-owned Skip Decay curve keyed by waves elapsed since Overheat starts."""
    curve = _load_tournament_bc_magnitudes().get("enemy_level_skip", {})
    return {
        max(0, int(wave)): abs(float(value))
        for wave, value in sorted(curve.items())
        if float(value) < 0.0
    }


# ═══════════════════════════════════════════════════════════════════════
#  Stat engine bridge
# ═══════════════════════════════════════════════════════════════════════


def compute_cf_damage_reduction_pct(
    cf_dr_unlock_level: int = 0,
    cf_reduction_pct_level: int = 0,
) -> float:
    """Compute total CF damage reduction % from lab levels.

    KB: canonical-formula-registry.csv:
      - CF Damage Reduction unlock: 1 level, base 10%
      - CF Reduction %: 30 levels, value = 10.50 + ((level-1) * 0.50)
    Total = base (if unlocked) + lab value (if leveled).
    Wiki: "The reduction is taken on the enemy damage after defense absolute."
    """
    base = 10.0 if cf_dr_unlock_level >= 1 else 0.0
    if cf_reduction_pct_level >= 1:
        lab_value = 10.50 + (min(cf_reduction_pct_level, 30) - 1) * 0.50
    else:
        lab_value = 0.0
    return base + lab_value


def config_from_statbook(
    statbook_rows: Dict[str, Any],
    *,
    mode_id: str = "farming",
    tier: int = 14,
    league: Optional[str] = None,
    tournament_wave: int = 0,
    current_wave: int = 0,
    bc_reduction_group1_pct: float = 0.0,
    bc_reduction_group2_pct: float = 0.0,
    bc_reduction_group3_pct: float = 0.0,
    bc_reduction_group4_pct: float = 0.0,
    cf_damage_reduction_pct: Optional[float] = None,
) -> ScenarioConfig:
    """Build a ScenarioConfig from stat engine statbook rows.

    Reads all mechanic_param, runtime_mechanic_param, and environment_param
    surfaces needed by the scenario engine.

    CF damage reduction is auto-read from the stat engine surface
    ``state::uw.chrono_field.damage_reduction_pct`` when resolved.
    The ``cf_damage_reduction_pct`` parameter overrides this if supplied
    (non-None), providing a fallback for stat engine versions that do not
    yet emit the surface.
    """
    def _sid(surface_id: str) -> str:
        return normalize_surface_id_to_contract(surface_id)

    def _val(key: str, default: float = 0.0) -> float:
        row = statbook_rows.get(_sid(key), {})
        v = row.get("final_value")
        if v is None:
            return default
        try:
            return float(v)
        except (TypeError, ValueError):
            return default

    # CF damage reduction: prefer explicit override, then stat engine surface.
    if cf_damage_reduction_pct is not None:
        resolved_cf_dr = cf_damage_reduction_pct
    else:
        resolved_cf_dr = _val(_mech('uw.chrono_field.damage_reduction_pct'))

    return ScenarioConfig(
        mode_id=mode_id,
        tier=tier,
        league=league,
        tournament_wave=tournament_wave,
        current_wave=current_wave,
        bc_reduction_group1_pct=bc_reduction_group1_pct,
        bc_reduction_group2_pct=bc_reduction_group2_pct,
        bc_reduction_group3_pct=bc_reduction_group3_pct,
        bc_reduction_group4_pct=bc_reduction_group4_pct,

        bh_base_duration_s=_val(_mech('uw.black_hole.duration_seconds')),
        bh_base_cooldown_s=_val(_mech('uw.black_hole.cooldown_seconds')),
        cf_base_duration_s=_val(_mech('uw.chrono_field.duration_seconds')),
        cf_base_cooldown_s=_val(_mech('uw.chrono_field.cooldown_seconds')),
        cf_slow_pct=_val(_mech('uw.chrono_field.slow_pct')),
        cf_damage_reduction_pct=resolved_cf_dr,
        gt_base_duration_s=_val(_mech('uw.golden_tower.duration_seconds')),
        gt_base_cooldown_s=_val(_mech('uw.golden_tower.cooldown_seconds')),

        bh_perk_duration_add_s=_val(_runtime('uw.black_hole.duration_seconds')),
        bh_perk_cooldown_add_s=_val(_runtime('uw.black_hole.cooldown_seconds')),
        cf_perk_duration_add_s=_val(_runtime('uw.chrono_field.duration_seconds')),

        env_enemy_damage_multiplier=_val(_env('enemy.damage_multiplier'), 1.0),
        env_boss_health_multiplier=_val(_env('enemy.boss.health_multiplier'), 1.0),
        env_boss_speed_multiplier=_val(_env('enemy.boss.speed_multiplier'), 1.0),

        bot_amplify_duration_s=_val(_mech('bot.amplify.duration_seconds')),
        bot_amplify_cooldown_s=_val(_mech('bot.amplify.cooldown_seconds')),
        bot_golden_duration_s=_val(_mech('bot.golden.duration_seconds')),
        bot_golden_cooldown_s=_val(_mech('bot.golden.cooldown_seconds')),
        bot_thunder_duration_s=_val(_mech('bot.thunder.duration_seconds')),
        bot_thunder_cooldown_s=_val(_mech('bot.thunder.cooldown_seconds')),
        bot_flame_cooldown_s=_val(_mech('bot.flame.cooldown_seconds')),
        bot_flame_damage_reduction_pct=_val(_mech('bot.flame.damage_reduction_pct')),

        tower_orb_count=int(_val(_canon('tower_orb_count'))),
        tower_orb_speed_rpm=_val(_canon('tower_orb_speed_rpm')),
        electron_count=int(_val(_mech('module.orbital_augment.electron_count'), 0.0)),
    )


# ═══════════════════════════════════════════════════════════════════════
#  Main computation
# ═══════════════════════════════════════════════════════════════════════


def compute_scenario_surfaces(config: ScenarioConfig) -> ScenarioSurfaces:
    """Compute all fixed-for-run scenario-adjusted effect surfaces."""
    s = ScenarioSurfaces()
    s.mode_id = config.mode_id

    tier_bcs = _load_tier_battle_conditions()
    tourn_mags = _load_tournament_bc_magnitudes()
    boss_resist = _load_boss_enemy_class_resistances()

    is_tournament = config.mode_id == "tournament" and config.league
    active_wave = max(0, int(config.tournament_wave if is_tournament else config.current_wave))
    g1r = config.bc_reduction_group1_pct
    g2r = config.bc_reduction_group2_pct
    g4r = config.bc_reduction_group4_pct

    # ── Group 1 BCs: resistance multipliers + more_bosses ──

    if is_tournament:
        s.bc_source = f"tournament_magnitudes:league={config.league}:wave={config.tournament_wave}"
        w = config.tournament_wave
        s.bc_plasma_cannon_resistance = _reduce_resistance_multiplier(
            _interpolate_bc_magnitude(tourn_mags.get("plasma_cannon_resistance", {}), w), g1r)
        s.bc_orb_resistance = _reduce_resistance_multiplier(
            _interpolate_bc_magnitude(tourn_mags.get("orb_resistance", {}), w), g1r)
        s.bc_thorns_resistance = _reduce_resistance_multiplier(
            _interpolate_bc_magnitude(tourn_mags.get("thorns_resistance", {}), w), g1r)
        s.bc_death_ray_resistance = _reduce_resistance_multiplier(
            _interpolate_bc_magnitude(tourn_mags.get("death_ray_resistance", {}), w), g1r)
        s.bc_knockback_resistance = _reduce_resistance_multiplier(
            _interpolate_bc_magnitude(tourn_mags.get("knockback_resistance", {}), w), g1r)

        # Tournament more_bosses: constant 6 across all waves, group 1 reduction
        raw_mb = _interpolate_bc_magnitude(tourn_mags.get("more_bosses", {}), w)
        s.boss_wave_interval = max(1, round(_reduce_additive_magnitude(raw_mb, g1r)))
    else:
        s.bc_source = f"tier_battle_conditions:tier={config.tier}"
        t = config.tier

        # Resistance multipliers
        for bc_id, attr in [
            ("plasma_cannon_resistance", "bc_plasma_cannon_resistance"),
            ("orb_resistance", "bc_orb_resistance"),
            ("thorns_resistance", "bc_thorns_resistance"),
            ("death_ray_resistance", "bc_death_ray_resistance"),
            ("knockback_resistance", "bc_knockback_resistance"),
        ]:
            bc = tier_bcs.get(t, {}).get(bc_id)
            if bc and bc["kind"] == "damage_multiplier" and bc["value"]:
                setattr(s, attr, _reduce_resistance_multiplier(float(bc["value"]), g1r))
            elif bc and bc["kind"] == "knockback_multiplier" and bc["value"]:
                setattr(s, attr, _reduce_resistance_multiplier(float(bc["value"]), g1r))
            else:
                setattr(s, attr, 1.0)

        # Tier more_bosses
        mb = tier_bcs.get(t, {}).get("more_bosses")
        if mb and mb["kind"] == "boss_interval_waves" and mb["value"]:
            raw_interval = float(mb["value"])
            # BC reduction on more_bosses moves interval back toward 10
            penalty = 10.0 - raw_interval
            s.boss_wave_interval = max(1, round(10.0 - penalty * max(0.0, 1.0 - g1r / 100.0)))
        else:
            s.boss_wave_interval = 10

    # ── Group 2 BCs: enemy modifiers ──

    if is_tournament:
        w = config.tournament_wave
        raw_eas = _interpolate_bc_magnitude(tourn_mags.get("enemy_attack_speed", {}), w)
        s.bc_enemy_attack_speed_increase_pct = _reduce_additive_magnitude(raw_eas * 100.0, g2r)
        raw_es = _interpolate_bc_magnitude(tourn_mags.get("enemy_speed", {}), w)
        s.bc_enemy_speed_increase_pct = _reduce_additive_magnitude(raw_es * 100.0, g2r)
        raw_me = _interpolate_bc_magnitude(tourn_mags.get("more_enemies", {}), w)
        s.bc_more_enemies_pct = _reduce_additive_magnitude(raw_me * 100.0, g2r)
        raw_ae = _interpolate_bc_magnitude(tourn_mags.get("armored_enemies", {}), w)
        s.bc_armored_enemies_blocked_hits = _reduce_additive_magnitude(raw_ae, g2r)
    else:
        # Tier enemy_attack_speed: NOT present in tier BCs.
        s.bc_enemy_attack_speed_increase_pct = 0.0
        # Tier armored_enemies
        raw_ae = _tier_bc_float(tier_bcs, config.tier, "armored_enemies")
        s.bc_armored_enemies_blocked_hits = _reduce_additive_magnitude(raw_ae, g2r)

    # ── Group 4 BCs: UW duration reduction + enemy level skip ──

    if is_tournament:
        w = config.tournament_wave
        raw_uwd = _interpolate_bc_magnitude(tourn_mags.get("ultimate_weapons_duration", {}), w)
        # Magnitudes are negative (e.g. -5 seconds). Reduction shrinks the penalty.
        s.bc_uw_duration_reduction_s = _reduce_additive_magnitude(raw_uwd, g4r)

        raw_els = _interpolate_bc_magnitude(tourn_mags.get("enemy_level_skip", {}), w)
        s.bc_enemy_level_skip_reduction_pp = _reduce_additive_magnitude(raw_els, g4r)

        # death_defy_down: negative pp (e.g. -0.30 at wave 1000)
        raw_ddd = _interpolate_bc_magnitude(tourn_mags.get("death_defy_down", {}), w)
        s.bc_death_defy_down_pp = _reduce_additive_magnitude(raw_ddd, g4r)

        # energy_shields_down: fraction reduction (e.g. 1.0 = fully disabled at wave 1000)
        raw_esd = _interpolate_bc_magnitude(tourn_mags.get("energy_shields_down", {}), w)
        s.bc_energy_shields_down_fraction = _reduce_additive_magnitude(raw_esd, g4r)
    else:
        # Tier enemy_level_skip_reduction
        els = tier_bcs.get(config.tier, {}).get("enemy_level_skip_reduction")
        if els and els["value"]:
            raw_pp = float(els["value"])
            s.bc_enemy_level_skip_reduction_pp = _reduce_additive_magnitude(raw_pp, g4r)
        # death_defy_down and energy_shields_down: not present in tier BCs
        s.bc_death_defy_down_pp = 0.0
        s.bc_energy_shields_down_fraction = 0.0

    # ── Boss hit interval (base 2.0s, adjusted by enemy_attack_speed) ──
    # KB: boss-hit-interval.csv: 2.0s. Behavior: "increased by x%".
    # Formula: base / (1 + increase_pct / 100)
    s.overheat_start_wave = overheat_start_wave_for_tier(config.tier)
    s.overheat_active = s.overheat_start_wave > 0 and active_wave >= s.overheat_start_wave
    s.overheat_enemy_skip_decay_active = s.overheat_active
    if is_tournament and s.overheat_active:
        overheat_waves = max(0, active_wave - s.overheat_start_wave)
        s.overheat_damage_decay_active = True
        s.overheat_health_decay_active = True
        s.overheat_more_fleets_active = True
        s.overheat_more_elites_active = True
        s.overheat_damage_decay_steps = overheat_waves // 10
        s.overheat_health_decay_steps = overheat_waves // 10
        s.overheat_extra_fleets = overheat_waves // 100
        s.overheat_extra_elites = overheat_waves // 5

    base_hit_interval = 2.0
    if s.bc_enemy_attack_speed_increase_pct > 0:
        s.boss_hit_interval_seconds = base_hit_interval / (1.0 + s.bc_enemy_attack_speed_increase_pct / 100.0)
    else:
        s.boss_hit_interval_seconds = base_hit_interval

    # ── Boss class inherent resistances ──
    s.boss_thorns_effectiveness = boss_resist.get("thorns", 0.5)
    s.boss_electron_effectiveness = boss_resist.get("oa_electrons", 0.25)

    # ── Environment overlays (pass-through from stat engine) ──
    s.env_enemy_damage_multiplier = config.env_enemy_damage_multiplier
    s.env_boss_health_multiplier = config.env_boss_health_multiplier
    s.env_boss_speed_multiplier = config.env_boss_speed_multiplier

    # Timing-owned surfaces are emitted by simulators/timing.py.
    # ── Orb/electron pass-through ──
    s.tower_orb_count = config.tower_orb_count
    s.tower_orb_speed_rpm = config.tower_orb_speed_rpm
    s.electron_count = config.electron_count

    s.unsupported_terminal_pressures = _unsupported_terminal_pressures_for_scenario(
        config=config,
        scenario=s,
        tier_bcs=tier_bcs,
        is_tournament=is_tournament,
    )
    s.surfaces_status = "complete"
    return s


def compute_farming_throughput_surfaces(
    *,
    account_state,
    config: ScenarioConfig,
    stat_inputs: Sequence[StatInput],
    effective_wave_duration_seconds: float,
    farming_hours_per_day: float = 23.5,
) -> FarmingThroughputSurfaces:
    scenario = compute_scenario_surfaces(config)
    target_farming_wave = _target_farming_wave_from_state(account_state, config)
    wave_skip_pct = _lookup_runtime_row_value(stat_inputs, 'cards.wave_skip.chance_pct')
    intro_sprint_waves = _lookup_runtime_row_value(stat_inputs, 'cards.intro_sprint.waves')
    wave_skip_multiplier = 1.0 + (max(0.0, wave_skip_pct) / 100.0)
    waves_per_run_effective = max(
        0.0,
        target_farming_wave * wave_skip_multiplier + min(max(0.0, intro_sprint_waves), target_farming_wave),
    )
    run_duration_seconds = max(0.0, target_farming_wave * max(0.0, effective_wave_duration_seconds))
    runs_per_day_effective = (
        (max(0.0, farming_hours_per_day) * 3600.0) / run_duration_seconds
        if run_duration_seconds > 0.0 else 0.0
    )
    waves_per_day_effective = runs_per_day_effective * waves_per_run_effective
    bosses_per_day_effective = (
        waves_per_day_effective / float(max(1, scenario.boss_wave_interval))
        if waves_per_day_effective > 0.0 else 0.0
    )
    return FarmingThroughputSurfaces(
        target_farming_wave=target_farming_wave,
        waves_per_run_effective=waves_per_run_effective,
        runs_per_day_effective=runs_per_day_effective,
        waves_per_day_effective=waves_per_day_effective,
        bosses_per_day_effective=bosses_per_day_effective,
    )


def _farming_throughput_surface_specs(
    throughput: FarmingThroughputSurfaces,
) -> tuple[tuple[str, float, str, str], ...]:
    return (
        (
            'support_surface::scenario.target_farming_wave',
            throughput.target_farming_wave,
            'waves',
            'Target farming wave resolved from tier progression state.',
        ),
        (
            'support_surface::scenario.waves_per_run_effective',
            throughput.waves_per_run_effective,
            'waves_per_run',
            'Effective waves progressed per run after Wave Skip and Intro Sprint.',
        ),
        (
            'support_surface::scenario.runs_per_day_effective',
            throughput.runs_per_day_effective,
            'runs_per_day',
            'Effective farming runs per day from farming-hours cadence and wave timing.',
        ),
        (
            'support_surface::scenario.waves_per_day_effective',
            throughput.waves_per_day_effective,
            'waves_per_day',
            'Effective waves progressed per day from scenario-owned farming throughput.',
        ),
        (
            'support_surface::scenario.bosses_per_day_effective',
            throughput.bosses_per_day_effective,
            'bosses_per_day',
            'Effective bosses per day from scenario-owned farming throughput and boss cadence.',
        ),
    )


def farming_throughput_support_row_payloads(
    *,
    account_state,
    config: ScenarioConfig,
    stat_inputs: Sequence[StatInput],
    effective_wave_duration_seconds: float,
    farming_hours_per_day: float = 23.5,
) -> dict[str, dict[str, object]]:
    throughput = compute_farming_throughput_surfaces(
        account_state=account_state,
        config=config,
        stat_inputs=stat_inputs,
        effective_wave_duration_seconds=effective_wave_duration_seconds,
        farming_hours_per_day=farming_hours_per_day,
    )
    payloads: dict[str, dict[str, object]] = {}
    for surface_id, value, unit, notes in _farming_throughput_surface_specs(throughput):
        payloads[surface_id] = {
            'stat_name': surface_id,
            'final_value': value,
            'value_type': 'scalar',
            'source_count': 1,
            'status': 'resolved',
            'notes': notes,
            'contributors': [{
                'source_class': 'scenario_owned_throughput',
                'value': value,
                'unit': unit,
                'source_alignment': 'Scenario+Inputs',
            }],
            'schema': {
                'source_alignment': 'Scenario+Inputs',
                'publisher': 'scenario_support_publication',
                'unit': unit,
            },
        }
    return payloads


def publish_farming_throughput_support_surfaces(
    rows: Dict[str, StatRow],
    *,
    account_state,
    config: ScenarioConfig,
    stat_inputs: Sequence[StatInput],
    farming_hours_per_day: float = 23.5,
) -> None:
    wave_duration_row = rows.get('support_surface::timing.wave_duration_seconds_effective')
    if wave_duration_row is None:
        return
    try:
        effective_wave_duration_seconds = float(wave_duration_row.final_value)
    except (TypeError, ValueError):
        return

    throughput = compute_farming_throughput_surfaces(
        account_state=account_state,
        config=config,
        stat_inputs=stat_inputs,
        effective_wave_duration_seconds=effective_wave_duration_seconds,
        farming_hours_per_day=farming_hours_per_day,
    )
    for surface_id, value, unit, notes in _farming_throughput_surface_specs(throughput):
        rows[surface_id] = StatRow(
            stat_name=surface_id,
            final_value=value,
            value_type='scalar',
            source_count=1,
            status='resolved',
            notes=notes,
            contributors=[{
                'source_class': 'scenario_owned_throughput',
                'value': value,
                'unit': unit,
                'source_alignment': 'Scenario+Inputs',
            }],
            schema={'source_alignment': 'Scenario+Inputs', 'publisher': 'scenario_support_publication', 'unit': unit},
        )


def _lookup_runtime_row_value(rows: Sequence[StatInput], destination_id: str) -> float:
    for row in rows:
        if (
            row.destination_object_type == 'runtime_mechanic_param'
            and row.destination_id == destination_id
            and row.active
        ):
            try:
                return float(row.value)
            except (TypeError, ValueError):
                return 0.0
    return 0.0


def _target_farming_wave_from_state(account_state, config: ScenarioConfig) -> float:
    tier_label = f'Tier {int(config.tier)}'
    raw_value = (getattr(account_state, 'tier_progression_waves', {}) or {}).get(tier_label)
    try:
        return max(0.0, float(raw_value))
    except (TypeError, ValueError):
        return 0.0
