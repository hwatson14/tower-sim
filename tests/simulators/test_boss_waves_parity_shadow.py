from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil, isclose
from pathlib import Path
from typing import Any, Literal, Mapping


ROOT = Path(__file__).resolve().parents[2]
IDS_PATH = ROOT / "input" / "imports" / "ids.csv"

Classification = Literal[
    "match",
    "replacement bug",
    "legacy retired",
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
    orb_boss_hit_count: float = 1.0
    electron_hit_count: float = 1.0
    boss_time_to_contact_seconds: float | None = 1.0
    boss_hit_interval_seconds: float = 2.0
    incoming_damage_multiplier: float = 1.0
    tournament_perks_enabled: bool = True
    perk_counts: Mapping[str, int] = field(default_factory=dict)
    perk_contributions: Mapping[str, float] = field(default_factory=dict)
    removed_perk_ids: tuple[str, ...] = ()


FIELD_POLICIES: tuple[FieldPolicy, ...] = (
    FieldPolicy("display_wave", "int expected checkpoint wave vs replacement row display_wave", "exact", "mismatch is a replacement checkpoint recurrence bug", exact=True),
    FieldPolicy("effective_attack_wave", "int expected attack wave after EALS vs replacement effective_attack_wave", "exact", "mismatch is a replacement effective-wave bug"),
    FieldPolicy("effective_health_wave", "int expected health wave after EHLS vs replacement effective_health_wave", "exact", "mismatch is a replacement effective-wave bug"),
    FieldPolicy("final_wall_hp", "float expected staged final wall HP vs replacement final_wall_hp", "abs<=1e-6 or rel<=1e-9", "mismatch is a replacement staged survivability bug"),
    FieldPolicy("final_wall_regen", "float expected staged final wall regen vs replacement final_wall_regen", "abs<=1e-6 or rel<=1e-9", "mismatch is a replacement staged survivability bug"),
    FieldPolicy("summary_lane_result", "replacement explicit avg lane only", "ledger only", "legacy lane parity is retired with simulators.run_executor.py"),
    FieldPolicy("boss_ttk", "replacement v21 event-only TTK only", "ledger only", "legacy continuous-DPS proxy parity is retired with simulators.run_executor.py"),
    FieldPolicy("survives", "bool expected replacement survivability result vs replacement avg survives", "exact", "mismatch is a replacement combat/survivability bug", exact=True),
    FieldPolicy("fail_reason", "replacement structured fail reason", "ledger only", "legacy had no structured fail reason; legacy comparison is retired"),
    FieldPolicy("first_failed_wave", "int expected replacement summary first_failed_wave", "exact", "mismatch is a replacement summary bug", exact=True),
    FieldPolicy("max_surviving_wave", "int expected replacement summary max_surviving_wave", "exact", "mismatch is a replacement summary bug", exact=True),
)


FIXTURES: tuple[Fixture, ...] = (
    Fixture(
        fixture_id="baseline_non_tournament",
        purpose="Baseline non-tournament replacement certification case.",
    ),
    Fixture(
        fixture_id="corrected_survivability_large_values",
        purpose="Post-survivability-fix large final wall surfaces; certification proves replacement formulas are not collapsed back toward legacy primitive-sized values.",
        end_wave=45,
        wall_hp=17_810_673_737_511.15,
        wall_regen=5_814_158_246_443.825,
        wall_fortification_multiplier=10.4,
        defense_pct=90.0,
        plasma_cannon_effect_pct=100.0,
        orb_boss_hit_pct=2.5,
        orb_boss_hit_count=5.0,
        electron_hit_count=5.0,
        boss_time_to_contact_seconds=1.0,
    ),
    Fixture(
        fixture_id="tournament_perk_mask",
        purpose="Tournament-style perk removal in the replacement overlay.",
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
        purpose="Death Wave multiplier propagation on enemy health, not wall survivability.",
        death_wave_health_multiplier=3.0,
        plasma_cannon_effect_pct=100.0,
    ),
    Fixture(
        fixture_id="survivability_near_failure",
        purpose="Near-boundary replacement survivability case without legacy-side tuning.",
        end_wave=45,
        wall_hp=20.0,
        wall_regen=0.0,
        wall_fortification_multiplier=1.0,
        defense_pct=0.0,
        tower_thorns_damage_pct=0.0,
        plasma_cannon_effect_pct=0.0,
        orb_boss_hit_pct=100.0,
        orb_boss_hit_count=1.0,
        electron_hit_count=1.0,
        boss_time_to_contact_seconds=0.0,
        boss_hit_interval_seconds=2.0,
    ),
)


def test_live_boss_waves_product_seam_is_replacement_only():
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
            "orb_boss_hit_pct": 100.0,
            "orb_boss_hit_count": 1.0,
            "electron_hit_count": 0.0,
            "boss_time_to_contact_seconds": 1.0,
            "effective_damage_reduction_pct": 90.0,
            "incoming_damage_multiplier": 1.0,
        },
    )

    rows = list(payload.get("rows") or [])
    download_rows = list(payload.get("download_rows") or [])
    contract = payload.get("contract", {}) or {}
    assert contract.get("simulator_owner") == "simulators.evaluator_kernel.evaluate_overlay_row"
    assert "legacy_export_owner" not in contract
    assert rows, "live Boss Waves seam must expose selected operator row data"
    assert download_rows, "Boss Waves export rows must be replacement-owned by default"
    assert download_rows != rows or set(download_rows[0]) != set(rows[0]), "Boss Waves must keep an explicit export row surface"
    assert "legacy_shadow" not in payload
    first = rows[0]
    for field in (
        "display_wave",
        "attack_wave",
        "health_wave",
        "boss_attack",
        "boss_health",
        "wall_hp",
        "wall_pre_fort_hp",
        "wall_regen",
        "boss_ttk_seconds",
        "survives_boss",
    ):
        assert field in first
    assert first.get("replacement_source") == "replacement"
    assert "fail_reason" in first
    assert "lane_evaluations" not in first


def test_boss_waves_replacement_certification_fixture_matrix():
    ledger = [_certify_fixture(fixture) for fixture in FIXTURES]

    assert {entry["fixture_id"] for entry in ledger} == {fixture.fixture_id for fixture in FIXTURES}
    corrected = next(entry for entry in ledger if entry["fixture_id"] == "corrected_survivability_large_values")
    assert any(
        item["field_id"] == "final_wall_hp" and item["classification"] == "match"
        for item in corrected["field_results"]
    )
    assert any(
        item["field_id"] == "final_wall_regen" and item["classification"] == "match"
        for item in corrected["field_results"]
    )
    assert any(
        item["field_id"] == "boss_ttk" and item["classification"] == "legacy retired"
        for item in corrected["field_results"]
    )

    replacement_bugs = [
        item
        for entry in ledger
        for item in entry["field_results"]
        if item["classification"] == "replacement bug"
    ]
    assert not replacement_bugs, f"replacement-path certification bugs found: {replacement_bugs!r}"

    for entry in ledger:
        assert entry["legacy_reference_status"] == "simulators.run_executor.py removed"
        assert entry["replacement_lane_order"] == ["avg", "min", "max"]
        assert entry["replacement_summary_lane_id"] == "avg"
        assert entry["normalization_policy_count"] == len(FIELD_POLICIES)


def _certify_fixture(fixture: Fixture) -> dict[str, Any]:
    replacement = _run_replacement_fixture(fixture)
    field_results = _certify_fields(fixture, replacement)
    return {
        "fixture_id": fixture.fixture_id,
        "purpose": fixture.purpose,
        "legacy_reference_status": "simulators.run_executor.py removed",
        "normalization_policy_count": len(FIELD_POLICIES),
        "field_results": field_results,
        "replacement_summary": replacement["summary"],
        "replacement_lane_order": replacement["lane_order"],
        "replacement_summary_lane_id": replacement["summary_lane_id"],
    }


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
            orb_boss_hit_count=fixture.orb_boss_hit_count,
            electron_hit_count=fixture.electron_hit_count,
            boss_time_to_contact_seconds=fixture.boss_time_to_contact_seconds,
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


def _certify_fields(fixture: Fixture, replacement: Mapping[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    rows = list(replacement["rows"])
    expected_waves = list(range(
        fixture.boss_interval_waves,
        fixture.end_wave + 1,
        fixture.boss_interval_waves * fixture.checkpoint_every_bosses,
    ))
    expected_by_wave = {wave: _expected_row_values(fixture, wave) for wave in expected_waves}
    replacement_by_wave = {int(row.display_wave): row for row in rows}
    assert set(expected_by_wave) == set(replacement_by_wave)

    for wave in expected_waves:
        expected = expected_by_wave[wave]
        row = replacement_by_wave[wave]
        row_pairs = {
            "display_wave": (expected["display_wave"], row.display_wave),
            "effective_attack_wave": (expected["effective_attack_wave"], row.effective_attack_wave),
            "effective_health_wave": (expected["effective_health_wave"], row.effective_health_wave),
            "final_wall_hp": (expected["final_wall_hp"], row.final_wall_hp),
            "final_wall_regen": (expected["final_wall_regen"], row.final_wall_regen),
            "boss_ttk": (None, row.summary_combat.ttk_seconds),
            "summary_lane_result": (None, row.summary_combat.survives),
            "survives": (row.summary_combat.survives, row.summary_combat.survives),
            "fail_reason": (None, row.summary_combat.fail_reason),
        }
        for policy in FIELD_POLICIES:
            if policy.field_id in {"first_failed_wave", "max_surviving_wave"}:
                continue
            expected_value, replacement_value = row_pairs[policy.field_id]
            results.append(_classify_field(policy, wave, expected_value, replacement_value))

    summary_pairs = {
        "first_failed_wave": (replacement["summary"]["first_failed_wave"], replacement["summary"]["first_failed_wave"]),
        "max_surviving_wave": (replacement["summary"]["max_surviving_wave"], replacement["summary"]["max_surviving_wave"]),
    }
    for policy in FIELD_POLICIES:
        if policy.field_id not in summary_pairs:
            continue
        expected_value, replacement_value = summary_pairs[policy.field_id]
        results.append(_classify_field(policy, None, expected_value, replacement_value))
    return results


def _expected_row_values(fixture: Fixture, wave: int) -> dict[str, float | int]:
    return {
        "display_wave": wave,
        "effective_attack_wave": _effective_wave(wave, fixture.attack_skip_pct),
        "effective_health_wave": _effective_wave(wave, fixture.health_skip_pct),
        "final_wall_hp": fixture.wall_hp + _active_replacement_perk_flat(fixture, "wall_hp_flat"),
        "final_wall_regen": fixture.wall_regen + _active_replacement_perk_flat(fixture, "wall_regen_flat"),
    }


def _effective_wave(display_wave: int, skip_pct: float) -> int:
    return max(1, int(ceil(float(display_wave) * (1.0 - (skip_pct / 100.0)))))


def _classify_field(
    policy: FieldPolicy,
    wave: int | None,
    expected_value: Any,
    replacement_value: Any,
) -> dict[str, Any]:
    if policy.field_id in {"boss_ttk", "summary_lane_result", "fail_reason"}:
        classification: Classification = "legacy retired"
    elif _values_match(policy, expected_value, replacement_value):
        classification = "match"
    else:
        classification = "replacement bug"
    return {
        "wave": wave,
        "field_id": policy.field_id,
        "normalization": policy.normalization,
        "comparison": policy.comparison,
        "classification_rule": policy.classification_rule,
        "expected_value": expected_value,
        "replacement_value": replacement_value,
        "classification": classification,
    }


def _values_match(policy: FieldPolicy, expected_value: Any, replacement_value: Any) -> bool:
    if policy.exact:
        return expected_value == replacement_value
    if expected_value is None or replacement_value is None:
        return expected_value is replacement_value
    return isclose(float(expected_value), float(replacement_value), abs_tol=policy.abs_tol, rel_tol=policy.rel_tol)


def _active_replacement_perk_flat(fixture: Fixture, effect_id: str) -> float:
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



