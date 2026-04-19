from __future__ import annotations

import pytest


def _contributors(**overrides):
    from qe.run_plan import SurvivabilityContributorBundle

    defaults = dict(
        base_wall_hp=100.0,
        workshop_wall_hp=200.0,
        lab_wall_hp=50.0,
        enhancement_wall_hp=25.0,
        module_flat_wall_hp=25.0,
        wall_hp_multiplier=2.0,
        base_wall_regen=10.0,
        workshop_wall_regen=5.0,
        lab_wall_regen=5.0,
        wall_regen_multiplier=3.0,
        wall_fortification_multiplier=1.5,
        tower_defense_pct=20.0,
        timed_dr_by_lane={"min": 0.0, "avg": 0.25, "max": 0.5},
    )
    defaults.update(overrides)
    return SurvivabilityContributorBundle(**defaults)


def _combat(**overrides):
    from simulators.evaluator_kernel import CombatInputs

    defaults = dict(
        plasma_cannon_effect_pct=0.0,
        tower_thorns_damage_pct=100.0,
        orb_boss_hit_pct=100.0,
        orb_boss_hits_per_second=10.0,
        electron_hits_per_second=10.0,
        boss_contact_time_seconds=1.0,
        boss_hit_interval_seconds=2.0,
        max_ttk_seconds=10.0,
    )
    defaults.update(overrides)
    return CombatInputs(**defaults)


def test_run_plan_compiles_identity_dependency_order_and_table1_registry():
    from qe.run_plan import CommonTrajectoryInputs, TABLE1_COLUMN_REGISTRY, build_common_trajectory, compile_run_plan

    inputs = CommonTrajectoryInputs(
        start_wave=1,
        end_wave=20,
        boss_interval_waves=10,
        attack_skip_chance=0.5,
        health_skip_chance=0.0,
        free_upgrade_chance_by_category={"attack": 1.0},
        category_track_order={"attack": ("Damage",)},
        track_max_levels={"Damage": 1},
        workshop_levels={"Damage": 0},
        perk_counts={"perk_a": 1},
        perk_contributions={"damage_multiplier": 1.2},
        survivability_contributors=_contributors(),
    )
    plan = compile_run_plan(inputs)
    table = build_common_trajectory(plan)

    assert plan.plan_id == compile_run_plan(inputs).plan_id
    assert plan.plan_version == "boss_waves.run_plan.v1"
    assert plan.dependency_order == (
        "checkpoint_grid",
        "wave_progression",
        "free_upgrade_generation",
        "free_upgrade_allocation",
        "workshop_levels",
        "compiled_perk_state",
        "survivability_contributors",
    )
    registry_ids = {spec.column_id for spec in TABLE1_COLUMN_REGISTRY}
    assert {"wave_progression", "free_upgrade_state", "compiled_perk_state", "survivability_contributors"} <= registry_ids
    first = table.rows[0]
    assert [row.display_wave for row in table.rows] == [10, 20]
    assert first.wave_progression.attack_wave == 5
    assert first.generated_free_upgrades_last_step["attack"] == 10
    assert first.allocated_free_upgrades_last_step["attack"] == 1
    assert first.unallocated_free_upgrades_last_step["attack"] == 9
    assert first.workshop_levels["Damage"] == 1
    assert first.compiled_perk_state.counts == {"perk_a": 1}
    assert first.compiled_perk_state.contributions == {"damage_multiplier": 1.2}
    assert first.survivability_contributors.base_wall_hp == 100.0


def test_table2_registry_derived_survivability_lanes_and_operator_handles():
    from qe.run_plan import CommonTrajectoryInputs, build_common_trajectory
    from simulators.evaluator_kernel import (
        LANE_ORDER,
        SUMMARY_LANE_ID,
        ScenarioOverlayInputs,
        ScenarioSurvivabilityTransforms,
        TABLE2_COLUMN_REGISTRY,
        build_scenario_overlay_table,
    )

    table1 = build_common_trajectory(
        CommonTrajectoryInputs(
            start_wave=1,
            end_wave=10,
            boss_interval_waves=10,
            attack_skip_chance=0.0,
            health_skip_chance=0.0,
            tier_column="Tier 1",
            perk_counts={"standard_damage": 1, "tradeoff_enemy_damage": 1},
            survivability_contributors=_contributors(),
        )
    )
    table2 = build_scenario_overlay_table(
        table1,
        scenario=ScenarioOverlayInputs(
            scenario_key="t1",
            tier_column="Tier 1",
            battle_conditions=("more_bosses",),
            heat={"enemy_attack": 1.0},
            tournament_perks_enabled=False,
            removed_perk_ids=("tradeoff_enemy_damage",),
            attack_skip_chance_delta=0.5,
            survivability_transforms=ScenarioSurvivabilityTransforms(
                wall_hp_multiplier=1.5,
                wall_regen_multiplier=2.0,
                enemy_attack_multiplier=2.0,
            ),
        ),
        combat=_combat(plasma_cannon_effect_pct=100.0),
    )

    row = table2.rows[0]
    registry_ids = {spec.column_id for spec in TABLE2_COLUMN_REGISTRY}
    assert {"final_wall_hp", "final_wall_regen", "lane_evaluations", "summary_lane_id", "summary_combat"} <= registry_ids
    assert row.effective_attack_skip_chance == 0.5
    assert row.effective_attack_wave == 5
    assert row.final_wall_hp == pytest.approx((100 + 200 + 50 + 25 + 25) * 2.0 * 1.5)
    assert row.final_wall_regen == pytest.approx((10 + 5 + 5) * 3.0 * 2.0)
    assert row.active_perk_counts == {"standard_damage": 1}
    assert LANE_ORDER == ("avg", "min", "max")
    assert [lane.lane_id for lane in row.lane_evaluations] == ["avg", "min", "max"]
    assert row.summary_lane_id == SUMMARY_LANE_ID == "avg"
    assert row.summary_combat.lane_id == "avg"
    assert row.operator_handle.handle_id == "boss:t1:10:avg"
    assert row.operator_handle.lane_handle_ids["min"] == "boss:t1:10:min"
    assert row.to_operator_row()["summary_lane_id"] == "avg"


def test_v21_ttk_is_event_only_and_fails_closed_without_event_horizon():
    from qe.run_plan import CommonTrajectoryInputs, build_common_trajectory
    from simulators.evaluator_kernel import KernelAmbiguityError, ScenarioOverlayInputs, build_scenario_overlay_table

    table1 = build_common_trajectory(
        CommonTrajectoryInputs(start_wave=1, end_wave=10, tier_column="Tier 1", survivability_contributors=_contributors())
    )
    table2 = build_scenario_overlay_table(
        table1,
        scenario=ScenarioOverlayInputs(scenario_key="pc", tier_column="Tier 1"),
        combat=_combat(plasma_cannon_effect_pct=100.0, orb_boss_hit_pct=0.0, tower_thorns_damage_pct=0.0),
    )
    assert table2.rows[0].summary_combat.ttk_seconds == 0.0

    with pytest.raises(KernelAmbiguityError, match="event horizon"):
        build_scenario_overlay_table(
            table1,
            scenario=ScenarioOverlayInputs(scenario_key="no-kill-events", tier_column="Tier 1"),
            combat=_combat(
                plasma_cannon_effect_pct=0.0,
                orb_boss_hit_pct=0.0,
                tower_thorns_damage_pct=0.0,
                boss_contact_time_seconds=None,
                max_ttk_seconds=1.0,
            ),
        )


def test_scenario_overlay_fails_closed_on_ambiguous_survivability_perks_and_lane_invariant():
    from qe.run_plan import CommonTrajectoryInputs, build_common_trajectory, compile_run_plan
    from simulators.evaluator_kernel import (
        KernelAmbiguityError,
        ScenarioOverlayInputs,
        ScenarioSurvivabilityTransforms,
        build_scenario_overlay_table,
    )

    with pytest.raises(ValueError, match="base_wall_hp"):
        compile_run_plan(CommonTrajectoryInputs(start_wave=1, end_wave=10, survivability_contributors=_contributors(base_wall_hp=-1.0)))

    table1 = build_common_trajectory(
        CommonTrajectoryInputs(start_wave=1, end_wave=10, tier_column="Tier 1", perk_counts={"known_perk": 1}, survivability_contributors=_contributors())
    )
    with pytest.raises(KernelAmbiguityError, match="removed_perk_ids"):
        build_scenario_overlay_table(
            table1,
            scenario=ScenarioOverlayInputs("missing-perk-mask", "Tier 1", tournament_perks_enabled=False),
            combat=_combat(plasma_cannon_effect_pct=100.0),
        )
    with pytest.raises(KernelAmbiguityError, match="unknown compiled perk"):
        build_scenario_overlay_table(
            table1,
            scenario=ScenarioOverlayInputs("unknown-perk-mask", "Tier 1", tournament_perks_enabled=False, removed_perk_ids=("missing",)),
            combat=_combat(plasma_cannon_effect_pct=100.0),
        )
    with pytest.raises(KernelAmbiguityError, match="lane DR invariant"):
        build_scenario_overlay_table(
            table1,
            scenario=ScenarioOverlayInputs(
                "bad-lane-dr",
                "Tier 1",
                survivability_transforms=ScenarioSurvivabilityTransforms(dr_bonus_by_lane={"min": 0.9, "avg": 0.0, "max": 0.0}),
            ),
            combat=_combat(plasma_cannon_effect_pct=100.0),
        )


def test_scenario_overlay_recomputes_effective_waves_from_table1_start_baseline():
    from qe.run_plan import CommonTrajectoryInputs, build_common_trajectory
    from simulators.evaluator_kernel import ScenarioOverlayInputs, build_scenario_overlay_table

    table1 = build_common_trajectory(
        CommonTrajectoryInputs(start_wave=10, end_wave=10, tier_column="Tier 1", survivability_contributors=_contributors())
    )
    table2 = build_scenario_overlay_table(
        table1,
        scenario=ScenarioOverlayInputs("start-10", "Tier 1", attack_skip_chance_delta=1.0),
        combat=_combat(plasma_cannon_effect_pct=100.0),
    )

    assert table2.rows[0].effective_attack_wave == 9
    assert table2.rows[0].effective_health_wave == 10
