from __future__ import annotations

from dataclasses import dataclass, field
from math import isclose
from pathlib import Path
from typing import Any, Literal, Mapping

import pytest


ROOT = Path(__file__).resolve().parents[2]
IDS_PATH = ROOT / "input" / "imports" / "ids.csv"

Classification = Literal[
    "match",
    "replacement bug",
    "legacy bug",
    "intentional model improvement",
    "unresolved semantic difference",
    "not directly comparable",
]


@dataclass(frozen=True)
class FieldPolicy:
    field_id: str
    normalization: str
    comparison: str
    classification_rule: str
    exact: bool = False
    abs_tol: float = 1e-6
    rel_tol: float = 1e-9


@dataclass(frozen=True)
class Fixture:
    fixture_id: str
    purpose: str
    end_wave: int = 27
    tier_column: str = "Tier 1"
    boss_interval_waves: int = 9
    checkpoint_every_bosses: int = 1
    attack_skip_pct: float = 0.0
    health_skip_pct: float = 0.0
    death_wave_health_multiplier: float = 1.0
    wall_hp: float = 1_000.0
    wall_regen: float = 10.0
    wall_fortification_multiplier: float = 1.0
    defense_pct: float = 50.0
    avg_timed_dr: float = 0.0
    min_timed_dr: float = 0.0
    max_timed_dr: float = 0.0
    plasma_cannon_effect_pct: float = 0.0
    tower_thorns_damage_pct: float = 100.0
    orb_boss_hit_pct: float = 100.0
    orb_boss_hits_per_second: float = 1.0
    electron_hits_per_second: float = 1.0
    boss_contact_time_seconds: float | None = 1.0
    boss_hit_interval_seconds: float = 2.0
    incoming_damage_multiplier: float = 1.0
    tournament_perks_enabled: bool = True
    perk_counts: Mapping[str, int] = field(default_factory=dict)
    perk_contributions: Mapping[str, float] = field(default_factory=dict)
    removed_perk_ids: tuple[str, ...] = ()


FIELD_POLICIES: tuple[FieldPolicy, ...] = (
    FieldPolicy("display_wave", "int legacy row display_wave vs replacement row display_wave", "exact", "mismatch is a replacement or progression-fixture bug", exact=True),
    FieldPolicy("effective_attack_wave", "int legacy attack_wave vs replacement effective_attack_wave", "exact", "mismatch is a replacement effective-wave bug unless fixture cannot express legacy skip"),
    FieldPolicy("effective_health_wave", "int legacy health_wave vs replacement effective_health_wave", "exact", "mismatch is a replacement effective-wave bug unless fixture cannot express legacy skip"),
    FieldPolicy("enemy_attack", "float legacy boss_attack vs replacement enemy_attack", "abs<=1e-6 or rel<=1e-9", "mismatch is a replacement enemy-table/scenario-overlay bug"),
    FieldPolicy("enemy_health", "float legacy boss_health vs replacement enemy_health", "abs<=1e-6 or rel<=1e-9 when Death Wave multiplier is 1", "Death Wave-scaled rows are not directly comparable because legacy has no fixture input for that multiplier"),
    FieldPolicy("final_wall_hp", "float legacy wall_hp vs replacement final_wall_hp", "abs<=1e-6 or rel<=1e-9", "mismatch is a replacement staged survivability bug when fixture uses shared primitives"),
    FieldPolicy("final_wall_regen", "float legacy wall_regen vs replacement final_wall_regen", "abs<=1e-6 or rel<=1e-9", "mismatch is a replacement staged survivability bug when fixture uses shared primitives"),
    FieldPolicy("boss_ttk", "float legacy boss_ttk_seconds_used vs replacement summary ttk", "ledger only", "not directly comparable by default because live legacy contract includes continuous_runtime_dps_proxy while replacement v21 forbids it"),
    FieldPolicy("summary_lane_result", "legacy canonical row result vs replacement explicit avg lane", "ledger only", "not directly comparable because legacy has no avg/min/max lane model"),
    FieldPolicy("survives", "bool legacy survives_boss vs replacement avg survives", "exact", "mismatch is an unresolved semantic difference unless tied to a known non-comparable TTK/Death Wave input", exact=True),
    FieldPolicy("fail_reason", "legacy has no structured fail reason; replacement avg fail_reason", "ledger only", "not directly comparable"),
    FieldPolicy("first_failed_wave", "int legacy summary first_failed_wave vs replacement derived first_failed_wave", "exact when fixture has comparable combat/enemy semantics", "mismatch is unresolved when Death Wave or TTK semantics differ", exact=True),
    FieldPolicy("max_surviving_wave", "int legacy summary max_surviving_wave vs replacement derived max_surviving_wave", "exact when fixture has comparable combat/enemy semantics", "mismatch is unresolved when Death Wave or TTK semantics differ", exact=True),
)


FIXTURES: tuple[Fixture, ...] = (
    Fixture(
        fixture_id="baseline_non_tournament",
        purpose="Baseline non-tournament case with shared wall, enemy, skip, and event-only-compatible combat inputs.",
    ),
    Fixture(
        fixture_id="tournament_perk_mask",
        purpose="Tournament-style perk removal; final wall surfaces remain comparable, internal perk masking is replacement-only.",
        tournament_perks_enabled=False,
        perk_counts={"standard_wall": 1, "tradeoff_wall": 1},
        perk_contributions={
            "standard_wall:wall_hp_flat": 50.0,
            "standard_wall:wall_regen_flat": 2.0,
            "tradeoff_wall:wall_hp_flat": 999.0,
        },
        removed_perk_ids=("tradeoff_wall",),
        wall_hp=1_000.0,
        wall_regen=10.0,
    ),
    Fixture(
        fixture_id="skip_effective_waves",
        purpose="Non-zero EALS/EHLS effective-wave behavior.",
        end_wave=45,
        attack_skip_pct=25.0,
        health_skip_pct=50.0,
    ),
    Fixture(
        fixture_id="death_wave_scaled",
        purpose="Death Wave multiplier propagation; enemy-health direct parity is limited by legacy input surface.",
        death_wave_health_multiplier=3.0,
        plasma_cannon_effect_pct=100.0,
    ),
    Fixture(
        fixture_id="survivability_near_failure",
        purpose="Shared near-boundary survivability case without asymmetric replacement-side tuning.",
        end_wave=45,
        wall_hp=20.0,
        wall_regen=0.0,
        wall_fortification_multiplier=1.0,
        defense_pct=0.0,
        tower_thorns_damage_pct=0.0,
        plasma_cannon_effect_pct=0.0,
        orb_boss_hit_pct=100.0,
        orb_boss_hits_per_second=1.0,
        electron_hits_per_second=1.0,
        boss_contact_time_seconds=0.0,
        boss_hit_interval_seconds=2.0,
    ),
)


def test_live_boss_waves_product_seam_exposes_shadow_validation_subset_read_only():
    from app.models import PipelineRunRequest
    from app.pipeline import build_boss_wave_payload

    payload = build_boss_wave_payload(
        PipelineRunRequest(ids=IDS_PATH, out=ROOT / "out"),
        preset_name="Farming",
        tier_number=14,
        end_wave=18,
        boss_wave_step=1,
        stop_on_failure=False,
        scenario_runtime_inputs={
            "orb_boss_hit_pct": 2.5,
            "orb_boss_hits_per_second": 5.0,
            "electron_hits_per_second": 5.0,
            "boss_contact_time_seconds": 1.0,
            "effective_damage_reduction_pct": 90.0,
            "incoming_damage_multiplier": 1.0,
        },
    )

    rows = list(payload.get("rows") or [])
    legacy_download_rows = list(payload.get("download_rows") or [])
    contract = payload.get("contract", {}) or {}
    assert contract.get("simulator_owner") == "simulators.evaluator_kernel.evaluate_overlay_row"
    assert contract.get("legacy_export_owner") == "simulators.run_executor.build_boss_wave_table_payload"
    assert rows, "live Boss Waves seam must expose selected operator row data"
    assert legacy_download_rows, "Phase 2A must keep legacy-compatible rows available for shadow/export validation"
    first = rows[0]
    for field in (
        "display_wave",
        "attack_wave",
        "health_wave",
        "boss_attack",
        "boss_health",
        "wall_hp",
        "wall_regen",
        "boss_ttk_seconds_used",
        "survives_boss",
    ):
        assert field in first
    assert first.get("phase2a_source") == "phase2a_replacement"
    assert "fail_reason" in first
    assert "lane_evaluations" not in first


def test_boss_waves_replacement_shadow_parity_fixture_matrix():
    ledger = [_compare_fixture(fixture) for fixture in FIXTURES]

    assert {entry["fixture_id"] for entry in ledger} == {fixture.fixture_id for fixture in FIXTURES}
    assert any(
        item["field_id"] == "enemy_health" and item["classification"] == "not directly comparable"
        for entry in ledger
        for item in entry["field_results"]
    )
    assert any(
        item["field_id"] == "boss_ttk" and item["classification"] == "not directly comparable"
        for entry in ledger
        for item in entry["field_results"]
    )

    replacement_bugs = [
        item
        for entry in ledger
        for item in entry["field_results"]
        if item["classification"] == "replacement bug"
    ]
    assert not replacement_bugs, f"replacement-path parity bugs found: {replacement_bugs!r}"

    for entry in ledger:
        assert entry["replacement_lane_order"] == ["avg", "min", "max"]
        assert entry["replacement_summary_lane_id"] == "avg"
        assert entry["normalization_policy_count"] == len(FIELD_POLICIES)


def _compare_fixture(fixture: Fixture) -> dict[str, Any]:
    legacy = _run_legacy_fixture(fixture)
    replacement = _run_replacement_fixture(fixture)
    field_results = _compare_fields(fixture, legacy, replacement)
    return {
        "fixture_id": fixture.fixture_id,
        "purpose": fixture.purpose,
        "normalization_policy_count": len(FIELD_POLICIES),
        "field_results": field_results,
        "legacy_summary": legacy["summary"],
        "replacement_summary": replacement["summary"],
        "replacement_lane_order": replacement["lane_order"],
        "replacement_summary_lane_id": replacement["summary_lane_id"],
    }


def _run_legacy_fixture(fixture: Fixture) -> dict[str, Any]:
    from input.loader import load_inputs
    from input.runtime_state import build_runtime_state
    from simulators.contracts import PerformanceMetrics, PerkState, WaveCheckpoint
    from simulators.run_executor import RunToMaxConfig, build_boss_wave_table_payload, build_start_of_run_state

    class _FakeRow:
        def __init__(self, value: float):
            self.final_value = value

    class _FakeStatBook:
        def __init__(self):
            wall_hp = fixture.wall_hp + _active_legacy_perk_flat(fixture, "wall_hp_flat")
            wall_regen = fixture.wall_regen + _active_legacy_perk_flat(fixture, "wall_regen_flat")
            self.rows = {
                "state::tower.enemy_attack_level_skip_pct": _FakeRow(fixture.attack_skip_pct),
                "state::tower.enemy_health_level_skip_pct": _FakeRow(fixture.health_skip_pct),
                "state::tower.free_attack_upgrade_chance_pct": _FakeRow(0.0),
                "state::tower.free_defense_upgrade_chance_pct": _FakeRow(0.0),
                "state::tower.free_utility_upgrade_chance_pct": _FakeRow(0.0),
                "state::wall.hp": _FakeRow(wall_hp),
                "state::wall.regen": _FakeRow(wall_regen),
                "state::wall.fortification_multiplier": _FakeRow(fixture.wall_fortification_multiplier),
                "state::tower.defense_pct": _FakeRow(fixture.defense_pct),
                "state::tower.thorns_damage_pct": _FakeRow(fixture.tower_thorns_damage_pct),
                "state::cards.plasma_cannon.effect_pct": _FakeRow(fixture.plasma_cannon_effect_pct),
            }
            self.diagnostics = {"delta_fallback_used": False}

    class _FakeSnapshot:
        def __init__(self, wave: int):
            self.checkpoint = WaveCheckpoint(display_wave=wave)
            self.resolved_statbook = _FakeStatBook()
            self.scenario_context = {}
            self.timing_context = type("Timing", (), {})()
            self.geometry_context = {}
            self.combat_runtime = type(
                "Combat",
                (),
                {
                    "orb_boss_hit_pct": fixture.orb_boss_hit_pct,
                    "orb_boss_hits_per_second": fixture.orb_boss_hits_per_second,
                    "electron_hits_per_second": fixture.electron_hits_per_second,
                    "boss_contact_time_seconds": fixture.boss_contact_time_seconds,
                    "boss_hit_interval_seconds": fixture.boss_hit_interval_seconds,
                    "effective_damage_reduction_pct": _fixture_avg_dr_fraction(fixture) * 100.0,
                    "incoming_damage_multiplier": fixture.incoming_damage_multiplier,
                },
            )()
            self.metrics = PerformanceMetrics(row_resolution_ms=0.0, qe_resolution_count=1, timing_recompute_count=1)

    bundle = load_inputs()
    account_state = build_runtime_state(bundle.ids_raw, loadout_config=bundle.loadout_config, perk_config=bundle.perk_config)
    projected = build_start_of_run_state(
        account_state,
        preset_name="Farming",
        perk_state=PerkState(wave=0, counts=dict(fixture.perk_counts), dirty=False),
    )

    payload = build_boss_wave_table_payload(
        account_state=account_state,
        initial_projected_state=projected,
        config=RunToMaxConfig(
            execution_mode="table_sweep",
            preset_name="Farming",
            mode_id="farming" if fixture.tournament_perks_enabled else "tournament",
            tier_number=int(fixture.tier_column.split()[-1]),
            tier_column=fixture.tier_column,
            start_wave=1,
            end_wave=fixture.end_wave,
            boss_interval_waves=fixture.boss_interval_waves,
            checkpoint_every_bosses=fixture.checkpoint_every_bosses,
            perks_enabled=fixture.tournament_perks_enabled,
            state_mode="start_of_run",
            max_ttk_seconds=10.0,
        ),
        row_resolver=lambda normalized: _FakeSnapshot(normalized.checkpoint.display_wave),
        stop_on_failure=False,
    )
    return {"rows": list(payload["rows"]), "summary": dict(payload["summary"])}


def _run_replacement_fixture(fixture: Fixture) -> dict[str, Any]:
    from qe.run_plan import CommonTrajectoryInputs, SurvivabilityContributorBundle, build_common_trajectory
    from simulators.evaluator_kernel import (
        LANE_ORDER,
        SUMMARY_LANE_ID,
        CombatInputs,
        ScenarioOverlayInputs,
        build_scenario_overlay_table,
    )

    contributors = SurvivabilityContributorBundle(
        base_wall_hp=fixture.wall_hp,
        base_wall_regen=fixture.wall_regen,
        wall_fortification_multiplier=fixture.wall_fortification_multiplier,
        tower_defense_pct=fixture.defense_pct,
        timed_dr_by_lane={"min": fixture.min_timed_dr, "avg": fixture.avg_timed_dr, "max": fixture.max_timed_dr},
    )
    table1 = build_common_trajectory(
        CommonTrajectoryInputs(
            start_wave=1,
            end_wave=fixture.end_wave,
            boss_interval_waves=fixture.boss_interval_waves,
            checkpoint_every_bosses=fixture.checkpoint_every_bosses,
            tier_column=fixture.tier_column,
            attack_skip_chance=fixture.attack_skip_pct / 100.0,
            health_skip_chance=fixture.health_skip_pct / 100.0,
            perk_counts=dict(fixture.perk_counts),
            perk_contributions=dict(fixture.perk_contributions),
            survivability_contributors=contributors,
            death_wave_health_multiplier=fixture.death_wave_health_multiplier,
        )
    )
    table2 = build_scenario_overlay_table(
        table1,
        scenario=ScenarioOverlayInputs(
            scenario_key=fixture.fixture_id,
            tier_column=fixture.tier_column,
            tournament_perks_enabled=fixture.tournament_perks_enabled,
            removed_perk_ids=fixture.removed_perk_ids,
        ),
        combat=CombatInputs(
            plasma_cannon_effect_pct=fixture.plasma_cannon_effect_pct,
            tower_thorns_damage_pct=fixture.tower_thorns_damage_pct,
            orb_boss_hit_pct=fixture.orb_boss_hit_pct,
            orb_boss_hits_per_second=fixture.orb_boss_hits_per_second,
            electron_hits_per_second=fixture.electron_hits_per_second,
            boss_contact_time_seconds=fixture.boss_contact_time_seconds,
            boss_hit_interval_seconds=fixture.boss_hit_interval_seconds,
            max_ttk_seconds=10.0,
        ),
    )
    rows = list(table2.rows)
    surviving = [row.display_wave for row in rows if row.summary_combat.survives]
    failed = [row.display_wave for row in rows if not row.summary_combat.survives]
    return {
        "rows": rows,
        "summary": {
            "max_surviving_wave": max(surviving, default=0),
            "first_failed_wave": min(failed, default=0),
        },
        "lane_order": list(LANE_ORDER),
        "summary_lane_id": SUMMARY_LANE_ID,
    }


def _compare_fields(fixture: Fixture, legacy: Mapping[str, Any], replacement: Mapping[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    legacy_rows = {int(row["display_wave"]): row for row in legacy["rows"]}
    replacement_rows = {int(row.display_wave): row for row in replacement["rows"]}
    common_waves = sorted(set(legacy_rows) & set(replacement_rows))
    assert common_waves, f"fixture {fixture.fixture_id} produced no shared checkpoint waves"

    for wave in common_waves:
        legacy_row = legacy_rows[wave]
        replacement_row = replacement_rows[wave]
        row_pairs = {
            "display_wave": (legacy_row["display_wave"], replacement_row.display_wave),
            "effective_attack_wave": (legacy_row["attack_wave"], replacement_row.effective_attack_wave),
            "effective_health_wave": (legacy_row["health_wave"], replacement_row.effective_health_wave),
            "enemy_attack": (legacy_row["boss_attack"], replacement_row.enemy_attack),
            "enemy_health": (legacy_row["boss_health"], replacement_row.enemy_health),
            "final_wall_hp": (legacy_row["wall_hp"], replacement_row.final_wall_hp),
            "final_wall_regen": (legacy_row["wall_regen"], replacement_row.final_wall_regen),
            "boss_ttk": (legacy_row["boss_ttk_seconds_used"], replacement_row.summary_combat.ttk_seconds),
            "summary_lane_result": (legacy_row["survives_boss"], replacement_row.summary_combat.survives),
            "survives": (legacy_row["survives_boss"], replacement_row.summary_combat.survives),
            "fail_reason": (None, replacement_row.summary_combat.fail_reason),
        }
        for policy in FIELD_POLICIES:
            if policy.field_id in {"first_failed_wave", "max_surviving_wave"}:
                continue
            legacy_value, replacement_value = row_pairs[policy.field_id]
            results.append(_classify_field(fixture, policy, wave, legacy_value, replacement_value))

    summary_pairs = {
        "first_failed_wave": (legacy["summary"]["first_failed_wave"], replacement["summary"]["first_failed_wave"]),
        "max_surviving_wave": (legacy["summary"]["max_surviving_wave"], replacement["summary"]["max_surviving_wave"]),
    }
    for policy in FIELD_POLICIES:
        if policy.field_id not in summary_pairs:
            continue
        legacy_value, replacement_value = summary_pairs[policy.field_id]
        results.append(_classify_field(fixture, policy, None, legacy_value, replacement_value))
    return results


def _classify_field(
    fixture: Fixture,
    policy: FieldPolicy,
    wave: int | None,
    legacy_value: Any,
    replacement_value: Any,
) -> dict[str, Any]:
    comparable = _is_directly_comparable(fixture, policy.field_id)
    if not comparable:
        classification: Classification = "not directly comparable"
    elif _values_match(policy, legacy_value, replacement_value):
        classification = "match"
    elif policy.field_id in {"survives", "first_failed_wave", "max_surviving_wave"} and fixture.death_wave_health_multiplier != 1.0:
        classification = "unresolved semantic difference"
    else:
        classification = "replacement bug"
    return {
        "fixture_id": fixture.fixture_id,
        "wave": wave,
        "field_id": policy.field_id,
        "normalization": policy.normalization,
        "comparison": policy.comparison,
        "classification_rule": policy.classification_rule,
        "legacy_value": legacy_value,
        "replacement_value": replacement_value,
        "classification": classification,
    }


def _is_directly_comparable(fixture: Fixture, field_id: str) -> bool:
    if field_id in {"boss_ttk", "summary_lane_result", "fail_reason"}:
        return False
    if field_id == "enemy_health" and fixture.death_wave_health_multiplier != 1.0:
        return False
    return True


def _values_match(policy: FieldPolicy, legacy_value: Any, replacement_value: Any) -> bool:
    if policy.exact:
        return legacy_value == replacement_value
    if legacy_value is None or replacement_value is None:
        return legacy_value is replacement_value
    return isclose(float(legacy_value), float(replacement_value), abs_tol=policy.abs_tol, rel_tol=policy.rel_tol)


def _fixture_avg_dr_fraction(fixture: Fixture) -> float:
    defense = max(0.0, min(100.0, fixture.defense_pct)) / 100.0
    timed = max(0.0, min(1.0, fixture.avg_timed_dr))
    return max(0.0, min(1.0, 1.0 - ((1.0 - defense) * (1.0 - timed))))


def _active_legacy_perk_flat(fixture: Fixture, effect_id: str) -> float:
    removed = set(fixture.removed_perk_ids if not fixture.tournament_perks_enabled else ())
    total = 0.0
    for contribution_id, value in fixture.perk_contributions.items():
        owner, _, effect = str(contribution_id).partition(":")
        if not effect:
            effect = owner
            owner = ""
        if owner in removed:
            continue
        if effect == effect_id:
            total += float(value)
    return total
