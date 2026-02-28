from __future__ import annotations

from dataclasses import dataclass
import csv
from pathlib import Path

import pytest

from tower_sim.engines.combat_stat_derivation import (
    build_canonical_stat_inputs,
    build_canonical_wave_row,
    build_canonical_wave_snapshot,
    TOURNAMENT_HEAT_BC_IDS,
    derive_canonical_combat_snapshot,
    resolve_canonical_wave_damage_for_attack_wave,
    validate_boss_survivability_spec,
    wave_state_from_row,
)
from tower_sim.registry.stat_registry import Phase, default_registry
from tower_sim.loaders.bc_heat_loader import HeatDataError, make_bc_id


@dataclass(frozen=True)
class _RunStats:
    values: dict[str, float]


@dataclass(frozen=True)
class _EngineResult:
    run_stats: dict


@dataclass(frozen=True)
class _WaveSnapshot:
    values: dict[str, float]


def _engine_result(start_values: dict[str, float]) -> _EngineResult:
    return _EngineResult(run_stats={Phase.START_OF_RUN: _RunStats(values=start_values)})


def test_derive_canonical_combat_snapshot_prefers_wave_values() -> None:
    engine_result = _engine_result(
        {
            "tower_hp": 100.0,
            "tower_regen": 2.0,
            "def_pct": 0.1,
            "wall_hp": 50.0,
            "wall_regen": 1.0,
            "thorns_damage_mult": 0.2,
        }
    )
    wave_snapshot = _WaveSnapshot(values={"tower_hp": 120.0, "def_pct": 0.2})

    snapshot, missing = derive_canonical_combat_snapshot(engine_result, wave_snapshot)

    assert not missing
    assert snapshot is not None
    assert snapshot.values["tower_hp"] == 120.0
    assert snapshot.values["def_pct"] == 0.2
    assert snapshot.values["wall_hp"] == 50.0
    assert snapshot.contributions["tower_hp"][0].source == "at_wave_snapshot"
    assert snapshot.contributions["wall_hp"][0].source == "start_of_run"


def test_derive_canonical_combat_snapshot_caps_defense_percent_at_98() -> None:
    engine_result = _engine_result(
        {
            "tower_hp": 100.0,
            "tower_regen": 2.0,
            "def_pct": 1.4,
            "wall_hp": 50.0,
            "wall_regen": 1.0,
            "thorns_damage_mult": 0.2,
        }
    )

    snapshot, missing = derive_canonical_combat_snapshot(engine_result, wave_snapshot=None)

    assert not missing
    assert snapshot is not None
    assert snapshot.values["def_pct"] == 0.98


def test_derive_canonical_combat_snapshot_fail_closed_when_required_stat_missing() -> None:
    engine_result = _engine_result(
        {
            "tower_hp": 100.0,
            "tower_regen": 2.0,
            "def_pct": 0.1,
            "wall_hp": 50.0,
            "wall_regen": 1.0,
        }
    )

    snapshot, missing = derive_canonical_combat_snapshot(engine_result, wave_snapshot=None)

    assert snapshot is None
    assert missing == ["stat:thorns_damage_mult"]

from tower_sim.engines.stat_engine import StatInput
from tower_sim.run.problem_spec import ProblemSpec, ScenarioSpec, SkipRampSpec, StatInputSpec


def _problem_spec(*, allow_core_stat_overrides: bool = False) -> ProblemSpec:
    return ProblemSpec(
        scenario=ScenarioSpec(mode="farming", tier=12, allow_core_stat_overrides=allow_core_stat_overrides),
        stat_inputs=[
            StatInputSpec(
                stat_id="tower_hp",
                phase=Phase.START_OF_RUN,
                base_value=100.0,
                provenance="test",
            )
        ],
    )


def test_build_canonical_stat_inputs_blocks_core_override_in_strict_mode(monkeypatch) -> None:
    def _fake_compile(_ids_snapshot):
        return type(
            "_Compiled",
            (),
            {
                "stat_inputs": [
                    StatInput(
                        stat_id="tower_hp",
                        phase=Phase.START_OF_RUN,
                        base_value=120.0,
                        provenance="compiled",
                    )
                ],
                "missing": [],
            },
        )()

    monkeypatch.setattr(
        "tower_sim.engines.combat_stat_derivation._compile_full",
        _fake_compile,
    )
    monkeypatch.setattr(
        "tower_sim.engines.combat_stat_derivation._compile_survivability_loadout",
        lambda *_args, **_kwargs: [],
    )

    built = build_canonical_stat_inputs(
        problem_spec=_problem_spec(allow_core_stat_overrides=False),
        ids_snapshot=object(),
        registry=default_registry(),
    )

    assert built.core_stat_override_policy == "strict_fail_closed"
    assert built.blocked_core_overrides == ["tower_hp@start_of_run"]


def test_build_canonical_stat_inputs_allows_core_override_in_explicit_mode(monkeypatch) -> None:
    def _fake_compile(_ids_snapshot):
        return type(
            "_Compiled",
            (),
            {
                "stat_inputs": [
                    StatInput(
                        stat_id="tower_hp",
                        phase=Phase.START_OF_RUN,
                        base_value=120.0,
                        provenance="compiled",
                    )
                ],
                "missing": [],
            },
        )()

    monkeypatch.setattr(
        "tower_sim.engines.combat_stat_derivation._compile_full",
        _fake_compile,
    )
    monkeypatch.setattr(
        "tower_sim.engines.combat_stat_derivation._compile_survivability_loadout",
        lambda *_args, **_kwargs: [],
    )

    built = build_canonical_stat_inputs(
        problem_spec=_problem_spec(allow_core_stat_overrides=True),
        ids_snapshot=object(),
        registry=default_registry(),
    )

    assert built.core_stat_override_policy == "explicit_override_mode"
    assert built.blocked_core_overrides == []


def test_build_canonical_stat_inputs_ignores_workshop_alias_collisions(monkeypatch) -> None:
    def _fake_compile(_ids_snapshot):
        return type(
            "_Compiled",
            (),
            {
                "stat_inputs": [
                    StatInput(
                        stat_id="tower_hp",
                        phase=Phase.START_OF_RUN,
                        base_value=120.0,
                        provenance="workshop_alias:Health->tower_hp",
                    )
                ],
                "missing": [],
            },
        )()

    monkeypatch.setattr(
        "tower_sim.engines.combat_stat_derivation._compile_full",
        _fake_compile,
    )
    monkeypatch.setattr(
        "tower_sim.engines.combat_stat_derivation._compile_survivability_loadout",
        lambda *_args, **_kwargs: [],
    )

    built = build_canonical_stat_inputs(
        problem_spec=_problem_spec(allow_core_stat_overrides=False),
        ids_snapshot=object(),
        registry=default_registry(),
    )

    assert built.blocked_core_overrides == []


def test_build_canonical_stat_inputs_uses_mode_specific_module_context(monkeypatch) -> None:
    observed: list[str] = []

    def _fake_compile(_ids_snapshot):
        return type("_Compiled", (), {"stat_inputs": [], "missing": []})()

    def _fake_loadout(_ids_snapshot, *, module_context, allow_provisional):
        observed.append(module_context)
        return []

    monkeypatch.setattr(
        "tower_sim.engines.combat_stat_derivation._compile_full",
        _fake_compile,
    )
    monkeypatch.setattr(
        "tower_sim.engines.combat_stat_derivation._compile_survivability_loadout",
        _fake_loadout,
    )

    build_canonical_stat_inputs(
        problem_spec=ProblemSpec(
            scenario=ScenarioSpec(mode="farming", tier=12),
            stat_inputs=[],
        ),
        ids_snapshot=object(),
        registry=default_registry(),
    )
    build_canonical_stat_inputs(
        problem_spec=ProblemSpec(
            scenario=ScenarioSpec(mode="tournament", tier=12),
            stat_inputs=[],
        ),
        ids_snapshot=object(),
        registry=default_registry(),
    )

    assert observed == ["Farming", "Tourney"]


def test_build_canonical_stat_inputs_skips_unsupported_cards_but_keeps_loadout(monkeypatch) -> None:
    def _fake_compile(_ids_snapshot):
        return type(
            "_Compiled",
            (),
            {
                "stat_inputs": [
                    StatInput(
                        stat_id="tower_hp",
                        phase=Phase.START_OF_RUN,
                        base_value=100.0,
                        provenance="compiled",
                    ),
                    StatInput(
                        stat_id="tower_regen",
                        phase=Phase.START_OF_RUN,
                        base_value=10.0,
                        provenance="compiled",
                    ),
                    StatInput(
                        stat_id="def_pct",
                        phase=Phase.START_OF_RUN,
                        base_value=0.2,
                        provenance="compiled",
                    ),
                    StatInput(
                        stat_id="wall_hp",
                        phase=Phase.START_OF_RUN,
                        base_value=20.0,
                        provenance="compiled",
                    ),
                    StatInput(
                        stat_id="wall_regen",
                        phase=Phase.START_OF_RUN,
                        base_value=1.0,
                        provenance="compiled",
                    ),
                    StatInput(
                        stat_id="thorns_damage_mult",
                        phase=Phase.START_OF_RUN,
                        base_value=0.1,
                        provenance="compiled",
                    ),
                    StatInput(
                        stat_id="eals_pct",
                        phase=Phase.START_OF_RUN,
                        base_value=0.0,
                        provenance="compiled",
                    ),
                    StatInput(
                        stat_id="ehls_pct",
                        phase=Phase.START_OF_RUN,
                        base_value=0.0,
                        provenance="compiled",
                    ),
                ],
                "missing": [],
            },
        )()

    calls = {"count": 0}

    def _fake_loadout(_ids_snapshot, *, module_context, selected_cards, allow_provisional):
        calls["count"] += 1
        if calls["count"] == 1:
            raise ValueError("Unsupported card for survivability pipeline: 'Enemy Balance'.")
        return [
            StatInput(
                stat_id="tower_hp",
                phase=Phase.START_OF_RUN,
                loadout_delta=50.0,
                provenance="loadout",
            )
        ]

    monkeypatch.setattr(
        "tower_sim.engines.combat_stat_derivation._compile_full",
        _fake_compile,
    )
    monkeypatch.setattr(
        "tower_sim.engines.combat_stat_derivation._compile_survivability_loadout",
        _fake_loadout,
    )

    class _Snapshot:
        card_presets = {"Farming": ["Enemy Balance", "Health"]}

    built = build_canonical_stat_inputs(
        problem_spec=ProblemSpec(
            scenario=ScenarioSpec(mode="farming", tier=12),
            stat_inputs=[],
        ),
        ids_snapshot=_Snapshot(),
        registry=default_registry(),
    )

    assert "survivability_loadout_unsupported_card:Enemy Balance" in built.compiled_missing
    tower_hp = next(
        item
        for item in built.stat_inputs
        if item.stat_id == "tower_hp" and item.phase == Phase.START_OF_RUN
    )
    assert tower_hp.loadout_delta == 50.0




def test_build_canonical_stat_inputs_rebases_wall_stats_from_resolved_tower_values(monkeypatch) -> None:
    def _fake_compile(_ids_snapshot):
        return type(
            "_Compiled",
            (),
            {
                "stat_inputs": [
                    StatInput(
                        stat_id="tower_hp",
                        phase=Phase.START_OF_RUN,
                        base_value=100.0,
                        enhancement_multiplier=2.0,
                        provenance="compiled",
                    ),
                    StatInput(
                        stat_id="tower_regen",
                        phase=Phase.START_OF_RUN,
                        base_value=10.0,
                        enhancement_multiplier=3.0,
                        provenance="compiled",
                    ),
                    StatInput(
                        stat_id="def_pct",
                        phase=Phase.START_OF_RUN,
                        base_value=0.2,
                        provenance="compiled",
                    ),
                    StatInput(
                        stat_id="wall_hp",
                        phase=Phase.START_OF_RUN,
                        base_value=80.0,
                        enhancement_multiplier=4.0,
                        provenance="compiled",
                    ),
                    StatInput(
                        stat_id="wall_regen",
                        phase=Phase.START_OF_RUN,
                        base_value=5.0,
                        enhancement_multiplier=5.0,
                        provenance="compiled",
                    ),
                    StatInput(
                        stat_id="thorns_damage_mult",
                        phase=Phase.START_OF_RUN,
                        base_value=0.1,
                        provenance="compiled",
                    ),
                    StatInput(
                        stat_id="eals_pct",
                        phase=Phase.START_OF_RUN,
                        base_value=0.0,
                        provenance="compiled",
                    ),
                    StatInput(
                        stat_id="ehls_pct",
                        phase=Phase.START_OF_RUN,
                        base_value=0.0,
                        provenance="compiled",
                    ),
                ],
                "missing": [],
            },
        )()

    monkeypatch.setattr(
        "tower_sim.engines.combat_stat_derivation._compile_full",
        _fake_compile,
    )
    monkeypatch.setattr(
        "tower_sim.engines.combat_stat_derivation._compile_survivability_loadout",
        lambda *_args, **_kwargs: [],
    )
    monkeypatch.setattr(
        "tower_sim.engines.combat_stat_derivation._wall_ratio_from_ids",
        lambda _ids_snapshot, _stat_inputs: (2.5, 0.5, []),
    )

    built = build_canonical_stat_inputs(
        problem_spec=ProblemSpec(
            scenario=ScenarioSpec(mode="farming", tier=12),
            stat_inputs=[],
        ),
        ids_snapshot=object(),
        registry=default_registry(),
    )

    by_id = {
        item.stat_id: item
        for item in built.stat_inputs
        if item.phase == Phase.START_OF_RUN
    }
    wall_hp = by_id["wall_hp"]
    wall_regen = by_id["wall_regen"]

    assert wall_hp.base_value == pytest.approx(500.0)
    assert wall_hp.enhancement_multiplier == pytest.approx(4.0)
    assert wall_regen.base_value == pytest.approx(15.0)
    assert wall_regen.enhancement_multiplier == pytest.approx(5.0)

def test_build_canonical_stat_inputs_blocks_non_core_base_override_in_strict_mode(monkeypatch) -> None:
    def _fake_compile(_ids_snapshot):
        return type(
            "_Compiled",
            (),
            {
                "stat_inputs": [
                    StatInput(
                        stat_id="workshop_damage",
                        phase=Phase.START_OF_RUN,
                        base_value=333.0,
                        provenance="compiled",
                    )
                ],
                "missing": [],
            },
        )()

    monkeypatch.setattr(
        "tower_sim.engines.combat_stat_derivation._compile_full",
        _fake_compile,
    )
    monkeypatch.setattr(
        "tower_sim.engines.combat_stat_derivation._compile_survivability_loadout",
        lambda *_args, **_kwargs: [],
    )

    built = build_canonical_stat_inputs(
        problem_spec=ProblemSpec(
            scenario=ScenarioSpec(mode="farming", tier=12, allow_core_stat_overrides=False),
            stat_inputs=[
                StatInputSpec(
                    stat_id="workshop_damage",
                    phase=Phase.START_OF_RUN,
                    base_value=111.0,
                    provenance="test",
                )
            ],
        ),
        ids_snapshot=object(),
        registry=default_registry(),
    )

    workshop_damage = next(
        item
        for item in built.stat_inputs
        if item.stat_id == "workshop_damage" and item.phase == Phase.START_OF_RUN
    )
    assert workshop_damage.base_value == 111.0
    assert built.blocked_core_overrides == ["workshop_damage@start_of_run"]


def test_build_canonical_stat_inputs_allows_core_loadout_delta_in_strict_mode(monkeypatch) -> None:
    def _fake_compile(_ids_snapshot):
        return type("_Compiled", (), {"stat_inputs": [], "missing": []})()

    monkeypatch.setattr(
        "tower_sim.engines.combat_stat_derivation._compile_full",
        _fake_compile,
    )
    monkeypatch.setattr(
        "tower_sim.engines.combat_stat_derivation._compile_survivability_loadout",
        lambda *_args, **_kwargs: [
            StatInput(
                stat_id="def_pct",
                phase=Phase.START_OF_RUN,
                loadout_delta=0.12,
                provenance="loadout",
            )
        ],
    )

    problem = ProblemSpec(
        scenario=ScenarioSpec(mode="farming", tier=12, allow_core_stat_overrides=False),
        stat_inputs=[
            StatInputSpec(
                stat_id="def_pct",
                phase=Phase.START_OF_RUN,
                base_value=0.5,
                provenance="test",
            )
        ],
    )

    built = build_canonical_stat_inputs(
        problem_spec=problem,
        ids_snapshot=object(),
        registry=default_registry(),
    )

    def_pct = next(
        item
        for item in built.stat_inputs
        if item.stat_id == "def_pct" and item.phase == Phase.START_OF_RUN
    )
    assert def_pct.base_value == 0.5
    assert def_pct.loadout_delta == 0.12
    assert built.blocked_core_overrides == []


def test_build_canonical_stat_inputs_requires_base_or_derived_for_required_stat(monkeypatch) -> None:
    def _fake_compile(_ids_snapshot):
        return type("_Compiled", (), {"stat_inputs": [], "missing": []})()

    monkeypatch.setattr(
        "tower_sim.engines.combat_stat_derivation._compile_full",
        _fake_compile,
    )
    monkeypatch.setattr(
        "tower_sim.engines.combat_stat_derivation._compile_survivability_loadout",
        lambda *_args, **_kwargs: [
            StatInput(
                stat_id="tower_hp",
                phase=Phase.START_OF_RUN,
                loadout_delta=250.0,
                provenance="loadout",
            )
        ],
    )

    built = build_canonical_stat_inputs(
        problem_spec=ProblemSpec(
            scenario=ScenarioSpec(mode="farming", tier=12, allow_core_stat_overrides=False),
            stat_inputs=[],
        ),
        ids_snapshot=object(),
        registry=default_registry(),
    )

    assert "stat_input:tower_hp" in built.missing_required_stat_inputs

from tower_sim.run.problem_spec import BossStatsSpec, BossSurvivabilitySpec, TowerDefenseSpec


def test_resolve_canonical_wave_damage_for_attack_wave() -> None:
    problem = ProblemSpec(
        scenario=ScenarioSpec(mode="farming", tier=1, wave=10),
        stat_inputs=[],
    )
    damage, missing = resolve_canonical_wave_damage_for_attack_wave(
        problem_spec=problem,
        attack_wave=10,
    )
    assert missing == []
    assert isinstance(damage, float)
    assert damage > 0


def test_validate_boss_survivability_spec_reports_invalid_fields() -> None:
    problem = ProblemSpec(
        scenario=ScenarioSpec(
            mode="farming",
            tier=1,
            boss_survivability=BossSurvivabilitySpec(
                boss=BossStatsSpec(hp=1.0, attack=-1.0, attack_interval=0.0, enrage_mult=0.0),
                tower=TowerDefenseSpec(dr_frac=1.5, regen_per_sec=-1.0, shields=-1.0),
                combat_params={},
                bc_params={},
            ),
        ),
        stat_inputs=[],
    )
    missing, diagnostics = validate_boss_survivability_spec(problem)
    assert missing == ["boss_survivability_invalid"]
    assert diagnostics["boss_attack"] == "non_positive"
    assert diagnostics["boss_attack_interval"] == "non_positive"
    assert diagnostics["tower_dr_frac"] == "out_of_range"

from tower_sim.engines.stat_snapshots import StatSnapshotError


def test_wave_state_from_row_fail_closed_when_keys_missing() -> None:
    try:
        wave_state_from_row({"wave": 10})
    except StatSnapshotError as exc:
        assert "Wave row missing required keys" in str(exc)
    else:
        raise AssertionError("Expected StatSnapshotError")

from tower_sim.engines.stat_engine import StatEngine
from tower_sim.loaders.account_snapshot_compiler import compile_account_snapshot
from tower_sim.loaders.ids_parser import parse_ids
from tower_sim.run.context import RunContext


def test_tournament_heat_missing_is_fail_closed(monkeypatch) -> None:
    class _FakeHeatTable:
        def value_at(self, *, league: str, wave_actual: int, bc_id: str):
            if bc_id == "thorns_resistance:":
                raise HeatDataError("missing")

            class _Row:
                value_num = 1.0

            return _Row()

    monkeypatch.setattr(
        "tower_sim.engines.combat_stat_derivation.cached_tournament_heat_table",
        lambda scale_path, registry_path: _FakeHeatTable(),
    )

    problem = ProblemSpec(
        scenario=ScenarioSpec(
            mode="tournament",
            tier=12,
            league="champion",
            wave=10,
            eals_ramp=SkipRampSpec(start=0.0, end=0.0, ramp_waves=1000),
            ehls_ramp=SkipRampSpec(start=0.0, end=0.0, ramp_waves=1000),
        ),
        stat_inputs=[],
    )
    row, missing = build_canonical_wave_row(problem, default_registry(), wave=10)
    assert row is None
    assert missing == ["heat_bc_value:thorns_resistance:"]


def test_heat_magnitude_mechanically_changes_wave_snapshot(monkeypatch) -> None:
    ids_snapshot = compile_account_snapshot(parse_ids(Path("tests/fixtures/tower-sim-data/_IDS.csv")))
    registry = default_registry()
    stat_inputs = [
        StatInput(stat_id="tower_hp", phase=Phase.START_OF_RUN, base_value=100.0, provenance="test"),
        StatInput(stat_id="tower_regen", phase=Phase.START_OF_RUN, base_value=1.0, provenance="test"),
        StatInput(stat_id="def_pct", phase=Phase.START_OF_RUN, base_value=0.0, provenance="test"),
        StatInput(stat_id="wall_hp", phase=Phase.START_OF_RUN, base_value=0.0, provenance="test"),
        StatInput(stat_id="wall_regen", phase=Phase.START_OF_RUN, base_value=0.0, provenance="test"),
        StatInput(stat_id="thorns_damage_mult", phase=Phase.START_OF_RUN, base_value=0.25, provenance="test"),
        StatInput(stat_id="orb_damage_mult", phase=Phase.START_OF_RUN, base_value=1.0, provenance="test"),
        StatInput(stat_id="death_ray_damage_mult", phase=Phase.START_OF_RUN, base_value=1.0, provenance="test"),
        StatInput(stat_id="plasma_cannon_damage_mult", phase=Phase.START_OF_RUN, base_value=1.0, provenance="test"),
        StatInput(stat_id="knockback_mult", phase=Phase.START_OF_RUN, base_value=1.0, provenance="test"),
        StatInput(stat_id="eals_pct", phase=Phase.START_OF_RUN, base_value=0.0, provenance="test"),
        StatInput(stat_id="ehls_pct", phase=Phase.START_OF_RUN, base_value=0.0, provenance="test"),
    ]
    engine_result = StatEngine(registry=registry).build(stat_inputs)

    monkeypatch.setattr(
        "tower_sim.engines.combat_stat_derivation.compile_workshop_values_at_wave",
        lambda _ids_snapshot, wave: ({}, []),
    )

    wave_row = {"wave": 10, "enemy_attack_wave": 10, "enemy_health_wave": 10}
    snapshot_no_heat, missing_no_heat = build_canonical_wave_snapshot(
        ids_snapshot=ids_snapshot,
        wave=10,
        stat_inputs=stat_inputs,
        engine_result=engine_result,
        registry=registry,
        tier_rules=None,
        run_context=RunContext.from_mode("farming", tier="12"),
        heat_magnitudes=None,
        wave_row=wave_row,
    )
    snapshot_with_heat, missing_with_heat = build_canonical_wave_snapshot(
        ids_snapshot=ids_snapshot,
        wave=10,
        stat_inputs=stat_inputs,
        engine_result=engine_result,
        registry=registry,
        tier_rules=None,
        run_context=RunContext.from_mode("tournament", tier="12"),
        heat_magnitudes={"thorns_damage_mult": 1.30},
        wave_row=wave_row,
    )

    assert missing_no_heat == []
    assert missing_with_heat == []
    assert snapshot_no_heat is not None
    assert snapshot_with_heat is not None
    assert snapshot_no_heat.values["thorns_damage_mult"] == 0.25
    assert snapshot_with_heat.values["thorns_damage_mult"] == 1.30
    assert snapshot_with_heat.applied_heat["thorns_damage_mult"] == 1.30


def test_tournament_heat_bc_ids_match_registry_csv_order() -> None:
    registry_path = Path("tables/inputs/tournament/heat_bc_registry.csv")
    with registry_path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        derived = []
        seen = set()
        for row in reader:
            bc_id = make_bc_id(row["bc_key"].strip(), row.get("bc_variant", "").strip())
            if bc_id in TOURNAMENT_HEAT_BC_IDS and bc_id not in seen:
                derived.append(bc_id)
                seen.add(bc_id)
    assert tuple(derived) == TOURNAMENT_HEAT_BC_IDS


from tower_sim.loaders.account_snapshot_compiler import compile_account_snapshot
from tower_sim.loaders.ids_parser import parse_ids
from tower_sim.run.spec_loader import load_problem_spec
from tower_sim.engines.survivability_pipeline import compile_survivability_loadout_stat_inputs_with_diagnostics


def test_canonical_module_contribution_ledger_captures_primary_unique_and_substats() -> None:
    ids_snapshot = compile_account_snapshot(parse_ids(Path("tests/fixtures/tower-sim-data/_IDS.csv")))
    problem = load_problem_spec(Path("tests/fixtures/specs/sample_spec.json"))

    loadout = compile_survivability_loadout_stat_inputs_with_diagnostics(
        ids_snapshot,
        module_context="Testing",
        selected_cards=["Plasma Cannon"],
        allow_provisional=True,
    )

    assert loadout.module_contribution_ledger
    assert not loadout.layer_gaps

    by_target: dict[str, list[dict[str, object]]] = {}
    for row in loadout.module_contribution_ledger:
        by_target.setdefault(str(row["target"]), []).append(row)

    assert "tower_hp" in by_target
    assert "wall_regen" in by_target
    assert "def_pct" in by_target
    assert any(row["layer"] == "primary" for row in by_target["tower_hp"])
    assert any(row["layer"] == "unique" for row in by_target["wall_regen"])
    assert any(row["layer"] == "substat" for row in by_target["def_pct"])

    stat_by_id = {item.stat_id: item for item in loadout.stat_inputs}

    tower_hp_product = 1.0
    for row in by_target.get("tower_hp", []):
        if row["kind"] == "multiplier":
            tower_hp_product *= float(row["value"])
    assert stat_by_id["tower_hp"].enhancement_multiplier == pytest.approx(tower_hp_product, rel=1e-9)

    wall_regen_product = 1.0
    for row in by_target.get("wall_regen", []):
        if row["kind"] == "multiplier":
            wall_regen_product *= float(row["value"])
    assert stat_by_id["wall_regen"].enhancement_multiplier == pytest.approx(wall_regen_product, rel=1e-9)

    def_pct_delta = 0.0
    for row in by_target.get("def_pct", []):
        if row["kind"] == "delta":
            def_pct_delta += float(row["value"])
    assert stat_by_id["def_pct"].loadout_delta == pytest.approx(def_pct_delta, rel=1e-9)

    built = build_canonical_stat_inputs(
        problem_spec=problem,
        ids_snapshot=ids_snapshot,
        registry=default_registry(),
    )
    assert built.module_contribution_ledger
    assert set(built.module_unmapped_by_layer.keys()) == {"main", "unique", "substats"}
    assert built.module_unmapped_by_layer["main"] == []
    assert built.module_unmapped_by_layer["unique"] == []
    assert built.module_unmapped_by_layer["substats"] == []
    assert set(built.canonical_unmapped_by_source.keys()) == {
        "modules",
        "cards",
        "labs",
        "enhancements",
        "workshop",
        "ultimate_weapons",
        "relics",
        "other",
    }
    assert built.canonical_unmapped_by_source["modules"] == []

    primary_rows = [
        row
        for row in built.module_contribution_ledger
        if row.get("layer") == "primary"
    ]
    assert primary_rows
    assert not any(
        str(row.get("target", "")).startswith("module_primary_effect:")
        for row in primary_rows
    )
    assert any(row.get("target") == "tower_damage" for row in primary_rows)
    assert any(row.get("target") == "workshop_coins_per_kill_bonus" for row in primary_rows)
    assert any(row.get("target") == "death_wave_damage" for row in primary_rows)
    assert not any(str(row.get("target", "")).startswith("uw_") for row in primary_rows)


def test_wall_ratio_from_ids_uses_compiled_workshop_ratios_only(monkeypatch: pytest.MonkeyPatch) -> None:
    from tower_sim.engines import combat_stat_derivation as derivation

    ids_snapshot = type("_Ids", (), {"labs": {"Wall Health": 1, "Wall Regen": 1}})()
    stat_inputs = [
        StatInput(stat_id="workshop_wall_health", phase=Phase.START_OF_RUN, base_value=0.2, enhancement_multiplier=2.0, provenance="test"),
        StatInput(stat_id="workshop_wall_regen", phase=Phase.START_OF_RUN, base_value=0.1, enhancement_multiplier=3.0, provenance="test"),
    ]

    wall_hp_ratio, wall_regen_ratio, missing = derivation._wall_ratio_from_ids(ids_snapshot, stat_inputs)

    assert wall_hp_ratio == pytest.approx(0.4)
    assert wall_regen_ratio == pytest.approx(0.3)
    assert missing == []
