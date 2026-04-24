from __future__ import annotations

from dataclasses import replace

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
        orb_boss_hit_count=10,
        electron_hit_count=10,
        boss_time_to_contact_seconds=1.0,
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
        perk_contributions={"perk_a:wall_hp_flat": 50.0, "perk_a:wall_regen_multiplier": 1.25},
        survivability_contributors=_contributors(),
        death_wave_health_multiplier=2.5,
    )
    plan = compile_run_plan(inputs)
    table = build_common_trajectory(plan)

    assert plan.plan_id == compile_run_plan(inputs).plan_id
    assert plan.plan_version == "boss_waves.run_plan.v1"
    assert plan.death_wave_health_max_multiplier == 2.5
    assert plan.death_wave_health_max_wave == 1000
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
    assert {"wave_progression", "free_upgrade_state", "compiled_perk_state", "survivability_contributors", "death_wave_health_multiplier"} <= registry_ids
    first = table.rows[0]
    assert [row.display_wave for row in table.rows] == [10, 20]
    assert first.wave_progression.attack_wave == 5
    assert first.generated_free_upgrades_last_step["attack"] == 10
    assert first.allocated_free_upgrades_last_step["attack"] == 1
    assert first.unallocated_free_upgrades_last_step["attack"] == 9
    assert first.workshop_levels["Damage"] == 1
    assert first.compiled_perk_state.counts == {"perk_a": 1}
    assert first.compiled_perk_state.contributions == {"perk_a:wall_hp_flat": 50.0, "perk_a:wall_regen_multiplier": 1.25}
    assert first.survivability_contributors.base_wall_hp == 100.0
    assert first.survivability_contributors.wall_hp_primitives == {
        "base_wall_hp": 100.0,
        "workshop_wall_hp": 200.0,
        "lab_wall_hp": 50.0,
        "enhancement_wall_hp": 25.0,
        "module_flat_wall_hp": 25.0,
    }
    assert first.death_wave_health_multiplier == pytest.approx(1.015)


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
            perk_contributions={
                "standard_damage:wall_hp_flat": 50.0,
                "standard_damage:wall_regen_flat": 2.0,
                "standard_defense:tower_defense_pct_points_add": 10.0,
                "tradeoff_enemy_damage:wall_hp_flat": 999.0,
                "tradeoff_enemy_damage:wall_regen_multiplier": 99.0,
            },
            survivability_contributors=_contributors(),
            death_wave_health_multiplier=3.0,
        )
    )
    baseline_table1 = build_common_trajectory(
        CommonTrajectoryInputs(
            start_wave=1,
            end_wave=10,
            boss_interval_waves=10,
            attack_skip_chance=0.0,
            health_skip_chance=0.0,
            tier_column="Tier 1",
            perk_counts={"standard_damage": 1, "tradeoff_enemy_damage": 1},
            perk_contributions={
                "standard_damage:wall_hp_flat": 50.0,
                "standard_damage:wall_regen_flat": 2.0,
                "standard_defense:tower_defense_pct_points_add": 10.0,
                "tradeoff_enemy_damage:wall_hp_flat": 999.0,
                "tradeoff_enemy_damage:wall_regen_multiplier": 99.0,
            },
            survivability_contributors=_contributors(),
            death_wave_health_multiplier=1.0,
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
    baseline_row = build_scenario_overlay_table(
        baseline_table1,
        scenario=ScenarioOverlayInputs(
            scenario_key="t1-baseline",
            tier_column="Tier 1",
            tournament_perks_enabled=False,
            removed_perk_ids=("tradeoff_enemy_damage",),
        ),
        combat=_combat(plasma_cannon_effect_pct=100.0),
    ).rows[0]
    registry_ids = {spec.column_id for spec in TABLE2_COLUMN_REGISTRY}
    assert {"active_perk_contributions", "final_wall_hp", "final_wall_regen", "lane_evaluations", "summary_lane_id", "summary_combat"} <= registry_ids
    assert row.effective_attack_skip_chance == 0.5
    assert row.effective_attack_wave == 5
    assert row.final_wall_hp == pytest.approx((100 + 200 + 50 + 25 + 25 + 50) * 2.0 * 1.5)
    assert row.final_wall_regen == pytest.approx((10 + 5 + 5 + 2) * 3.0 * 2.0)
    assert row.active_perk_counts == {"standard_damage": 1}
    assert row.active_perk_contributions == {
        "standard_damage:wall_hp_flat": 50.0,
        "standard_damage:wall_regen_flat": 2.0,
        "standard_defense:tower_defense_pct_points_add": 10.0,
    }
    assert row.damage_reduction_pct == pytest.approx(47.5)
    assert row.enemy_health == pytest.approx(baseline_row.enemy_health)
    assert LANE_ORDER == ("avg", "min", "max")
    assert [lane.lane_id for lane in row.lane_evaluations] == ["avg", "min", "max"]
    assert row.summary_lane_id == SUMMARY_LANE_ID == "avg"
    assert row.summary_combat.lane_id == "avg"
    assert row.operator_handle.handle_id == "boss:t1:10:avg"
    assert row.operator_handle.lane_handle_ids["min"] == "boss:t1:10:min"
    assert row.to_operator_row()["summary_lane_id"] == "avg"


def test_table1_rederives_survivability_from_evolving_workshop_and_perk_state():
    from qe.run_plan import CommonTrajectoryInputs, SurvivabilityContributorBundle, build_common_trajectory
    from simulators.evaluator_kernel import ScenarioOverlayInputs, build_scenario_overlay_table

    table1 = build_common_trajectory(
        CommonTrajectoryInputs(
            start_wave=1,
            end_wave=2,
            boss_interval_waves=1,
            tier_column="Tier 1",
            free_upgrade_chance_by_category={"defense": 1.0},
            category_track_order={"defense": ("Wall Health", "Health Regen")},
            track_max_levels={"Wall Health": 10, "Health Regen": 10},
            workshop_levels={"Wall Health": 1, "Health Regen": 1},
            perk_counts_by_wave={2: {"regen_perk": 1}},
            perk_contributions_by_wave={2: {"regen_perk:wall_regen_multiplier": 2.0}},
            survivability_contributors=SurvivabilityContributorBundle(
                base_wall_hp=0.0,
                workshop_wall_hp=100.0,
                wall_hp_workshop_track="Wall Health",
                wall_hp_workshop_baseline_level=1,
                wall_hp_workshop_value_per_level=25.0,
                base_wall_regen=0.0,
                workshop_wall_regen=10.0,
                wall_regen_workshop_track="Health Regen",
                wall_regen_workshop_baseline_level=1,
                wall_regen_workshop_value_per_level=5.0,
                wall_fortification_multiplier=1.0,
                tower_defense_pct=90.0,
            ),
        )
    )

    assert [row.workshop_levels for row in table1.rows] == [
        {"Wall Health": 2, "Health Regen": 1},
        {"Wall Health": 2, "Health Regen": 2},
    ]
    assert [row.survivability_contributors.workshop_wall_hp for row in table1.rows] == [125.0, 125.0]
    assert [row.survivability_contributors.workshop_wall_regen for row in table1.rows] == [10.0, 15.0]
    assert [row.compiled_perk_state.contributions for row in table1.rows] == [
        {},
        {"regen_perk:wall_regen_multiplier": 2.0},
    ]

    table2 = build_scenario_overlay_table(
        table1,
        scenario=ScenarioOverlayInputs("row-evolve", "Tier 1"),
        combat=_combat(plasma_cannon_effect_pct=100.0),
    )
    assert [row.final_wall_hp for row in table2.rows] == [125.0, 125.0]
    assert [row.final_wall_regen for row in table2.rows] == [10.0, 30.0]


def test_table1_rederives_wall_hp_from_evolving_tower_hp_and_wall_health_workshops():
    from qe.run_plan import CommonTrajectoryInputs, SurvivabilityContributorBundle, build_common_trajectory, workshop_value_for_level
    from simulators.evaluator_kernel import ScenarioOverlayInputs, build_scenario_overlay_table

    tower_multiplier = 2.0
    static_ratio = 100.0
    wall_multiplier = 1.5
    start_tower_hp = workshop_value_for_level("Health", 5700) * tower_multiplier
    start_wall_ratio = static_ratio + workshop_value_for_level("Wall Health", 1340)
    table1 = build_common_trajectory(
        CommonTrajectoryInputs(
            start_wave=1,
            end_wave=2,
            boss_interval_waves=1,
            checkpoint_every_bosses=1,
            tier_column="Tier 1",
            free_upgrade_chance_by_category={"defense": 1.0},
            category_track_order={"defense": ("Health", "Wall Health")},
            track_max_levels={"Health": 5701, "Wall Health": 1341},
            workshop_levels={"Health": 5700, "Wall Health": 1340},
            survivability_contributors=SurvivabilityContributorBundle(
                base_wall_hp=0.0,
                workshop_wall_hp=start_tower_hp * (start_wall_ratio / 100.0) * wall_multiplier,
                wall_hp_workshop_track="Wall Health",
                wall_hp_workshop_baseline_level=1340,
                wall_hp_static_ratio_percent_points=static_ratio,
                wall_hp_effect_multiplier=wall_multiplier,
                tower_hp_workshop_track="Health",
                tower_hp_workshop_baseline_level=5700,
                tower_hp_workshop_multiplier=tower_multiplier,
                wall_fortification_multiplier=1.0,
                tower_defense_pct=90.0,
            ),
        )
    )

    table2 = build_scenario_overlay_table(
        table1,
        scenario=ScenarioOverlayInputs("tower-hp-row-evolve", "Tier 1"),
        combat=_combat(plasma_cannon_effect_pct=100.0),
    )

    first_expected = (
        workshop_value_for_level("Health", 5701)
        * tower_multiplier
        * ((static_ratio + workshop_value_for_level("Wall Health", 1340)) / 100.0)
        * wall_multiplier
    )
    second_expected = (
        workshop_value_for_level("Health", 5701)
        * tower_multiplier
        * ((static_ratio + workshop_value_for_level("Wall Health", 1341)) / 100.0)
        * wall_multiplier
    )
    assert [row.workshop_levels for row in table1.rows] == [
        {"Health": 5701, "Wall Health": 1340},
        {"Health": 5701, "Wall Health": 1341},
    ]
    assert [row.final_wall_hp for row in table2.rows] == pytest.approx([first_expected, second_expected])


def test_cf_and_bh_duration_perk_contributions_recompute_timed_dr_per_row():
    from qe.run_plan import CommonTrajectoryInputs, SurvivabilityContributorBundle, build_common_trajectory
    from simulators.evaluator_kernel import ScenarioOverlayInputs, build_scenario_overlay_table

    table1 = build_common_trajectory(
        CommonTrajectoryInputs(
            start_wave=1,
            end_wave=2,
            boss_interval_waves=1,
            tier_column="Tier 1",
            perk_counts_by_wave={2: {"PERK_BLACK_HOLE_DURATION_12_0S": 1, "PERK_CHRONO_FIELD_DURATION_5S": 1}},
            perk_contributions_by_wave={
                2: {
                    "PERK_BLACK_HOLE_DURATION_12_0S:black_hole_duration_seconds_add": 10.0,
                    "PERK_CHRONO_FIELD_DURATION_5S:chrono_field_duration_seconds_add": 10.0,
                }
            },
            survivability_contributors=SurvivabilityContributorBundle(
                base_wall_hp=10_000.0,
                wall_fortification_multiplier=1.0,
                tower_defense_pct=0.0,
                black_hole_damage_reduction_pct=50.0,
                black_hole_duration_seconds=10.0,
                black_hole_cooldown_seconds=100.0,
                chrono_field_damage_reduction_pct=20.0,
                chrono_field_duration_seconds=10.0,
                chrono_field_cooldown_seconds=100.0,
            ),
        )
    )
    table2 = build_scenario_overlay_table(
        table1,
        scenario=ScenarioOverlayInputs("timed-dr-perks", "Tier 1"),
        combat=_combat(plasma_cannon_effect_pct=100.0),
    )

    assert table2.rows[0].damage_reduction_pct == pytest.approx(100.0 * (1.0 - ((1.0 - 0.05) * (1.0 - 0.02))))
    assert table2.rows[1].damage_reduction_pct == pytest.approx(100.0 * (1.0 - ((1.0 - 0.10) * (1.0 - 0.04))))
    assert table2.rows[1].damage_reduction_pct > table2.rows[0].damage_reduction_pct


def test_death_wave_multiplier_feeds_table1_tower_hp_wall_hp_not_enemy_health_or_regen():
    from qe.run_plan import CommonTrajectoryInputs, SurvivabilityContributorBundle, build_common_trajectory, workshop_value_for_level
    from simulators.evaluator_kernel import ScenarioOverlayInputs, build_scenario_overlay_table

    contributors = SurvivabilityContributorBundle(
        base_wall_hp=0.0,
        workshop_wall_hp=workshop_value_for_level("Health", 100) * 2.0,
        wall_hp_workshop_track="Wall Health",
        wall_hp_workshop_baseline_level=10,
        wall_hp_static_ratio_percent_points=100.0,
        wall_hp_effect_multiplier=1.0,
        tower_hp_workshop_track="Health",
        tower_hp_workshop_baseline_level=100,
        tower_hp_workshop_multiplier=1.0,
        base_wall_regen=100.0,
        wall_fortification_multiplier=1.0,
        tower_defense_pct=90.0,
    )
    base = build_scenario_overlay_table(
            build_common_trajectory(CommonTrajectoryInputs(start_wave=1, end_wave=10, tier_column="Tier 1", survivability_contributors=contributors, death_wave_health_max_multiplier=1.0)),
        scenario=ScenarioOverlayInputs("base", "Tier 1"),
        combat=_combat(plasma_cannon_effect_pct=100.0),
    ).rows[0]
    death_wave = build_scenario_overlay_table(
            build_common_trajectory(CommonTrajectoryInputs(start_wave=1, end_wave=10, tier_column="Tier 1", survivability_contributors=contributors, death_wave_health_max_multiplier=10.0, death_wave_health_max_wave=10)),
        scenario=ScenarioOverlayInputs("dw", "Tier 1"),
        combat=_combat(plasma_cannon_effect_pct=100.0),
    ).rows[0]

    assert death_wave.enemy_health == pytest.approx(base.enemy_health)
    assert death_wave.final_wall_hp == pytest.approx(base.final_wall_hp * 10.0)
    assert death_wave.final_wall_regen == base.final_wall_regen


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

    with pytest.raises(KernelAmbiguityError, match="cannot be killed"):
        build_scenario_overlay_table(
            table1,
            scenario=ScenarioOverlayInputs(scenario_key="no-kill-events", tier_column="Tier 1"),
            combat=_combat(
                plasma_cannon_effect_pct=0.0,
                orb_boss_hit_pct=0.0,
                tower_thorns_damage_pct=0.0,
                boss_time_to_contact_seconds=None,
                max_ttk_seconds=1.0,
            ),
        )

    contact_kill = build_scenario_overlay_table(
        table1,
        scenario=ScenarioOverlayInputs(scenario_key="contact-kill", tier_column="Tier 1"),
        combat=_combat(
            plasma_cannon_effect_pct=0.0,
            orb_boss_hit_pct=0.0,
            tower_thorns_damage_pct=100.0,
            boss_time_to_contact_seconds=5.0,
            boss_hit_interval_seconds=2.0,
            max_ttk_seconds=200.0,
        ),
    )
    assert contact_kill.rows[0].summary_combat.ttk_seconds >= 5.0
    assert contact_kill.rows[0].summary_combat.contact_thorns_kill_seconds >= 5.0


def test_v21_ttk_includes_contact_thorns_and_uses_fractional_kill_threshold():
    from simulators.evaluator_kernel import (
        CombatInputs,
        _simulate_boss_contact_thorns_kill_seconds,
        _simulate_boss_contact_thorns_result,
        _simulate_boss_pre_contact_kill_state,
        _simulate_boss_ttk,
    )

    combat = CombatInputs(
        plasma_cannon_effect_pct=54.0,
        orb_boss_total_damage_pct=2.0,
        electron_total_damage_pct=7.5,
        tower_thorns_damage_pct=121.0,
        boss_time_to_contact_seconds=1.0,
        boss_hit_interval_seconds=2.0,
        max_ttk_seconds=600.0,
    )

    low_hp_state = _simulate_boss_pre_contact_kill_state(enemy_health=1e12, combat=combat)
    high_hp_state = _simulate_boss_pre_contact_kill_state(enemy_health=1e30, combat=combat)
    low_hp_contact = _simulate_boss_contact_thorns_kill_seconds(
        remaining_hp=low_hp_state.remaining_hp,
        starting_hp=low_hp_state.starting_hp,
        kill_threshold=low_hp_state.kill_threshold,
        combat=combat,
    )
    high_hp_contact = _simulate_boss_contact_thorns_kill_seconds(
        remaining_hp=high_hp_state.remaining_hp,
        starting_hp=high_hp_state.starting_hp,
        kill_threshold=high_hp_state.kill_threshold,
        combat=combat,
    )
    high_hp_contact_result = _simulate_boss_contact_thorns_result(
        remaining_hp=high_hp_state.remaining_hp,
        starting_hp=high_hp_state.starting_hp,
        kill_threshold=high_hp_state.kill_threshold,
        combat=combat,
    )

    assert _simulate_boss_ttk(enemy_health=1e30, combat=combat) == pytest.approx(high_hp_contact)
    assert high_hp_contact == pytest.approx(low_hp_contact)
    assert high_hp_contact == pytest.approx(1.0)
    assert high_hp_state.damage_breakdown.plasma_cannon_damage == pytest.approx(5.4e29)
    assert high_hp_state.damage_breakdown.orb_damage == pytest.approx(9.2e27)
    assert high_hp_state.damage_breakdown.electron_damage == pytest.approx(3.381e28)
    assert high_hp_state.damage_breakdown.plasma_cannon_damage_pct == pytest.approx(54.0)
    assert high_hp_state.damage_breakdown.orb_damage_pct == pytest.approx(2.0)
    assert high_hp_state.damage_breakdown.electron_damage_pct == pytest.approx(7.5)
    assert high_hp_contact_result.kill_seconds == pytest.approx(high_hp_contact)
    assert high_hp_contact_result.thorns_hits == 1
    assert high_hp_contact_result.thorns_damage_pct == pytest.approx(high_hp_contact_result.thorns_damage / 1e30 * 100.0)
    assert high_hp_contact_result.thorns_damage_pct == pytest.approx(41.699)
    assert high_hp_contact_result.thorns_expected_damage_pct_from_hits == pytest.approx(high_hp_contact_result.thorns_damage_pct)
    assert (
        high_hp_state.damage_breakdown.plasma_cannon_damage
        + high_hp_state.damage_breakdown.orb_damage
        + high_hp_state.damage_breakdown.electron_damage
        + high_hp_contact_result.thorns_damage
    ) == pytest.approx(1e30, rel=1e-8)


def test_wall_thorns_contact_damage_is_derived_from_tower_thorns_and_wall_thorns_lab():
    from qe.run_plan import derive_wall_thorns_contact_damage_pct

    assert derive_wall_thorns_contact_damage_pct(
        tower_thorns_damage_pct=121.0,
        wall_thorns_level=16,
    ) == pytest.approx(19.36)
    with pytest.raises(ValueError, match="wall_thorns_level"):
        derive_wall_thorns_contact_damage_pct(tower_thorns_damage_pct=121.0, wall_thorns_level=-1)


def test_contact_resolution_applies_sharp_fortitude_wall_thorns_increase_per_contact_hit():
    from simulators.evaluator_kernel import CombatInputs, _simulate_boss_contact_thorns_kill_seconds, _simulate_boss_pre_contact_kill_state, _simulate_boss_ttk

    base = dict(
        plasma_cannon_effect_pct=54.0,
        orb_boss_total_damage_pct=2.0,
        electron_total_damage_pct=7.5,
        tower_thorns_damage_pct=19.36,
        boss_time_to_contact_seconds=1.0,
        boss_hit_interval_seconds=2.0,
        max_ttk_seconds=600.0,
    )

    base_state = _simulate_boss_pre_contact_kill_state(enemy_health=1e30, combat=CombatInputs(**base))
    sharp_state = _simulate_boss_pre_contact_kill_state(
        enemy_health=1e30,
        combat=CombatInputs(**base, wall_thorns_damage_increase_per_hit=0.01),
    )
    without_sharp_fortitude = _simulate_boss_contact_thorns_kill_seconds(
        remaining_hp=base_state.remaining_hp,
        starting_hp=base_state.starting_hp,
        kill_threshold=base_state.kill_threshold,
        combat=CombatInputs(**base),
    )
    with_sharp_fortitude = _simulate_boss_contact_thorns_kill_seconds(
        remaining_hp=sharp_state.remaining_hp,
        starting_hp=sharp_state.starting_hp,
        kill_threshold=sharp_state.kill_threshold,
        combat=CombatInputs(**base, wall_thorns_damage_increase_per_hit=0.01),
    )

    assert without_sharp_fortitude == pytest.approx(9.0)
    assert with_sharp_fortitude == pytest.approx(7.0)
    assert _simulate_boss_ttk(
        enemy_health=1e30,
        combat=CombatInputs(**base, wall_thorns_damage_increase_per_hit=0.01),
    ) == pytest.approx(7.0)
    assert with_sharp_fortitude < without_sharp_fortitude


def test_contact_resolution_reports_expected_thorns_damage_from_total_hits():
    from simulators.evaluator_kernel import CombatInputs, _simulate_boss_contact_thorns_result, _simulate_boss_pre_contact_kill_state

    combat = CombatInputs(
        plasma_cannon_effect_pct=54.0,
        orb_boss_total_damage_pct=2.0,
        electron_total_damage_pct=7.5,
        tower_thorns_damage_pct=19.36,
        boss_time_to_contact_seconds=1.0,
        boss_hit_interval_seconds=2.0,
        max_ttk_seconds=600.0,
        wall_thorns_damage_increase_per_hit=0.01,
    )
    state = _simulate_boss_pre_contact_kill_state(enemy_health=1e30, combat=combat)
    result = _simulate_boss_contact_thorns_result(
        remaining_hp=state.remaining_hp,
        starting_hp=state.starting_hp,
        kill_threshold=state.kill_threshold,
        combat=combat,
    )

    assert result.thorns_hits == 4
    assert result.kill_seconds == pytest.approx(7.0)
    assert result.thorns_damage_pct == pytest.approx(41.699)
    assert result.thorns_expected_damage_pct_from_hits == pytest.approx(result.thorns_damage_pct)


def test_v21_ttk_uses_total_orb_and_electron_hits_not_rates():
    from qe.run_plan import CommonTrajectoryInputs, SurvivabilityContributorBundle, build_common_trajectory
    from simulators.evaluator_kernel import ScenarioOverlayInputs, build_scenario_overlay_table

    table1 = build_common_trajectory(
        CommonTrajectoryInputs(
            start_wave=1,
            end_wave=10,
            tier_column="Tier 1",
            survivability_contributors=SurvivabilityContributorBundle(
                base_wall_hp=10_000.0,
                base_wall_regen=0.0,
                wall_fortification_multiplier=1.0,
                tower_defense_pct=90.0,
            ),
        )
    )

    killed_by_opening_totals = build_scenario_overlay_table(
        table1,
        scenario=ScenarioOverlayInputs("total-events", "Tier 1"),
        combat=_combat(
            plasma_cannon_effect_pct=0.0,
            tower_thorns_damage_pct=0.0,
            orb_boss_hit_pct=100.0,
            orb_boss_hit_count=1,
            electron_hit_count=0,
            boss_time_to_contact_seconds=3.0,
            max_ttk_seconds=10.0,
        ),
    )

    assert killed_by_opening_totals.rows[0].summary_combat.ttk_seconds == pytest.approx(3.0)
    assert killed_by_opening_totals.rows[0].summary_combat.boss_hits_taken == 0


def test_v21_ttk_accepts_total_orb_and_electron_damage_without_rate_or_count():
    from qe.run_plan import CommonTrajectoryInputs, SurvivabilityContributorBundle, build_common_trajectory
    from simulators.evaluator_kernel import ScenarioOverlayInputs, build_scenario_overlay_table

    table1 = build_common_trajectory(
        CommonTrajectoryInputs(
            start_wave=1,
            end_wave=10,
            tier_column="Tier 1",
            survivability_contributors=SurvivabilityContributorBundle(
                base_wall_hp=10_000.0,
                wall_fortification_multiplier=1.0,
                tower_defense_pct=90.0,
            ),
        )
    )

    killed_by_total_damage = build_scenario_overlay_table(
        table1,
        scenario=ScenarioOverlayInputs("total-damage", "Tier 1"),
        combat=_combat(
            plasma_cannon_effect_pct=0.0,
            tower_thorns_damage_pct=0.0,
            orb_boss_hit_pct=None,
            orb_boss_hit_count=None,
            electron_hit_count=None,
            orb_boss_total_damage_pct=100.0,
            electron_total_damage_pct=0.0,
            boss_time_to_contact_seconds=4.0,
            max_ttk_seconds=10.0,
        ),
    )

    assert killed_by_total_damage.rows[0].summary_combat.ttk_seconds == pytest.approx(4.0)
    assert killed_by_total_damage.rows[0].summary_combat.boss_hits_taken == 0


def test_orb_electron_pre_contact_kill_requires_contact_timing():
    from qe.run_plan import CommonTrajectoryInputs, SurvivabilityContributorBundle, build_common_trajectory
    from simulators.evaluator_kernel import KernelAmbiguityError, ScenarioOverlayInputs, build_scenario_overlay_table

    table1 = build_common_trajectory(
        CommonTrajectoryInputs(
            start_wave=1,
            end_wave=10,
            tier_column="Tier 1",
            survivability_contributors=SurvivabilityContributorBundle(
                base_wall_hp=10_000.0,
                wall_fortification_multiplier=1.0,
                tower_defense_pct=90.0,
            ),
        )
    )

    with pytest.raises(KernelAmbiguityError, match="boss_time_to_contact_seconds is required"):
        build_scenario_overlay_table(
            table1,
            scenario=ScenarioOverlayInputs("missing-contact-time", "Tier 1"),
            combat=_combat(
                plasma_cannon_effect_pct=0.0,
                tower_thorns_damage_pct=0.0,
                orb_boss_total_damage_pct=100.0,
                electron_total_damage_pct=0.0,
                boss_time_to_contact_seconds=None,
                max_ttk_seconds=10.0,
            ),
        )


def test_boss_hits_to_player_match_wall_thorns_contact_events():
    from qe.run_plan import CommonTrajectoryInputs, SurvivabilityContributorBundle, build_common_trajectory
    from simulators.evaluator_kernel import ScenarioOverlayInputs, build_scenario_overlay_table

    table1 = build_common_trajectory(
        CommonTrajectoryInputs(
            start_wave=1,
            end_wave=10,
            tier_column="Tier 1",
            survivability_contributors=SurvivabilityContributorBundle(
                base_wall_hp=1_000_000_000.0,
                base_wall_regen=0.0,
                wall_fortification_multiplier=1.0,
                tower_defense_pct=0.0,
            ),
        )
    )

    table2 = build_scenario_overlay_table(
        table1,
        scenario=ScenarioOverlayInputs("contact-hit-count", "Tier 1"),
        combat=_combat(
            plasma_cannon_effect_pct=54.0,
            orb_boss_total_damage_pct=2.0,
            electron_total_damage_pct=7.5,
            tower_thorns_damage_pct=19.36,
            boss_time_to_contact_seconds=1.0,
            boss_hit_interval_seconds=2.0,
            max_ttk_seconds=600.0,
            wall_thorns_damage_increase_per_hit=0.01,
        ),
    )

    row = table2.rows[0]
    assert row.boss_damage_breakdown.thorns_hits == 4
    assert row.summary_combat.boss_hits_taken == row.boss_damage_breakdown.thorns_hits
    assert row.summary_combat.ttk_seconds == pytest.approx(7.0)


def test_enemy_attack_and_health_tables_interpolate_between_rows():
    from simulators.evaluator_kernel import ENEMY_DAMAGE_TABLE, ENEMY_HEALTH_TABLE, _required_enemy_value

    attack_90 = _required_enemy_value(ENEMY_DAMAGE_TABLE, 90, "Tier 1")
    attack_100 = _required_enemy_value(ENEMY_DAMAGE_TABLE, 100, "Tier 1")
    health_90 = _required_enemy_value(ENEMY_HEALTH_TABLE, 90, "Tier 1")
    health_100 = _required_enemy_value(ENEMY_HEALTH_TABLE, 100, "Tier 1")

    assert _required_enemy_value(ENEMY_DAMAGE_TABLE, 95, "Tier 1") == pytest.approx((attack_90 + attack_100) / 2.0)
    assert _required_enemy_value(ENEMY_HEALTH_TABLE, 95, "Tier 1") == pytest.approx((health_90 + health_100) / 2.0)


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
    with pytest.raises(ValueError, match="source_policy"):
        compile_run_plan(CommonTrajectoryInputs(start_wave=1, end_wave=10, survivability_contributors=_contributors(source_policy="unsupported")))
    with pytest.raises(ValueError, match="unsupported perk contribution"):
        compile_run_plan(CommonTrajectoryInputs(start_wave=1, end_wave=10, perk_contributions={"perk_a:generic_multiplier": 1.2}, survivability_contributors=_contributors()))

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


def test_registry_validation_rejects_missing_fields_and_bad_key_contracts():
    from qe.run_plan import (
        ColumnFormulaSpec,
        CommonTrajectoryInputs,
        TABLE1_COLUMN_REGISTRY,
        build_common_trajectory,
        validate_table1_registry,
    )
    from simulators.evaluator_kernel import (
        ScenarioOverlayInputs,
        ScenarioOverlayTable,
        TABLE2_COLUMN_REGISTRY,
        build_scenario_overlay_table,
        validate_table2_registry,
    )

    table1 = build_common_trajectory(CommonTrajectoryInputs(start_wave=1, end_wave=10, tier_column="Tier 1", survivability_contributors=_contributors()))
    bad_table1_registry = tuple(
        replace(spec, recurrence_type="decorative_only") if spec.column_id == "wave_progression" else spec
        for spec in TABLE1_COLUMN_REGISTRY
    )
    with pytest.raises(ValueError, match="recurrence_type"):
        validate_table1_registry(replace(table1, column_registry=bad_table1_registry))
    with pytest.raises(ValueError, match="missing registered columns"):
        validate_table1_registry(
            replace(
                table1,
                column_registry=TABLE1_COLUMN_REGISTRY
                + (ColumnFormulaSpec("unemitted_required_field", "qe", "float", (), "identity", "compile_once", "plan_static"),),
            )
        )

    table2 = build_scenario_overlay_table(
        table1,
        scenario=ScenarioOverlayInputs("registry", "Tier 1"),
        combat=_combat(plasma_cannon_effect_pct=100.0),
    )
    bad_table2_registry = tuple(
        replace(spec, dependencies=("table1.survivability_contributors",)) if spec.column_id == "final_wall_hp" else spec
        for spec in TABLE2_COLUMN_REGISTRY
    )
    with pytest.raises(ValueError, match="dependencies"):
        validate_table2_registry(replace(table2, column_registry=bad_table2_registry))
    with pytest.raises(ValueError, match="missing registered columns"):
        validate_table2_registry(
            replace(
                table2,
                column_registry=TABLE2_COLUMN_REGISTRY
                + (ColumnFormulaSpec("unemitted_overlay_field", "simulators", "float", (), "identity", "per_overlay_row", "row_static"),),
            )
        )

