from __future__ import annotations

import pytest
from pathlib import Path

from tower_sim.engines.stat_pipeline import (
    build_canonical_stat_pipeline,
    build_canonical_stat_pipeline_for_problem_spec,
)
import tower_sim.engines.stat_pipeline as stat_pipeline_module
import tower_sim.engines.stat_input_compiler as stat_input_compiler_module
from tower_sim.loaders.account_snapshot_compiler import compile_account_snapshot
from tower_sim.engines.combat_stat_derivation import build_canonical_wave_snapshot
from tower_sim.engines.stat_engine import StatEngine
from tower_sim.registry.stat_registry import Phase
from tower_sim.loaders.ids_parser import parse_ids
from tower_sim.run.spec_loader import load_problem_spec


def _snapshot():
    return compile_account_snapshot(parse_ids(Path("tests/fixtures/tower-sim-data/_IDS.csv")))


def test_build_canonical_stat_pipeline_for_problem_spec_builds_stage_outputs() -> None:
    snapshot = _snapshot()
    problem_spec = load_problem_spec(Path("tests/fixtures/specs/sample_spec.yaml"))

    result = build_canonical_stat_pipeline_for_problem_spec(
        snapshot=snapshot,
        problem_spec=problem_spec,
        wave=problem_spec.scenario.wave,
        include_perk_timeline=False,
    )

    assert "tower_hp" in result.base_stage.values
    assert "tower_hp" in result.start_stage.values
    assert result.at_wave_stage is not None
    assert result.at_wave_stage.wave_state.W_actual == problem_spec.scenario.wave


def test_build_canonical_stat_pipeline_wrapper_uses_scenario_contract() -> None:
    snapshot = _snapshot()
    problem_spec = load_problem_spec(Path("tests/fixtures/specs/sample_spec.yaml"))

    result = build_canonical_stat_pipeline(
        snapshot=snapshot,
        scenario=problem_spec.scenario,
        preset=None,
        wave=problem_spec.scenario.wave,
        include_perk_timeline=False,
    )

    assert result.start_stage.merge_policy in {
        "strict_fail_closed",
        "explicit_override_mode",
    }


def test_build_canonical_stat_pipeline_wrapper_applies_explicit_preset() -> None:
    snapshot = _snapshot()
    problem_spec = load_problem_spec(Path("tests/fixtures/specs/sample_spec.yaml"))

    result = build_canonical_stat_pipeline(
        snapshot=snapshot,
        scenario=problem_spec.scenario,
        preset="Farming",
        wave=problem_spec.scenario.wave,
        include_perk_timeline=False,
    )

    assert result.start_stage.merge_policy in {"strict_fail_closed", "explicit_override_mode"}


def test_stage_lineage_includes_workshop_levels_and_non_level_sources() -> None:
    snapshot = _snapshot()
    problem_spec = load_problem_spec(Path("tests/fixtures/specs/sample_spec.yaml"))

    result = build_canonical_stat_pipeline_for_problem_spec(
        snapshot=snapshot,
        problem_spec=problem_spec,
        wave=problem_spec.scenario.wave,
        include_perk_timeline=False,
    )

    workshop_rows = [
        row
        for row in result.start_stage.contributors
        if row.provenance.startswith("workshop_table:") or row.provenance.startswith("workshop_alias:")
    ]
    assert workshop_rows
    assert any(row.level is not None for row in workshop_rows)

    fixture_rows = [row for row in result.start_stage.contributors if row.provenance.startswith("fixture") ]
    assert fixture_rows
    assert all(row.level is None for row in fixture_rows)


def test_stage_golden_stat_presence_and_progression_contract() -> None:
    snapshot = _snapshot()
    problem_spec = load_problem_spec(Path("tests/fixtures/specs/sample_spec.yaml"))

    result = build_canonical_stat_pipeline_for_problem_spec(
        snapshot=snapshot,
        problem_spec=problem_spec,
        wave=problem_spec.scenario.wave,
        include_perk_timeline=False,
    )

    golden_ids = {
        "tower_hp",
        "tower_regen",
        "def_pct",
        "eals_pct",
        "ehls_pct",
        "tower_attack_speed",
        "tower_crit_chance",
        "tower_crit_multiplier",
        "wall_hp",
        "uw_smart_missiles_cooldown",
    }
    assert golden_ids.issubset(result.start_stage.values.keys())
    assert result.at_wave_stage is not None
    assert golden_ids.issubset(result.at_wave_stage.values.keys())

    # Stage 2 should incorporate loadout/start-of-run contributors beyond Stage 1 baseline.
    differing = [
        stat_id
        for stat_id, base_val in result.base_stage.values.items()
        if stat_id in result.start_stage.values and abs(result.start_stage.values[stat_id] - base_val) > 1e-9
    ]
    assert differing


def test_stage_required_stat_completeness_fail_closed(monkeypatch) -> None:
    snapshot = _snapshot()
    problem_spec = load_problem_spec(Path("tests/fixtures/specs/sample_spec.yaml"))

    class _RunStats:
        def __init__(self, values):
            self.values = values

    class _FakeResult:
        def __init__(self, values):
            self.run_stats = {Phase.START_OF_RUN: _RunStats(values)}

    original_build = StatEngine.build

    def _build_missing(self, inputs, wave_state=None):
        result = original_build(self, inputs, wave_state=wave_state)
        if wave_state is None:
            values = dict(result.run_stats[Phase.START_OF_RUN].values)
            values.pop("tower_hp", None)
            return _FakeResult(values)
        return result

    monkeypatch.setattr("tower_sim.engines.stat_pipeline.StatEngine.build", _build_missing)

    result = build_canonical_stat_pipeline_for_problem_spec(
        snapshot=snapshot,
        problem_spec=problem_spec,
        wave=problem_spec.scenario.wave,
        include_perk_timeline=False,
    )

    assert any(item.startswith("start_stage_missing:tower_hp") for item in result.missing)


def test_stage_golden_stat_values_for_pinned_snapshot() -> None:
    snapshot = _snapshot()
    problem_spec = load_problem_spec(Path("tests/fixtures/specs/sample_spec.yaml"))

    result = build_canonical_stat_pipeline_for_problem_spec(
        snapshot=snapshot,
        problem_spec=problem_spec,
        wave=problem_spec.scenario.wave,
        include_perk_timeline=False,
    )

    expected_start = {
        "tower_hp": 226100335680000.0,
        "tower_regen": 55998800000.0,
        "def_pct": 1.2412,
        "eals_pct": 0.18,
        "ehls_pct": 0.16,
        "tower_attack_speed": 0.0,
        "tower_crit_chance": 0.8,
        "tower_crit_multiplier": 5.169785043140672e16,
        "wall_hp": 1.2965581939439062e16,
        "uw_smart_missiles_cooldown": 0.0,
    }
    for stat_id, expected in expected_start.items():
        assert result.start_stage.values[stat_id] == pytest.approx(expected, rel=0.0, abs=1e-12)

    assert result.at_wave_stage is not None
    expected_at_wave = dict(expected_start)
    expected_at_wave["eals_pct"] = 0.155
    expected_at_wave["ehls_pct"] = 0.135
    for stat_id, expected in expected_at_wave.items():
        assert result.at_wave_stage.values[stat_id] == pytest.approx(expected, rel=0.0, abs=1e-12)


def test_stage_lineage_includes_uw_levels_from_snapshot_tracks() -> None:
    snapshot = _snapshot()
    problem_spec = load_problem_spec(Path("tests/fixtures/specs/sample_spec.yaml"))

    result = build_canonical_stat_pipeline_for_problem_spec(
        snapshot=snapshot,
        problem_spec=problem_spec,
        wave=problem_spec.scenario.wave,
        include_perk_timeline=False,
    )

    uw_rows = [row for row in result.start_stage.contributors if row.provenance.startswith("uw_section:")]
    assert uw_rows
    assert any(row.level is not None for row in uw_rows)


def test_stage_lineage_includes_card_levels_from_inventory() -> None:
    snapshot = _snapshot()
    problem_spec = load_problem_spec(Path("tests/fixtures/specs/sample_spec.yaml"))

    result = build_canonical_stat_pipeline_for_problem_spec(
        snapshot=snapshot,
        problem_spec=problem_spec,
        wave=problem_spec.scenario.wave,
        include_perk_timeline=False,
    )

    card_rows = [row for row in result.start_stage.contributors if row.provenance.startswith("cards:")]
    assert card_rows
    assert any(row.level is not None for row in card_rows)




def test_stage_lineage_includes_workshop_formula_levels() -> None:
    snapshot = _snapshot()
    problem_spec = load_problem_spec(Path("tests/fixtures/specs/sample_spec.yaml"))

    result = build_canonical_stat_pipeline_for_problem_spec(
        snapshot=snapshot,
        problem_spec=problem_spec,
        wave=problem_spec.scenario.wave,
        include_perk_timeline=False,
    )

    workshop_formula_rows = [
        row
        for row in result.base_stage.contributors
        if row.provenance.startswith("workshop_formula:")
    ]
    assert workshop_formula_rows
    assert all(row.level is not None for row in workshop_formula_rows)




def test_stage_lineage_has_no_null_levels_for_modeled_level_sources() -> None:
    snapshot = _snapshot()
    problem_spec = load_problem_spec(Path("tests/fixtures/specs/sample_spec.yaml"))

    result = build_canonical_stat_pipeline_for_problem_spec(
        snapshot=snapshot,
        problem_spec=problem_spec,
        wave=problem_spec.scenario.wave,
        include_perk_timeline=False,
    )

    modeled_prefixes = (
        "workshop_table:",
        "workshop_alias:",
        "workshop_formula:",
        "uw_section:",
        "cards:",
    )
    modeled_rows = [
        row
        for row in result.start_stage.contributors
        if any(row.provenance.startswith(prefix) for prefix in modeled_prefixes)
    ]

    assert modeled_rows
    null_rows = [row for row in modeled_rows if row.level is None]
    assert not null_rows


def test_at_wave_required_stat_completeness_fail_closed(monkeypatch) -> None:
    snapshot = _snapshot()
    problem_spec = load_problem_spec(Path("tests/fixtures/specs/sample_spec.yaml"))

    original = build_canonical_wave_snapshot

    def _build_missing(*args, **kwargs):
        wave_snapshot, missing = original(*args, **kwargs)
        if wave_snapshot is None or missing:
            return wave_snapshot, missing
        values = dict(wave_snapshot.values)
        values.pop("tower_hp", None)
        return (
            type(wave_snapshot)(
                wave=wave_snapshot.wave,
                values=values,
                applied_bc=wave_snapshot.applied_bc,
                applied_heat=wave_snapshot.applied_heat,
                frozen_order=wave_snapshot.frozen_order,
            ),
            missing,
        )

    monkeypatch.setattr("tower_sim.engines.stat_pipeline.build_canonical_wave_snapshot", _build_missing)

    result = build_canonical_stat_pipeline_for_problem_spec(
        snapshot=snapshot,
        problem_spec=problem_spec,
        wave=problem_spec.scenario.wave,
        include_perk_timeline=False,
    )

    assert any(item.startswith("at_wave_stage_missing:tower_hp") for item in result.missing)


def test_stage_materialization_uses_canonical_inputs_source() -> None:
    snapshot = _snapshot()
    problem_spec = load_problem_spec(Path("tests/fixtures/specs/tournament_champion_spec.yaml"))

    result = build_canonical_stat_pipeline_for_problem_spec(
        snapshot=snapshot,
        problem_spec=problem_spec,
        wave=problem_spec.scenario.wave,
        include_perk_timeline=False,
    )

    assert result.diagnostics["start_stage_source"] == "canonical_stat_inputs"
    assert "loadout_missing" not in result.diagnostics


@pytest.mark.parametrize(
    "spec_path",
    [
        Path("tests/fixtures/specs/tournament_champion_spec.yaml"),
        Path("tests/fixtures/specs/tournament_legend_spec.yaml"),
    ],
)
def test_stage_golden_stat_values_for_pinned_tournament_specs(spec_path: Path) -> None:
    snapshot = _snapshot()
    problem_spec = load_problem_spec(spec_path)

    result = build_canonical_stat_pipeline_for_problem_spec(
        snapshot=snapshot,
        problem_spec=problem_spec,
        wave=problem_spec.scenario.wave,
        include_perk_timeline=False,
    )

    expected_start = {
        "tower_hp": 226608.24167999995,
        "tower_regen": 2799.94,
        "def_pct": 0.4684,
        "eals_pct": 0.27,
        "ehls_pct": 0.22999999999999998,
        "tower_attack_speed": 0.0,
        "tower_crit_chance": 0.91,
        "tower_crit_multiplier": 5.169785043140672e16,
        "wall_hp": 6497353.745225208,
        "uw_smart_missiles_cooldown": 0.0,
    }
    for stat_id, expected in expected_start.items():
        assert result.start_stage.values[stat_id] == pytest.approx(expected, rel=0.0, abs=1e-12)

    assert result.at_wave_stage is not None
    expected_at_wave = dict(expected_start)
    expected_at_wave["eals_pct"] = 0.24500000000000002
    expected_at_wave["ehls_pct"] = 0.205
    for stat_id, expected in expected_at_wave.items():
        assert result.at_wave_stage.values[stat_id] == pytest.approx(expected, rel=0.0, abs=1e-12)


@pytest.mark.parametrize(
    "spec_path",
    [
        Path("tests/fixtures/specs/sample_spec.yaml"),
        Path("tests/fixtures/specs/tournament_champion_spec.yaml"),
        Path("tests/fixtures/specs/tournament_legend_spec.yaml"),
    ],
)
def test_stage_lineage_modeled_level_sources_no_nulls_across_specs(spec_path: Path) -> None:
    snapshot = _snapshot()
    problem_spec = load_problem_spec(spec_path)

    result = build_canonical_stat_pipeline_for_problem_spec(
        snapshot=snapshot,
        problem_spec=problem_spec,
        wave=problem_spec.scenario.wave,
        include_perk_timeline=False,
    )

    modeled_prefixes = (
        "workshop_table:",
        "workshop_alias:",
        "workshop_formula:",
        "uw_section:",
        "cards:",
    )
    modeled_rows = [
        row
        for row in result.start_stage.contributors
        if any(row.provenance.startswith(prefix) for prefix in modeled_prefixes)
    ]

    assert modeled_rows
    assert all(row.level is not None for row in modeled_rows)


@pytest.mark.parametrize(
    "spec_path",
    [
        Path("tests/fixtures/specs/sample_spec.yaml"),
        Path("tests/fixtures/specs/tournament_champion_spec.yaml"),
        Path("tests/fixtures/specs/tournament_legend_spec.yaml"),
    ],
)
def test_card_provenance_keys_are_mapped_for_pinned_specs(spec_path: Path) -> None:
    snapshot = _snapshot()
    problem_spec = load_problem_spec(spec_path)

    result = build_canonical_stat_pipeline_for_problem_spec(
        snapshot=snapshot,
        problem_spec=problem_spec,
        wave=problem_spec.scenario.wave,
        include_perk_timeline=False,
    )

    observed_card_keys = {
        row.provenance.split(":", 1)[1].strip()
        for row in result.start_stage.contributors
        if row.provenance.startswith("cards:")
    }
    assert observed_card_keys
    mapped_keys = set(stat_pipeline_module._CARD_PROVENANCE_TO_NAME.keys())
    assert observed_card_keys <= mapped_keys


@pytest.mark.parametrize(
    "spec_path",
    [
        Path("tests/fixtures/specs/sample_spec.yaml"),
        Path("tests/fixtures/specs/tournament_champion_spec.yaml"),
        Path("tests/fixtures/specs/tournament_legend_spec.yaml"),
    ],
)
def test_workshop_formula_stat_ids_are_mapped_for_pinned_specs(spec_path: Path) -> None:
    snapshot = _snapshot()
    problem_spec = load_problem_spec(spec_path)

    result = build_canonical_stat_pipeline_for_problem_spec(
        snapshot=snapshot,
        problem_spec=problem_spec,
        wave=problem_spec.scenario.wave,
        include_perk_timeline=False,
    )

    observed_formula_ids = {
        row.stat_id
        for row in result.base_stage.contributors
        if row.provenance.startswith("workshop_formula:")
    }
    assert observed_formula_ids
    mapped_formula_ids = set(stat_pipeline_module._WORKSHOP_FORMULA_STAT_TO_WORKSHOP_NAME.keys())
    assert observed_formula_ids <= mapped_formula_ids


@pytest.mark.parametrize(
    "spec_path",
    [
        Path("tests/fixtures/specs/sample_spec.yaml"),
        Path("tests/fixtures/specs/tournament_champion_spec.yaml"),
        Path("tests/fixtures/specs/tournament_legend_spec.yaml"),
    ],
)
def test_workshop_formula_lineage_values_match_compiled_inputs(spec_path: Path) -> None:
    snapshot = _snapshot()
    problem_spec = load_problem_spec(spec_path)

    result = build_canonical_stat_pipeline_for_problem_spec(
        snapshot=snapshot,
        problem_spec=problem_spec,
        wave=problem_spec.scenario.wave,
        include_perk_timeline=False,
    )

    formula_rows = [
        row
        for row in result.base_stage.contributors
        if row.provenance.startswith("workshop_formula:")
    ]
    assert formula_rows

    compiled = stat_input_compiler_module.compile_full_stat_inputs(snapshot)
    compiled_formula_values: dict[str, set[float]] = {}
    for item in compiled.stat_inputs:
        if not (item.provenance or "").startswith("workshop_formula:"):
            continue
        value = stat_pipeline_module._resolved_stat_input_value(item)
        compiled_formula_values.setdefault(item.stat_id, set()).add(float(value))

    for row in formula_rows:
        expected_values = compiled_formula_values.get(row.stat_id)
        assert expected_values is not None
        assert row.resolved_value in expected_values


@pytest.mark.parametrize(
    ("spec_path", "expected_at_wave_delta_ids"),
    [
        (
            Path("tests/fixtures/specs/sample_spec.yaml"),
            {
                "death_ray_damage_mult",
                "eals_pct",
                "ehls_pct",
                "orb_damage_mult",
                "plasma_cannon_damage_mult",
                "thorns_damage_mult",
            },
        ),
        (
            Path("tests/fixtures/specs/tournament_champion_spec.yaml"),
            {
                "death_ray_damage_mult",
                "eals_pct",
                "ehls_pct",
                "knockback_mult",
                "orb_damage_mult",
                "plasma_cannon_damage_mult",
                "thorns_damage_mult",
            },
        ),
        (
            Path("tests/fixtures/specs/tournament_legend_spec.yaml"),
            {
                "death_ray_damage_mult",
                "eals_pct",
                "ehls_pct",
                "knockback_mult",
                "orb_damage_mult",
                "plasma_cannon_damage_mult",
                "thorns_damage_mult",
            },
        ),
    ],
)
def test_stage3_wave_deltas_are_pinned_for_key_specs(
    spec_path: Path,
    expected_at_wave_delta_ids: set[str],
) -> None:
    snapshot = _snapshot()
    problem_spec = load_problem_spec(spec_path)

    result = build_canonical_stat_pipeline_for_problem_spec(
        snapshot=snapshot,
        problem_spec=problem_spec,
        wave=problem_spec.scenario.wave,
        include_perk_timeline=False,
    )

    assert result.at_wave_stage is not None
    differing_ids = {
        stat_id
        for stat_id, start_value in result.start_stage.values.items()
        if stat_id in result.at_wave_stage.values
        and abs(result.at_wave_stage.values[stat_id] - start_value) > 1e-12
    }
    assert differing_ids == expected_at_wave_delta_ids


@pytest.mark.parametrize(
    ("spec_path", "expected_stage2_delta_ids"),
    [
        (
            Path("tests/fixtures/specs/sample_spec.yaml"),
            {
                "def_pct",
                "eals_pct",
                "ehls_pct",
                "plasma_cannon_damage_mult",
                "thorns_damage_mult",
                "tower_hp",
                "tower_regen",
                "wall_hp",
                "wall_regen",
                "workshop_cash_bonus",
                "workshop_coins_per_kill_bonus",
            },
        ),
        (
            Path("tests/fixtures/specs/tournament_champion_spec.yaml"),
            {
                "def_pct",
                "eals_pct",
                "ehls_pct",
                "plasma_cannon_damage_mult",
                "thorns_damage_mult",
                "tower_hp",
                "tower_regen",
                "wall_hp",
                "wall_regen",
                "tower_crit_chance",
                "workshop_package_chance",
            },
        ),
        (
            Path("tests/fixtures/specs/tournament_legend_spec.yaml"),
            {
                "def_pct",
                "eals_pct",
                "ehls_pct",
                "plasma_cannon_damage_mult",
                "thorns_damage_mult",
                "tower_hp",
                "tower_regen",
                "wall_hp",
                "wall_regen",
                "tower_crit_chance",
                "workshop_package_chance",
            },
        ),
    ],
)
def test_stage2_deltas_are_pinned_for_key_specs(
    spec_path: Path,
    expected_stage2_delta_ids: set[str],
) -> None:
    snapshot = _snapshot()
    problem_spec = load_problem_spec(spec_path)

    result = build_canonical_stat_pipeline_for_problem_spec(
        snapshot=snapshot,
        problem_spec=problem_spec,
        wave=problem_spec.scenario.wave,
        include_perk_timeline=False,
    )

    differing_ids = {
        stat_id
        for stat_id, base_value in result.base_stage.values.items()
        if stat_id in result.start_stage.values
        and abs(result.start_stage.values[stat_id] - base_value) > 1e-12
    }
    assert differing_ids == expected_stage2_delta_ids
