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
from typing import Any, Dict, List, Optional, Sequence

from qe.contracts import normalize_surface_id_to_contract
from qe.models import StatInput, StatRow

ROOT = Path(__file__).resolve().parents[1]


def _canon(destination_id: str) -> str:
    return normalize_surface_id_to_contract(f_canon('{destination_id}'))


def _mech(destination_id: str) -> str:
    return normalize_surface_id_to_contract(f_mech('{destination_id}'))


def _runtime(destination_id: str) -> str:
    return normalize_surface_id_to_contract(f_runtime('{destination_id}'))


def _env(destination_id: str) -> str:
    return normalize_surface_id_to_contract(f_env('{destination_id}'))


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
        electron_count=int(_val(_mech('module.orbital_augment.electron_count'))),
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
    surface_specs = (
        ('support_surface::scenario.target_farming_wave', throughput.target_farming_wave, 'waves', 'Target farming wave resolved from tier progression state.'),
        ('support_surface::scenario.waves_per_run_effective', throughput.waves_per_run_effective, 'waves_per_run', 'Effective waves progressed per run after Wave Skip and Intro Sprint.'),
        ('support_surface::scenario.runs_per_day_effective', throughput.runs_per_day_effective, 'runs_per_day', 'Effective farming runs per day from farming-hours cadence and wave timing.'),
        ('support_surface::scenario.waves_per_day_effective', throughput.waves_per_day_effective, 'waves_per_day', 'Effective waves progressed per day from scenario-owned farming throughput.'),
        ('support_surface::scenario.bosses_per_day_effective', throughput.bosses_per_day_effective, 'bosses_per_day', 'Effective bosses per day from scenario-owned farming throughput and boss cadence.'),
    )
    for surface_id, value, unit, notes in surface_specs:
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
