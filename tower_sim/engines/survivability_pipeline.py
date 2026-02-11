from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tower_sim.loaders.table_paths import resolve_table_path
from typing import Dict, Iterable, List, Mapping, Optional

from tower_sim.engines.combat.boss_survivability import (
    BossContext,
    BossStats,
    TowerDefense,
    resolve_boss_fight,
)
from tower_sim.engines.stat_engine import StatEngine, StatInput
from tower_sim.engines.stat_input_compiler import compile_full_stat_inputs
from tower_sim.engines.stat_snapshots import AtWaveSnapshot, build_at_wave_snapshot
from tower_sim.engines.tier_rules import TierRulesResult, build_tier_rules
from tower_sim.engines.wave_engine import SkipRamp, make_wave_state
from tower_sim.libs.assist_efficiency import AssistEfficiencyInputs
from tower_sim.libs.boss_hit_interval import boss_hit_interval_seconds
from tower_sim.libs.modules_library import Rarity, SUBSTAT_TABLES, UNIQUE_EFFECTS
from tower_sim.libs.wave_damage_strict import EnemyWaveDamageLib
from tower_sim.loaders.tier_battle_conditions import load_tier_battle_conditions
from tower_sim.loaders.wiki.cards import CardEffect, get_card_effect
from tower_sim.loaders.wiki.enemy_level_skip import workshop_level_to_chance
from tower_sim.loaders.wiki.assist_module_labs import AssistLabLevels
from tower_sim.loaders.bc_heat_loader import load_heat_bundle
from tower_sim.registry.combat_stat_contract import required_survivability_stat_ids
from tower_sim.registry.naming_contract import resolve_named_entity
from tower_sim.registry.stat_registry import Phase, default_registry
from tower_sim.run.context import RunContext
from tower_sim.run.problem_spec import BossSurvivabilitySpec, ProblemSpec, ScenarioSpec
from tower_sim.util.account_snapshot import AccountSnapshot, ModuleSnapshot
from tower_sim.libs.assist_efficiency import compute_efficiencies
from tower_sim.engines.tier_rule_apply import SUPPORTED_BC
from tower_sim.libs.workshop_lib import load_workshop_tables, workshop_value
from tower_sim.loaders.wiki.module_rules import max_active_substats_for_module_level
from tower_sim.libs.labs_lib import load_labs_values


class SurvivabilityPipelineError(RuntimeError):
    pass


@dataclass(frozen=True)
class ModuleSubstat:
    name: str
    rarity: Rarity
    value: float


@dataclass(frozen=True)
class ModuleRecord:
    name: str
    slot: str
    rarity: Rarity
    level: int
    main_effect: float
    substats: List[ModuleSubstat]


@dataclass(frozen=True)
class ModuleLoadout:
    slot: str
    primary: Optional[str]
    assist: Optional[str]
    assist_enabled: bool
    assist_stone_level: int
    assist_cap_rarity: Optional[Rarity]


@dataclass(frozen=True)
class ModuleBlock:
    loadout_by_context: Dict[str, ModuleLoadout]
    inventory: Dict[str, ModuleRecord]


@dataclass(frozen=True)
class PipelineSnapshots:
    base_only: Dict[str, float]
    start_of_run: Dict[str, float]
    at_wave: AtWaveSnapshot


@dataclass(frozen=True)
class SurvivabilityVerdict:
    ttk_seconds: float
    ttd_seconds: float
    outcome: str


STAT_IDS_SURVIVABILITY = required_survivability_stat_ids(include_optional_offense=True)

_RELEVANT_SUBSTATS = {
    "Health Regen",
    "Defense",
    "Wall Health",
    "Thorns Damage",
    "Enemy Attack Level Skip",
    "Enemy Health Level Skip",
}

_WORKSHOP_THORNS_MAX_LEVEL = 99  # Wiki excerpt in prompt: 99 upgrades at +1% each.
_WORKSHOP_THORNS_PER_LEVEL = 0.01  # Wiki excerpt in prompt: +1% per workshop level.
_WALL_THORNS_PER_LEVEL = 0.01  # Wiki excerpt in prompt: lab % shown is applied directly.
_BOSS_THORNS_MULT = 0.5  # Wiki excerpt in prompt: bosses take 50% thorns damage.


SLOT_ORDER = {
    0: "Cannon",
    1: "Armor",
    2: "Generator",
    3: "Core",
}


_RESERVED_ROWS = {
    "Assist Slot",
    "Rarity Cap",
    "Multiplier Cap",
    "Substat Cap",
    "Primary Slot",
    "Placeholder 4th preset",
    "Placeholder 5th preset",
    "Rarity",
    "Level",
    "Stat",
}


def build_survivability_report(
    ids_snapshot: AccountSnapshot,
    problem_spec: ProblemSpec,
    *,
    module_context: str = "Testing",
    module_overrides: Mapping[str, Mapping[str, Optional[str]]] | None = None,
    selected_cards: Iterable[str] | None = None,
    allow_provisional: bool = False,
) -> Dict[str, object]:
    warnings: Dict[str, object] = {}
    inventory = _build_inventory_summary(ids_snapshot, module_context, module_overrides)
    base_inputs = _compile_base_stat_inputs(
        ids_snapshot, allow_provisional=allow_provisional
    )
    loadout_inputs = _compile_loadout_stat_inputs(
        ids_snapshot,
        module_context=module_context,
        module_overrides=module_overrides,
        selected_cards=selected_cards,
        allow_provisional=allow_provisional,
    )
    compiled = compile_full_stat_inputs(ids_snapshot)
    if compiled.missing:
        if not allow_provisional:
            raise SurvivabilityPipelineError(
                "Missing workshop/UW stat inputs: " + ", ".join(compiled.missing)
            )
        warnings["missing_stat_inputs"] = sorted(compiled.missing)
    stat_inputs = _merge_stat_inputs(base_inputs, loadout_inputs)
    stat_inputs = _merge_stat_inputs(stat_inputs, compiled.stat_inputs)

    registry = default_registry()
    engine = StatEngine(registry=registry)

    base_result = engine.build(base_inputs)
    base_snapshot = _snapshot_from_phase(base_result, Phase.START_OF_RUN)

    start_result = engine.build(stat_inputs)
    start_snapshot = _snapshot_from_phase(start_result, Phase.START_OF_RUN)

    wave_state = _build_wave_state(problem_spec.scenario, start_snapshot)
    tier_rules, dropped_tier_conditions = _load_tier_rules(problem_spec.scenario)
    if dropped_tier_conditions:
        warnings["dropped_tier_conditions"] = dropped_tier_conditions
    heat_magnitudes = _resolve_heat_magnitudes(problem_spec.scenario, registry)

    at_wave_snapshot = build_at_wave_snapshot(
        stat_inputs=stat_inputs,
        engine_result=start_result,
        registry=registry,
        tier_rules=tier_rules,
        battle_conditions=None,
        wave_state=wave_state,
        wave=problem_spec.scenario.wave,
        run_context=RunContext.from_mode(
            problem_spec.scenario.mode,
            tier=str(problem_spec.scenario.tier),
        ),
        heat_magnitudes=heat_magnitudes,
    )

    verdict = _resolve_survivability_verdict(
        problem_spec.scenario,
        at_wave_snapshot=at_wave_snapshot,
        start_snapshot=start_snapshot,
        wave_state=wave_state,
    )

    snapshots = PipelineSnapshots(
        base_only=base_snapshot,
        start_of_run=start_snapshot,
        at_wave=at_wave_snapshot,
    )

    tier_rules_applied = _tier_rules_applied(tier_rules)
    if problem_spec.scenario.tier >= 14 and not tier_rules_applied:
        raise SurvivabilityPipelineError(
            "Tier rules expected for tier 14+ but none were applied."
        )

    applied_bc = dict(at_wave_snapshot.applied_bc)
    applied_bc.update(tier_rules_applied)

    return {
        "inventory": inventory,
        "warnings": warnings,
        "snapshots": {
            "base_only": snapshots.base_only,
            "start_of_run": snapshots.start_of_run,
            "at_wave": {
                "wave": snapshots.at_wave.wave,
                "wave_state": {
                    "W_actual": wave_state.W_actual,
                    "W_attack": wave_state.W_attack,
                    "W_health": wave_state.W_health,
                },
                "values": snapshots.at_wave.values,
                "applied_bc": applied_bc,
                "applied_heat": snapshots.at_wave.applied_heat,
            },
        },
        "survivability_verdict": {
            "ttk_seconds": verdict.ttk_seconds,
            "ttd_seconds": verdict.ttd_seconds,
            "outcome": verdict.outcome,
        },
    }


def _snapshot_from_phase(engine_result, phase: Phase) -> Dict[str, float]:
    stats = engine_result.run_stats.get(phase)
    if stats is None:
        raise SurvivabilityPipelineError(f"Missing {phase.value} stats in StatEngine result.")
    return dict(stats.values)


def _merge_stat_inputs(
    base_inputs: Iterable[StatInput],
    loadout_inputs: Iterable[StatInput],
) -> List[StatInput]:
    merged: Dict[tuple[str, Phase], StatInput] = {}
    for stat_input in base_inputs:
        merged[(stat_input.stat_id, stat_input.phase)] = stat_input
    for stat_input in loadout_inputs:
        key = (stat_input.stat_id, stat_input.phase)
        if key not in merged:
            merged[key] = stat_input
            continue
        base = merged[key]
        merged[key] = StatInput(
            stat_id=base.stat_id,
            phase=base.phase,
            base_value=base.base_value,
            loadout_delta=_sum_optional(base.loadout_delta, stat_input.loadout_delta),
            enhancement_multiplier=_mul_optional(
                base.enhancement_multiplier, stat_input.enhancement_multiplier
            ),
            tier_rule_delta=base.tier_rule_delta or stat_input.tier_rule_delta,
            tier_rule_multiplier=base.tier_rule_multiplier
            or stat_input.tier_rule_multiplier,
            derived_value=base.derived_value or stat_input.derived_value,
            provenance=base.provenance or stat_input.provenance,
        )
    return list(merged.values())


def _sum_optional(left: Optional[float], right: Optional[float]) -> Optional[float]:
    if left is None and right is None:
        return None
    return float(left or 0.0) + float(right or 0.0)


def _mul_optional(left: Optional[float], right: Optional[float]) -> Optional[float]:
    if left is None and right is None:
        return None
    return float(left or 1.0) * float(right or 1.0)


def _compile_base_stat_inputs(
    ids_snapshot: AccountSnapshot,
    *,
    allow_provisional: bool,
) -> List[StatInput]:
    _assert_vault_zero(ids_snapshot)
    workshop_tables = load_workshop_tables()
    labs = load_labs_values()

    tower_hp = _workshop_value(ids_snapshot, "Health", workshop_tables, "WSValues")
    tower_hp *= _lab_multiplier(labs, "Health", ids_snapshot)

    tower_regen = _workshop_value(
        ids_snapshot, "Health Regen", workshop_tables, "WSValues"
    )
    tower_regen *= _lab_multiplier(labs, "Health Regen", ids_snapshot)

    def_pct = _defense_percent(ids_snapshot, allow_provisional=allow_provisional)

    wall_ratio = _wall_health_ratio(
        ids_snapshot, labs, allow_provisional=allow_provisional
    )
    wall_hp = tower_hp * wall_ratio

    wall_regen_ratio = _wall_regen_ratio(
        ids_snapshot, labs, allow_provisional=allow_provisional
    )
    wall_regen = tower_regen * wall_regen_ratio

    inputs = [
        StatInput(
            stat_id="tower_hp",
            phase=Phase.START_OF_RUN,
            base_value=tower_hp,
            provenance="base:workshop+labs",
        ),
        StatInput(
            stat_id="tower_regen",
            phase=Phase.START_OF_RUN,
            base_value=tower_regen,
            provenance="base:workshop+labs",
        ),
        StatInput(
            stat_id="def_pct",
            phase=Phase.START_OF_RUN,
            base_value=def_pct,
            provenance="base:workshop+labs",
        ),
        StatInput(
            stat_id="wall_hp",
            phase=Phase.START_OF_RUN,
            base_value=wall_hp,
            provenance="base:workshop+labs",
        ),
        StatInput(
            stat_id="wall_regen",
            phase=Phase.START_OF_RUN,
            base_value=wall_regen,
            provenance="base:workshop+labs",
        ),
    ]

    eals_pct = _resolve_skip_stat(ids_snapshot, "Enemy Attack Level Skip")
    ehls_pct = _resolve_skip_stat(ids_snapshot, "Enemy Health Level Skip")
    thorns_base, thorns_mult, thorns_provenance = _resolve_thorns_inputs(
        ids_snapshot
    )

    inputs.extend(
        [
            StatInput(
                stat_id="eals_pct",
                phase=Phase.START_OF_RUN,
                base_value=eals_pct,
                provenance="base:workshop+labs",
            ),
            StatInput(
                stat_id="ehls_pct",
                phase=Phase.START_OF_RUN,
                base_value=ehls_pct,
                provenance="base:workshop+labs",
            ),
            StatInput(
                stat_id="thorns_damage_mult",
                phase=Phase.START_OF_RUN,
                base_value=thorns_base,
                enhancement_multiplier=thorns_mult,
                provenance=thorns_provenance,
            ),
            StatInput(
                stat_id="orb_damage_mult",
                phase=Phase.START_OF_RUN,
                base_value=1.0,
                provenance="base:identity",
            ),
            StatInput(
                stat_id="death_ray_damage_mult",
                phase=Phase.START_OF_RUN,
                base_value=1.0,
                provenance="base:identity",
            ),
            StatInput(
                stat_id="plasma_cannon_damage_mult",
                phase=Phase.START_OF_RUN,
                base_value=0.0,
                provenance="base:cards:plasma_cannon",
            ),
            StatInput(
                stat_id="knockback_mult",
                phase=Phase.START_OF_RUN,
                base_value=1.0,
                provenance="base:identity",
            ),
        ]
    )
    return inputs


def _assert_vault_zero(ids_snapshot: AccountSnapshot) -> None:
    vault = ids_snapshot.vault
    if not vault:
        return
    check_keys = [
        "Health",
        "Health Regen",
        "Defense %",
        "Wall Health",
        "Wall Regen",
        "Thorn Damage",
    ]
    for key in check_keys:
        value = vault.get(key)
        if value is None:
            continue
        try:
            numeric = float(value)
        except ValueError as exc:
            raise SurvivabilityPipelineError(
                f"Invalid vault value for {key!r}: {value!r}"
            ) from exc
        if numeric != 0.0:
            raise SurvivabilityPipelineError(
                f"Vault modifier for {key!r} requires vault_stats_v1.csv provenance."
            )


def _workshop_value(
    ids_snapshot: AccountSnapshot,
    stat_name: str,
    workshop_tables,
    section: str,
) -> float:
    entry = ids_snapshot.workshop.get(stat_name)
    if entry is None or entry.coin_level is None:
        raise SurvivabilityPipelineError(
            f"Missing workshop level for {stat_name!r} in IDS."
        )
    level = entry.coin_level
    table_stat = stat_name
    if stat_name == "Health Regen":
        table_stat = "HPregen"
    return float(workshop_value(table_stat, level, workshop_tables, section=section))


def _lab_multiplier(labs, lab_name: str, ids_snapshot: AccountSnapshot) -> float:
    lab_level_raw = ids_snapshot.labs.get(lab_name)
    if lab_level_raw is None:
        raise SurvivabilityPipelineError(f"Missing lab level for {lab_name!r} in IDS.")
    lab_level = lab_level_raw
    if lab_name not in labs:
        raise SurvivabilityPipelineError(f"Missing lab table for {lab_name!r}.")
    lab = labs[lab_name]
    if lab_level == 0:
        return 1.0
    if lab_level not in lab.levels:
        raise SurvivabilityPipelineError(
            f"Lab {lab_name!r} missing level {lab_level} in labs_values_v1.csv."
        )
    if lab.unit == "raw_number":
        return lab.levels[lab_level]
    raise SurvivabilityPipelineError(
        f"Unsupported lab unit {lab.unit!r} for {lab_name!r}."
    )


def _defense_percent(ids_snapshot: AccountSnapshot, *, allow_provisional: bool) -> float:
    if not allow_provisional:
        raise SurvivabilityPipelineError(
            "Defense % ladder lacks an authoritative table. "
            "Set allow_provisional=True to use EP constants."
        )
    workshop_entry = ids_snapshot.workshop.get("Defense %")
    if workshop_entry is None or workshop_entry.coin_level is None:
        raise SurvivabilityPipelineError("Missing workshop Defense % level in IDS.")
    workshop_level = workshop_entry.coin_level
    lab_level_raw = ids_snapshot.labs.get("Defense %")
    if lab_level_raw is None:
        raise SurvivabilityPipelineError("Missing lab Defense % level in IDS.")
    lab_level = lab_level_raw
    ws_pp = workshop_level * 0.5
    lab_pp = min(lab_level * 0.2, 10.0)
    value = (ws_pp + lab_pp) / 100.0
    return min(value, 0.98)


def _wall_health_ratio(
    ids_snapshot: AccountSnapshot, labs, *, allow_provisional: bool
) -> float:
    if not allow_provisional:
        raise SurvivabilityPipelineError(
            "Wall Health ratio ladder lacks an authoritative table. "
            "Set allow_provisional=True to use EP constants."
        )
    base_ratio = 0.2
    workshop_entry = ids_snapshot.workshop.get("Wall Health")
    if workshop_entry is None or workshop_entry.coin_level is None:
        raise SurvivabilityPipelineError("Missing workshop Wall Health level in IDS.")
    workshop_level = workshop_entry.coin_level
    ratio = base_ratio + min(workshop_level * 0.001, 2.0)

    lab_level_raw = ids_snapshot.labs.get("Wall Health")
    if lab_level_raw is None:
        raise SurvivabilityPipelineError("Missing lab Wall Health level in IDS.")
    lab_level = lab_level_raw
    if lab_level > 0:
        if "Wall Health" not in labs:
            raise SurvivabilityPipelineError("Missing Wall Health lab table.")
        lab = labs["Wall Health"]
        if lab_level not in lab.levels:
            raise SurvivabilityPipelineError(
                f"Wall Health lab missing level {lab_level}."
            )
        lab_value = lab.levels[lab_level]
        if lab.unit == "percent":
            ratio += lab_value / 100.0
        elif lab.unit == "percent_points":
            ratio += lab_value / 100.0
        else:
            raise SurvivabilityPipelineError(
                f"Unsupported Wall Health lab unit {lab.unit!r}."
            )
    return ratio


def _wall_regen_ratio(
    ids_snapshot: AccountSnapshot, labs, *, allow_provisional: bool
) -> float:
    if not allow_provisional:
        raise SurvivabilityPipelineError(
            "Wall Regen ratio ladder lacks an authoritative table. "
            "Set allow_provisional=True to use EP constants."
        )
    lab_level_raw = ids_snapshot.labs.get("Wall Regen")
    if lab_level_raw is None:
        raise SurvivabilityPipelineError("Missing lab Wall Regen level in IDS.")
    lab_level = lab_level_raw
    if lab_level == 0:
        return 0.0
    if "Wall Regen" not in labs:
        raise SurvivabilityPipelineError("Missing Wall Regen lab table.")
    lab = labs["Wall Regen"]
    if lab_level not in lab.levels:
        raise SurvivabilityPipelineError(
            f"Wall Regen lab missing level {lab_level}."
        )
    if lab.unit == "percent":
        return lab.levels[lab_level] / 100.0
    if lab.unit == "percent_points":
        return lab.levels[lab_level] / 100.0
    raise SurvivabilityPipelineError(
        f"Unsupported Wall Regen lab unit {lab.unit!r}."
    )


def _resolve_thorns_inputs(
    ids_snapshot: AccountSnapshot,
) -> tuple[float, float, str]:
    workshop_entry = ids_snapshot.workshop.get("Thorn Damage")
    if workshop_entry is None or workshop_entry.coin_level is None:
        raise SurvivabilityPipelineError(
            "Missing workshop level for 'Thorn Damage' in IDS."
        )
    workshop_level = workshop_entry.coin_level
    if workshop_level < 0:
        raise SurvivabilityPipelineError(
            f"Invalid workshop level for Thorn Damage: {workshop_level}."
        )
    if workshop_level > _WORKSHOP_THORNS_MAX_LEVEL:
        raise SurvivabilityPipelineError(
            "Thorn Damage workshop level exceeds max "
            f"{_WORKSHOP_THORNS_MAX_LEVEL}: {workshop_level}."
        )
    workshop_thorns = workshop_level * _WORKSHOP_THORNS_PER_LEVEL

    wall_thorns_level = ids_snapshot.labs.get("Wall Thorn")
    if wall_thorns_level is None:
        raise SurvivabilityPipelineError("Missing canonical lab level for 'Wall Thorn' in IDS.")
    if wall_thorns_level < 0:
        raise SurvivabilityPipelineError(
            f"Invalid lab level for Wall Thorn: {wall_thorns_level}."
        )
    wall_thorns_pct = wall_thorns_level * _WALL_THORNS_PER_LEVEL

    relic_bonus = _sum_relic_bonus(ids_snapshot, ("Thorns", "Thorn Damage"))
    relic_multiplier = 1.0 + relic_bonus

    multiplier = relic_multiplier * wall_thorns_pct * _BOSS_THORNS_MULT
    provenance = (
        "workshop:Thorn Damage + labs:Wall Thorn + relics:Thorns "
        "(wiki excerpt in prompt)"
    )
    return workshop_thorns, multiplier, provenance


def _sum_relic_bonus(
    ids_snapshot: AccountSnapshot, keys: Iterable[str]
) -> float:
    relics = ids_snapshot.relics
    total = 0.0
    for key in keys:
        if key not in relics:
            continue
        value = relics.get(key)
        if value is None:
            raise SurvivabilityPipelineError(
                f"Missing relic value for {key!r} in IDS."
            )
        try:
            numeric = float(value)
        except ValueError as exc:
            raise SurvivabilityPipelineError(
                f"Invalid relic value for {key!r}: {value!r}"
            ) from exc
        total += numeric
    if total < 0:
        raise SurvivabilityPipelineError(
            f"Relic bonus must be non-negative, got {total}."
        )
    return total


def _compile_loadout_stat_inputs(
    ids_snapshot: AccountSnapshot,
    *,
    module_context: str,
    module_overrides: Mapping[str, Mapping[str, Optional[str]]] | None,
    selected_cards: Iterable[str] | None,
    allow_provisional: bool,
) -> List[StatInput]:
    accumulator = _StatAccumulator()
    module_blocks = _parse_module_blocks(ids_snapshot)
    for block in module_blocks.values():
        if module_context not in block.loadout_by_context:
            continue
        loadout = block.loadout_by_context[module_context]
        overrides = (module_overrides or {}).get(loadout.slot, {})
        primary_name = overrides.get("primary", loadout.primary)
        assist_name = overrides.get("assist", loadout.assist)
        assist_enabled = loadout.assist_enabled
        assist_level = loadout.assist_stone_level
        assist_cap = loadout.assist_cap_rarity
        allocation = ids_snapshot.allocation_levels.get(loadout.slot)
        if allocation is not None:
            assist_level = allocation.assist_level

        if primary_name:
            primary = _resolve_module(primary_name, loadout.slot, block.inventory)
        else:
            primary = None
        if assist_name:
            assist = _resolve_module(assist_name, loadout.slot, block.inventory)
        else:
            assist = None

        _apply_module_effects(
            accumulator,
            primary=primary,
            assist=assist,
            assist_enabled=assist_enabled,
            assist_level=assist_level,
            assist_cap=assist_cap,
            ids_snapshot=ids_snapshot,
            allow_provisional=allow_provisional,
        )

    _apply_card_effects(
        accumulator,
        ids_snapshot,
        module_context=module_context,
        selected_cards=selected_cards,
    )

    _apply_relic_effects(accumulator, ids_snapshot)

    return accumulator.to_stat_inputs()


def _apply_relic_effects(
    accumulator: "_StatAccumulator",
    ids_snapshot: AccountSnapshot,
) -> None:
    defense_bonus = 0.0
    for key in ("Defense", "Defense %"):
        raw = ids_snapshot.relics.get(key)
        if raw is None:
            continue
        try:
            numeric = float(raw)
        except ValueError as exc:
            raise SurvivabilityPipelineError(
                f"Invalid relic value for {key!r}: {raw!r}"
            ) from exc
        if numeric < 0:
            raise SurvivabilityPipelineError(
                f"Relic bonus must be non-negative for {key!r}, got {numeric}."
            )
        defense_bonus += numeric
    if defense_bonus > 0.0:
        accumulator.add("def_pct", defense_bonus, "relics:defense")


def _resolve_skip_stat(ids_snapshot: AccountSnapshot, lab_name: str) -> float:
    workshop_entry = ids_snapshot.workshop.get(lab_name)
    if workshop_entry is None or workshop_entry.coin_level is None:
        raise SurvivabilityPipelineError(
            f"Missing workshop level for {lab_name!r} in IDS."
        )
    workshop_level = workshop_entry.coin_level

    lab_level_raw = ids_snapshot.labs.get(lab_name)
    if lab_level_raw is None:
        raise SurvivabilityPipelineError(f"Missing lab level for {lab_name!r} in IDS.")
    lab_level = lab_level_raw

    from tower_sim.libs.labs_lib import load_labs_values

    labs = load_labs_values()
    if lab_name not in labs:
        raise SurvivabilityPipelineError(f"Missing lab table for {lab_name!r}.")
    lab = labs[lab_name]
    if lab_level not in lab.levels:
        raise SurvivabilityPipelineError(
            f"Lab {lab_name!r} missing level {lab_level} in labs_values_v1.csv."
        )
    lab_value = lab.levels[lab_level]
    if lab.unit == "percent_points":
        lab_value = lab_value / 100.0
    elif lab.unit == "percent":
        lab_value = lab_value / 100.0
    elif lab.unit != "raw_number":
        raise SurvivabilityPipelineError(
            f"Unsupported lab unit {lab.unit!r} for {lab_name!r}."
        )

    chance = workshop_level_to_chance(workshop_level) + float(lab_value)
    return _clamp01(chance * _enemy_level_skips_enhancement_multiplier(ids_snapshot))


def _enemy_level_skips_enhancement_multiplier(ids_snapshot: AccountSnapshot) -> float:
    for row in ids_snapshot.workshop_enhancements.rows:
        if not row:
            continue
        base_name = row[0].strip()
        if base_name != "Enemy Level Skips +":
            continue
        if len(row) < 2 or not row[1].strip():
            raise SurvivabilityPipelineError("Missing Enemy Level Skips enhancement multiplier in WS+ table.")
        try:
            mult = float(row[1].strip())
        except ValueError as exc:
            raise SurvivabilityPipelineError(
                f"Invalid Enemy Level Skips enhancement multiplier: {row[1]!r}."
            ) from exc
        if mult <= 0:
            raise SurvivabilityPipelineError(
                f"Enemy Level Skips enhancement multiplier must be > 0, got {mult}."
            )
        return mult
    raise SurvivabilityPipelineError("Missing Enemy Level Skips enhancement row in WS+ table.")


def _clamp01(value: float) -> float:
    if value <= 0.0:
        return 0.0
    if value >= 1.0:
        return 1.0
    return value


def _resolve_loadout(
    ids_snapshot: AccountSnapshot, module_context: str
) -> ResolvedLoadout:
    try:
        return resolve_loadout(ids_snapshot, module_context)
    except ValueError as exc:
        raise SurvivabilityPipelineError(str(exc)) from exc


def _build_wave_state(scenario: ScenarioSpec, start_snapshot: Mapping[str, float]):
    if scenario.eals_ramp and scenario.ehls_ramp:
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
    else:
        eals_pct = start_snapshot.get("eals_pct")
        ehls_pct = start_snapshot.get("ehls_pct")
        if eals_pct is None or ehls_pct is None:
            raise SurvivabilityPipelineError("Missing eals_pct/ehls_pct for wave state.")
        eals = SkipRamp(start=float(eals_pct), end=float(eals_pct), ramp_waves=1)
        ehls = SkipRamp(start=float(ehls_pct), end=float(ehls_pct), ramp_waves=1)

    return make_wave_state(scenario.wave, eals, ehls)


def _load_tier_rules(
    scenario: ScenarioSpec,
) -> tuple[Optional[TierRulesResult], List[Dict[str, str]]]:
    bc_path = resolve_table_path("tier_battle_conditions")
    catalog = load_tier_battle_conditions(bc_path, allow_incomplete=True)
    run_context = RunContext.from_mode(scenario.mode, tier=str(scenario.tier))
    rules = build_tier_rules(scenario.tier, run_context, catalog)
    unsupported = [
        condition
        for condition in rules.conditions
        if (condition.name, condition.kind, condition.unit) not in SUPPORTED_BC
    ]
    dropped: List[Dict[str, str]] = []
    if unsupported:
        for condition in unsupported:
            dropped.append(
                {
                    "name": condition.name,
                    "kind": condition.kind,
                    "unit": condition.unit,
                    "reason": "unsupported_bc",
                }
            )
        rules = TierRulesResult(
            tier=rules.tier,
            context=rules.context,
            conditions=[
                condition
                for condition in rules.conditions
                if (condition.name, condition.kind, condition.unit) in SUPPORTED_BC
            ],
        )
    return rules, dropped


def _tier_rules_applied(tier_rules: Optional[TierRulesResult]) -> Dict[str, float]:
    if tier_rules is None:
        return {}
    mapping = {
        "orb_resistance": "orb_damage_mult",
        "death_ray_resistance": "death_ray_damage_mult",
        "thorns_resistance": "thorns_damage_mult",
        "plasma_cannon_resistance": "plasma_cannon_damage_mult",
        "knockback_resistance": "knockback_mult",
    }
    applied: Dict[str, float] = {}
    for condition in tier_rules.conditions:
        stat_id = mapping.get(condition.name)
        if stat_id is None:
            continue
        applied[stat_id] = float(condition.value)
    return applied


def _resolve_heat_magnitudes(
    scenario: ScenarioSpec,
    registry,
) -> Optional[Dict[str, float]]:
    if scenario.mode != "tournament":
        return None
    if scenario.league is None:
        raise SurvivabilityPipelineError("Missing league for tournament heat lookup.")
    heat_path = resolve_table_path("heat_scale_long")
    magnitudes_path = (
        Path(__file__).resolve().parents[2]
        / "tables"
        / "battle_condition_magnitudes.csv"
    )
    bundle = load_heat_bundle(heat_path, magnitudes_path)

    league = scenario.league.lower()
    wave = scenario.wave
    scalars = [row for row in bundle.heat_scalars if row.league == league and row.wave == wave]
    if not scalars:
        raise SurvivabilityPipelineError("Missing heat scalar for league/wave.")
    if any(row.scalar != 1.0 for row in scalars):
        raise SurvivabilityPipelineError(
            "Heat scalar mapping to BC magnitudes is not implemented."
        )

    magnitudes = [
        row
        for row in bundle.magnitudes
        if row.league == league and row.wave == wave
    ]
    if not magnitudes:
        raise SurvivabilityPipelineError("Missing BC magnitudes for league/wave.")

    mapped: Dict[str, float] = {}
    for row in magnitudes:
        if row.bc_id in mapped:
            raise SurvivabilityPipelineError(f"Duplicate BC magnitude: {row.bc_id}")
        registry.validate_stat_id(row.bc_id)
        mapped[row.bc_id] = row.magnitude
    return mapped


def _resolve_survivability_verdict(
    scenario: ScenarioSpec,
    *,
    at_wave_snapshot: AtWaveSnapshot,
    start_snapshot: Mapping[str, float],
    wave_state,
) -> SurvivabilityVerdict:
    spec: BossSurvivabilitySpec | None = scenario.boss_survivability
    if spec is None:
        raise SurvivabilityPipelineError("Missing boss_survivability spec.")

    wave_damage = _resolve_wave_damage(scenario, wave_state)
    hit_interval = boss_hit_interval_seconds(
        str(spec.combat_params.get("hit_interval_id", "default"))
    )
    boss = BossStats(
        hp=None,
        attack=wave_damage,
        attack_interval=hit_interval,
        enrage_mult=spec.boss.enrage_mult or 1.0,
    )
    tower = TowerDefense(
        dr_frac=spec.tower.dr_frac,
        regen_per_sec=spec.tower.regen_per_sec,
        shields=spec.tower.shields,
    )
    values = dict(start_snapshot)
    values.update(at_wave_snapshot.values)
    combat_params = dict(spec.combat_params)
    for stat_id in STAT_IDS_SURVIVABILITY:
        if stat_id not in values:
            raise SurvivabilityPipelineError(
                f"Missing survivability stat {stat_id!r} in snapshot."
            )
    thorns_frac = values["thorns_damage_mult"]
    pc_frac = values["plasma_cannon_damage_mult"]
    combat_params.update(
        {
            "tower_hp": values["tower_hp"],
            "tower_regen": values["tower_regen"],
            "defense_pct": values["def_pct"],
            "wall_hp": values["wall_hp"],
            "wall_regen": values["wall_regen"],
            "thorns_frac": thorns_frac,
            "pc_frac": pc_frac,
        }
    )
    ctx = BossContext(
        wave=scenario.wave,
        tier=scenario.tier,
        league=scenario.league or "",
        boss=boss,
        tower=tower,
        combat_params=combat_params,
        bc_params=spec.bc_params,
    )
    result = resolve_boss_fight(ctx)
    ttk = result.get("ttk_seconds")
    ttd = result.get("ttd_seconds")
    outcome = result.get("outcome")
    if ttk is None or ttd is None or outcome is None:
        raise SurvivabilityPipelineError("Boss survivability result missing TTK/TTD.")
    return SurvivabilityVerdict(
        ttk_seconds=float(ttk),
        ttd_seconds=float(ttd),
        outcome=str(outcome),
    )


def _resolve_wave_damage(scenario: ScenarioSpec, wave_state) -> float:
    wave_tier = scenario.wave_damage_tier
    if wave_tier is None:
        if scenario.mode == "farming":
            wave_tier = f"Tier {scenario.tier}"
        elif scenario.league:
            wave_tier = scenario.league
    if wave_tier is None:
        raise SurvivabilityPipelineError("Missing wave damage tier.")
    lib = EnemyWaveDamageLib.from_repo_tables()
    return lib.wave_damage(wave_tier, wave_state.W_attack)


def _build_inventory_summary(
    ids_snapshot: AccountSnapshot,
    module_context: str,
    module_overrides: Mapping[str, Mapping[str, Optional[str]]] | None,
) -> Dict[str, object]:
    module_blocks = _parse_module_blocks(ids_snapshot)
    module_summary: Dict[str, object] = {}
    for slot, block in module_blocks.items():
        loadout = block.loadout_by_context.get(module_context)
        override = (module_overrides or {}).get(slot, {})
        allocation = ids_snapshot.allocation_levels.get(slot)
        module_summary[slot] = {
            "loadout": {
                "primary": override.get("primary", loadout.primary if loadout else None),
                "assist": override.get("assist", loadout.assist if loadout else None),
                "assist_enabled": loadout.assist_enabled if loadout else False,
                "assist_stone_level": (
                    allocation.assist_level
                    if allocation
                    else loadout.assist_stone_level if loadout else 0
                ),
                "assist_cap_rarity": loadout.assist_cap_rarity.name if loadout and loadout.assist_cap_rarity else None,
            },
            "inventory": [
                {
                    "name": record.name,
                    "rarity": record.rarity.name,
                    "level": record.level,
                    "main_effect": record.main_effect,
                    "substats": [
                        {
                            "name": substat.name,
                            "rarity": substat.rarity.name,
                            "value": substat.value,
                        }
                        for substat in record.substats
                    ],
                }
                for record in block.inventory.values()
            ],
        }

    cards = []
    for entry in ids_snapshot.cards_inventory.values():
        presets = [
            preset
            for preset, card_list in ids_snapshot.card_presets.items()
            if entry.name in card_list
        ]
        cards.append(
            {
                "name": entry.name,
                "level": entry.level,
                "mastery_unlocked": entry.mastery_unlocked,
                "mastery_lab_level": entry.mastery_lab_level,
                "equipped_presets": presets,
            }
        )
    bots = list(ids_snapshot.bots)
    guardians = list(ids_snapshot.guardians.rows)
    return {
        "modules": module_summary,
        "cards": cards,
        "bots": bots,
        "guardians": guardians,
    }


def _parse_module_blocks(ids_snapshot: AccountSnapshot) -> Dict[str, ModuleBlock]:
    blocks: Dict[str, ModuleBlock] = {}
    for slot_name in SLOT_ORDER.values():
        system_state = ids_snapshot.module_system_state.get(slot_name)
        if system_state is None:
            raise SurvivabilityPipelineError(
                f"Missing module system state for {slot_name!r}."
            )
        assist_cap = None
        if system_state.rarity_cap:
            assist_cap = _parse_rarity(system_state.rarity_cap)
        loadout_by_context: Dict[str, ModuleLoadout] = {}
        for preset_name, preset in ids_snapshot.module_presets.items():
            selection = preset.get(slot_name)
            if selection is None:
                raise SurvivabilityPipelineError(
                    f"Missing module preset {preset_name} for {slot_name!r}."
                )
            loadout_by_context[preset_name] = ModuleLoadout(
                slot=slot_name,
                primary=selection.primary,
                assist=selection.assist,
                assist_enabled=system_state.assist_unlocked,
                assist_stone_level=system_state.assist_level,
                assist_cap_rarity=assist_cap,
            )
        inventory: Dict[str, ModuleRecord] = {}
        for name, entry in ids_snapshot.modules_inventory.items():
            if entry.slot_type != slot_name:
                continue
            inventory[name] = _module_record_from_snapshot(entry, slot_name)
        blocks[slot_name] = ModuleBlock(
            loadout_by_context=loadout_by_context,
            inventory=inventory,
        )
    return blocks


def _module_record_from_snapshot(
    entry: ModuleSnapshot, slot_name: str
) -> ModuleRecord:
    if entry.rarity is None:
        raise SurvivabilityPipelineError(
            f"Missing rarity for module {entry.name!r} in {slot_name}."
        )
    rarity = _parse_rarity(entry.rarity)
    if rarity is None:
        raise SurvivabilityPipelineError(
            f"Missing rarity for module {entry.name!r} in {slot_name}."
        )
    if entry.level is None:
        raise SurvivabilityPipelineError(
            f"Missing level for module {entry.name!r} in {slot_name}."
        )
    if entry.stat is None:
        raise SurvivabilityPipelineError(
            f"Missing main effect for module {entry.name!r} in {slot_name}."
        )
    try:
        main_effect = float(entry.stat)
    except ValueError as exc:
        raise SurvivabilityPipelineError(
            f"Invalid main effect for module {entry.name!r}: {entry.stat!r}"
        ) from exc
    substats: List[ModuleSubstat] = []
    for substat in entry.substats:
        if not substat.stat_name:
            continue
        normalized = _normalize_substat_name(substat.stat_name)
        if normalized not in _RELEVANT_SUBSTATS:
            continue
        if substat.rarity is None:
            raise SurvivabilityPipelineError(
                f"Missing substat rarity for {substat.stat_name!r} in {entry.name!r}."
            )
        rarity_value = _parse_rarity(substat.rarity)
        if rarity_value is None:
            raise SurvivabilityPipelineError(
                f"Missing substat rarity for {substat.stat_name!r} in {entry.name!r}."
            )
        substat_value = _resolve_substat_value(slot_name, normalized, rarity_value)
        substats.append(
            ModuleSubstat(
                name=normalized,
                rarity=rarity_value,
                value=substat_value,
            )
        )
    return ModuleRecord(
        name=entry.name,
        slot=slot_name,
        rarity=rarity,
        level=entry.level,
        main_effect=main_effect,
        substats=substats,
    )


def _parse_module_block(rows: List[List[str]], slot_name: str) -> ModuleBlock:
    loadout_by_context: Dict[str, ModuleLoadout] = {}
    inventory: Dict[str, ModuleRecord] = {}
    assist_enabled: Optional[bool] = None
    assist_stone_level = 0
    assist_cap_rarity: Optional[Rarity] = None
    current_context: Optional[str] = None
    context_primary: Dict[str, Optional[str]] = {}
    context_assist: Dict[str, Optional[str]] = {}

    i = 0
    while i < len(rows):
        cell = rows[i][0].strip()
        if cell == "Assist Slot" and assist_enabled is None:
            assist_enabled = rows[i][1].strip().lower() == "true"
            assist_stone_level = _parse_optional_int(rows[i][2]) or 0
            i += 1
            continue
        if cell == "Rarity Cap" and assist_cap_rarity is None:
            assist_cap_rarity = _parse_rarity(rows[i][1])
            i += 1
            continue
        if cell in {"Farming", "Tourney", "Testing"}:
            current_context = cell
            i += 1
            continue
        if cell in {"Primary Slot", "Assist Slot"} and current_context:
            name = rows[i][1].strip() or None
            if cell == "Primary Slot":
                context_primary[current_context] = name
            else:
                context_assist[current_context] = name
            i += 1
            continue
        if _looks_like_module_header(rows, i):
            module_name = cell
            rarity_row = rows[i + 2]
            rarity = _parse_rarity(rarity_row[0])
            if rarity is None:
                raise SurvivabilityPipelineError(
                    f"Missing rarity for module {module_name!r} in {slot_name}."
                )
            level = _parse_optional_int(rarity_row[1])
            if level is None:
                raise SurvivabilityPipelineError(
                    f"Missing level for module {module_name!r} in {slot_name}."
                )
            main_effect = _parse_optional_float(rarity_row[2])
            if main_effect is None:
                raise SurvivabilityPipelineError(
                    f"Missing main effect for module {module_name!r} in {slot_name}."
                )
            substats: List[ModuleSubstat] = []
            i += 3
            while i < len(rows):
                if _looks_like_module_header(rows, i):
                    break
                candidate = rows[i][0].strip()
                if candidate in _RESERVED_ROWS or candidate in {"Farming", "Tourney", "Testing"}:
                    i += 1
                    continue
                if candidate:
                    normalized = _normalize_substat_name(candidate)
                    if normalized not in _RELEVANT_SUBSTATS:
                        i += 1
                        continue
                    rarity_value = _parse_rarity(rows[i][1])
                    if rarity_value is None:
                        raise SurvivabilityPipelineError(
                            f"Missing substat rarity for {candidate!r} in {module_name!r}."
                        )
                    substat_value = _resolve_substat_value(
                        slot_name, normalized, rarity_value
                    )
                    substats.append(
                        ModuleSubstat(
                            name=normalized,
                            rarity=rarity_value,
                            value=substat_value,
                        )
                    )
                i += 1
            inventory[module_name] = ModuleRecord(
                name=module_name,
                slot=slot_name,
                rarity=rarity,
                level=level,
                main_effect=main_effect,
                substats=substats,
            )
            continue
        i += 1

    for context in {"Farming", "Tourney", "Testing"}:
        loadout_by_context[context] = ModuleLoadout(
            slot=slot_name,
            primary=context_primary.get(context),
            assist=context_assist.get(context),
            assist_enabled=bool(assist_enabled),
            assist_stone_level=assist_stone_level,
            assist_cap_rarity=assist_cap_rarity,
        )
    return ModuleBlock(loadout_by_context=loadout_by_context, inventory=inventory)


def _looks_like_module_header(rows: List[List[str]], idx: int) -> bool:
    cell = rows[idx][0].strip()
    if not cell or cell in _RESERVED_ROWS or cell in {"Farming", "Tourney", "Testing"}:
        return False
    if idx + 2 >= len(rows):
        return False
    header = rows[idx + 1]
    if len(header) < 3:
        return False
    return header[0].strip() == "Rarity" and header[1].strip() == "Level"


def _resolve_module(
    module_name: str,
    slot_name: str,
    inventory: Mapping[str, ModuleRecord],
) -> ModuleRecord:
    if module_name not in inventory:
        raise SurvivabilityPipelineError(
            f"Unknown module {module_name!r} for slot {slot_name!r}."
        )
    return inventory[module_name]


def _resolve_substat_value(slot: str, substat_name: str, rarity: Rarity) -> float:
    if slot not in SUBSTAT_TABLES:
        raise SurvivabilityPipelineError(f"Missing substat table for slot {slot!r}.")
    slot_table = SUBSTAT_TABLES[slot]
    if substat_name not in slot_table:
        raise SurvivabilityPipelineError(
            f"Unknown substat {substat_name!r} for slot {slot!r}."
        )
    entry = slot_table[substat_name]
    if rarity not in entry.value:
        raise SurvivabilityPipelineError(
            f"Missing substat rarity {rarity.value!r} for {substat_name!r}."
        )
    raw = entry.value[rarity]
    if entry.unit == "pct":
        return float(raw) / 100.0
    if entry.unit == "mult":
        return float(raw)
    if entry.unit == "flat":
        return float(raw)
    if entry.unit == "count":
        return float(raw)
    if entry.unit == "sec":
        return float(raw)
    raise SurvivabilityPipelineError(
        f"Unsupported unit {entry.unit!r} for substat {substat_name!r}."
    )


def _apply_module_effects(
    accumulator: "_StatAccumulator",
    *,
    primary: ModuleRecord | None,
    assist: ModuleRecord | None,
    assist_enabled: bool,
    assist_level: int,
    assist_cap: Optional[Rarity],
    ids_snapshot: AccountSnapshot,
    allow_provisional: bool,
) -> None:
    if primary is None and assist is None:
        return
    assist_eff = _resolve_assist_efficiencies(
        labs=ids_snapshot.labs,
        slot=primary.slot if primary else assist.slot,
        assist_level=assist_level,
    )
    substat_eff = assist_eff.substat_eff

    if primary is not None and primary.slot == "Armor":
        multiplier = _armor_module_multiplier(
            ids_snapshot.labs,
            primary,
            assist if assist_enabled else None,
            assist_level,
            allow_provisional=allow_provisional,
        )
        accumulator.multiply("tower_hp", multiplier, "modules:armor_main_effect")

    if primary is not None:
        _apply_module_substats(accumulator, primary, is_assist=False, efficiency=1.0)
        _apply_unique_effects(accumulator, primary, is_assist=False, assist_cap=assist_cap)
    if assist is not None and assist_enabled:
        _apply_module_substats(
            accumulator, assist, is_assist=True, efficiency=substat_eff
        )
        _apply_unique_effects(accumulator, assist, is_assist=True, assist_cap=assist_cap)


def _apply_module_substats(
    accumulator: "_StatAccumulator",
    module: ModuleRecord,
    *,
    is_assist: bool,
    efficiency: float,
) -> None:
    active_count = max_active_substats_for_module_level(module.level)
    for substat in module.substats[:active_count]:
        value = substat.value * (efficiency if is_assist else 1.0)
        if substat.name == "Health Regen":
            accumulator.multiply("tower_regen", 1.0 + value, "modules:health_regen")
        elif substat.name == "Defense":
            accumulator.add("def_pct", value, "modules:defense")
        elif substat.name == "Wall Health":
            accumulator.multiply("wall_hp", 1.0 + value, "modules:wall_health")
        elif substat.name == "Thorns Damage":
            accumulator.add(
                "thorns_damage_mult", value, "modules:thorns_damage"
            )
        elif substat.name == "Enemy Attack Level Skip":
            accumulator.add("eals_pct", value, "modules:eals")
        elif substat.name == "Enemy Health Level Skip":
            accumulator.add("ehls_pct", value, "modules:ehls")


def _apply_unique_effects(
    accumulator: "_StatAccumulator",
    module: ModuleRecord,
    *,
    is_assist: bool,
    assist_cap: Optional[Rarity],
) -> None:
    effect = UNIQUE_EFFECTS.get(module.name)
    if effect is None:
        return
    if effect.effect_name != "wall_health_regen_mult_x":
        return
    rarity = module.rarity
    if is_assist and assist_cap is not None:
        rarity = _cap_rarity(rarity, assist_cap)
    multiplier = effect.value[rarity]
    accumulator.multiply("wall_hp", multiplier, "modules:unique:wall_health")
    accumulator.multiply("wall_regen", multiplier, "modules:unique:wall_regen")


def _resolve_assist_efficiencies(
    labs: Mapping[str, Optional[int]], slot: str, assist_level: int
) -> AssistEfficiencies:
    bonus_lab_key = f"Assist Module Bonus - {slot}"
    substat_lab_key = f"Assist Module Substats - {slot}"
    bonus_level = labs.get(bonus_lab_key)
    substat_level = labs.get(substat_lab_key)
    if bonus_level is None or substat_level is None:
        raise SurvivabilityPipelineError(
            f"Missing assist lab levels for {slot!r} in IDS."
        )
    labs = AssistLabLevels(
        bonus_level=bonus_level,
        substat_level=substat_level,
    )
    stone_pct = _assist_stone_percent(assist_level)
    inputs = AssistEfficiencyInputs(
        stone_bonus_percent=stone_pct,
        stone_substat_percent=stone_pct,
        labs=labs,
    )
    return compute_efficiencies(inputs)


def _armor_module_multiplier(
    labs: Mapping[str, Optional[int]],
    primary: ModuleRecord,
    assist: ModuleRecord | None,
    assist_level: int,
    *,
    allow_provisional: bool,
) -> float:
    if primary.slot != "Armor":
        return 1.0
    if not allow_provisional:
        raise SurvivabilityPipelineError(
            "Armor main-effect formula is EP-derived without a table. "
            "Set allow_provisional=True to apply it."
        )
    prim_bonus = primary.main_effect
    if assist is None:
        return prim_bonus
    if assist.slot != "Armor":
        raise SurvivabilityPipelineError(
            f"Assist module {assist.name!r} is not an Armor module."
        )
    stone_pct = _assist_stone_percent(assist_level)
    lab_level = labs.get("Assist Module Bonus - Armor")
    if lab_level is None:
        raise SurvivabilityPipelineError(
            "Missing Assist Module Bonus - Armor lab level in IDS."
        )
    labs = AssistLabLevels(
        bonus_level=lab_level,
        substat_level=0,
    )
    lab_pct = labs.bonus_percent
    assist_bonus = assist.main_effect
    assist_multiplier = ((assist_bonus - 1.0) * (1.0 + stone_pct + lab_pct) * 0.01) + 1.0
    return prim_bonus * assist_multiplier


def _assist_stone_percent(level: int) -> float:
    table_path = resolve_table_path("assist_stone_levels")
    if not table_path.exists():
        raise SurvivabilityPipelineError(
            f"Missing assist stone table: {table_path}"
        )
    with table_path.open("r", encoding="utf-8") as handle:
        header = handle.readline()
        if not header:
            raise SurvivabilityPipelineError("Assist stone table is empty.")
        for line in handle:
            parts = [cell.strip() for cell in line.split(",")]
            if len(parts) < 2:
                continue
            if int(float(parts[0])) == level:
                return float(parts[1])
    raise SurvivabilityPipelineError(
        f"Assist stone table missing level {level}."
    )


def _apply_card_effects(
    accumulator: "_StatAccumulator",
    ids_snapshot: AccountSnapshot,
    *,
    module_context: str,
    selected_cards: Iterable[str] | None,
) -> None:
    equipped = list(
        selected_cards or _resolve_equipped_cards(ids_snapshot, module_context)
    )
    for card_name in equipped:
        effect = _resolve_card_effect(card_name, ids_snapshot)
        if effect.card == "Health":
            if effect.unit != "mult":
                raise SurvivabilityPipelineError(
                    f"Health card has unsupported unit {effect.unit!r}."
                )
            accumulator.multiply("tower_hp", effect.value, "cards:health")
        elif effect.card == "Health Regen":
            if effect.unit != "mult":
                raise SurvivabilityPipelineError(
                    f"Health Regen card has unsupported unit {effect.unit!r}."
                )
            accumulator.multiply("tower_regen", effect.value, "cards:health_regen")
        elif effect.card == "Extra Defense":
            if effect.unit != "percent":
                raise SurvivabilityPipelineError(
                    f"Extra Defense card has unsupported unit {effect.unit!r}."
                )
            accumulator.add("def_pct", effect.value, "cards:extra_defense")
        else:
            try:
                card_canonical = resolve_named_entity("cards", effect.card)
            except KeyError as exc:
                raise SurvivabilityPipelineError(
                    f"Unsupported card for survivability pipeline: {card_name!r}."
                ) from exc
            if card_canonical == "CARD_PLASMA_CANNON":
                if effect.unit != "percent":
                    raise SurvivabilityPipelineError(
                        f"Plasma Cannon card has unsupported unit {effect.unit!r}."
                    )
                accumulator.add(
                    "plasma_cannon_damage_mult", effect.value, "cards:plasma_cannon"
                )
            else:
                raise SurvivabilityPipelineError(
                    f"Unsupported card for survivability pipeline: {card_name!r}."
                )


def _resolve_equipped_cards(
    ids_snapshot: AccountSnapshot, module_context: str
) -> List[str]:
    if module_context not in ids_snapshot.card_presets:
        raise SurvivabilityPipelineError(
            f"Missing card preset {module_context!r} in IDS snapshot."
        )
    return list(ids_snapshot.card_presets[module_context])


def _resolve_card_effect(
    card_name: str, ids_snapshot: AccountSnapshot
) -> CardEffect:
    entry = ids_snapshot.cards_inventory.get(card_name)
    if entry is None or entry.level is None:
        raise SurvivabilityPipelineError(
            f"Missing card {card_name!r} or card level in IDS."
        )
    return get_card_effect(card_name, entry.level)


class _StatAccumulator:
    def __init__(self) -> None:
        self._stats: Dict[str, Dict[str, float]] = {}

    def add(self, stat_id: str, delta: float, provenance: str) -> None:
        entry = self._stats.setdefault(stat_id, {"delta": 0.0, "mult": 1.0})
        entry["delta"] += float(delta)
        entry["provenance"] = provenance

    def multiply(self, stat_id: str, multiplier: float, provenance: str) -> None:
        entry = self._stats.setdefault(stat_id, {"delta": 0.0, "mult": 1.0})
        entry["mult"] *= float(multiplier)
        entry["provenance"] = provenance

    def to_stat_inputs(self) -> List[StatInput]:
        inputs: List[StatInput] = []
        for stat_id, entry in self._stats.items():
            delta = entry["delta"]
            mult = entry["mult"]
            inputs.append(
                StatInput(
                    stat_id=stat_id,
                    phase=Phase.START_OF_RUN,
                    loadout_delta=delta if delta != 0.0 else None,
                    enhancement_multiplier=mult if mult != 1.0 else None,
                    provenance=entry.get("provenance"),
                )
            )
        return inputs


def _slice_row(row: List[str], start: int, end: int) -> List[str]:
    padded = row + [""] * max(0, end + 1 - len(row))
    return padded[start : end + 1]


def _parse_optional_int(value: str) -> Optional[int]:
    candidate = value.strip()
    if candidate == "":
        return None
    return int(float(candidate))


def _parse_optional_float(value: str) -> Optional[float]:
    candidate = value.strip()
    if candidate == "":
        return None
    return float(candidate)


def _parse_rarity(value: str) -> Optional[Rarity]:
    candidate = value.strip()
    if candidate == "":
        return None
    core = candidate.split()[0].replace("+", "")
    for rarity in Rarity:
        if rarity.value.lower() == core.lower():
            return rarity
    raise SurvivabilityPipelineError(f"Unknown rarity {value!r} in IDS module data.")


def _cap_rarity(current: Rarity, cap: Rarity) -> Rarity:
    order = [Rarity.EPIC, Rarity.LEGENDARY, Rarity.MYTHIC, Rarity.ANCESTRAL]
    if current not in order or cap not in order:
        return current
    return current if order.index(current) <= order.index(cap) else cap


def _normalize_substat_name(name: str) -> str:
    mapping = {
        "Critical Factor": "Crit Factor",
        "MultiShot Chance": "Multishot Chance",
        "MultiShot Targets": "Multishot Targets",
        "Defense %": "Defense",
        "Thorn Damage": "Thorns Damage",
        "Package Chance": "Recovery Package Chance",
    }
    return mapping.get(name, name)


def compile_survivability_loadout_stat_inputs(
    ids_snapshot: AccountSnapshot,
    *,
    module_context: str = "Testing",
    module_overrides: Mapping[str, Mapping[str, Optional[str]]] | None = None,
    selected_cards: Iterable[str] | None = None,
    allow_provisional: bool = True,
) -> List[StatInput]:
    return _compile_loadout_stat_inputs(
        ids_snapshot,
        module_context=module_context,
        module_overrides=module_overrides,
        selected_cards=selected_cards,
        allow_provisional=allow_provisional,
    )


__all__ = [
    "SurvivabilityPipelineError",
    "build_survivability_report",
    "compile_survivability_loadout_stat_inputs",
]
