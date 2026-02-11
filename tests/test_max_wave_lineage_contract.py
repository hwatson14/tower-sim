from __future__ import annotations

from pathlib import Path

from tower_sim.engines.combat_stat_derivation import build_canonical_stat_inputs
from tower_sim.engines.stat_input_compiler import _UW_TRACK_SPECS, _WORKSHOP_STAT_SPECS
from tower_sim.loaders.account_snapshot_compiler import compile_account_snapshot
from tower_sim.loaders.ids_parser import SECTION_SPECS, parse_ids
from tower_sim.registry.combat_stat_contract import (
    contributor_ids_sections,
    ordered_stat_lineage_sections,
    required_max_wave_stat_input_ids,
    required_combat_stat_ids,
    stat_lineage_manifest,
)
from tower_sim.registry.stat_registry import Phase, default_registry
from tower_sim.run.problem_spec import (
    BossStatsSpec,
    BossSurvivabilitySpec,
    ProblemSpec,
    ScenarioSpec,
    SkipRampSpec,
    StatInputSpec,
    TowerDefenseSpec,
)


def _stat_input(stat_id: str, value: float) -> StatInputSpec:
    return StatInputSpec(
        stat_id=stat_id,
        phase=Phase.START_OF_RUN,
        base_value=value,
        provenance="contract_test",
    )


def _problem_spec() -> ProblemSpec:
    return ProblemSpec(
        scenario=ScenarioSpec(
            mode="farming",
            tier=12,
            wave=100,
            eals_ramp=SkipRampSpec(start=0.0, end=0.0, ramp_waves=1000),
            ehls_ramp=SkipRampSpec(start=0.0, end=0.0, ramp_waves=1000),
            boss_survivability=BossSurvivabilitySpec(
                boss=BossStatsSpec(hp=1.0, attack=1.0, attack_interval=1.0, enrage_mult=1.0),
                tower=TowerDefenseSpec(dr_frac=0.0, regen_per_sec=0.0, shields=0.0),
                combat_params={
                    "hit_interval_id": "default",
                    "defense_abs": 0.0,
                    "damage_reduction": 0.0,
                    "pc_frac": 0.0,
                    "pc_boss_mult": 1.0,
                    "orb_damage_frac": 0.0,
                    "electrons_damage_frac": 0.0,
                },
                bc_params={"boss_hp_mult": 1.0, "boss_attack_mult": 1.0},
            ),
        ),
        stat_inputs=[
            _stat_input("tower_hp", 100.0),
            _stat_input("tower_regen", 10.0),
            _stat_input("def_pct", 0.2),
            _stat_input("wall_hp", 50.0),
            _stat_input("wall_regen", 5.0),
            _stat_input("thorns_damage_mult", 1.0),
            _stat_input("eals_pct", 0.0),
            _stat_input("ehls_pct", 0.0),
            _stat_input("orb_damage_mult", 1.0),
            _stat_input("death_ray_damage_mult", 1.0),
            _stat_input("plasma_cannon_damage_mult", 1.0),
            _stat_input("knockback_mult", 1.0),
        ],
    )




def _compiler_reachable_stat_ids() -> set[str]:
    workshop_ids = {spec.stat_id for spec in _WORKSHOP_STAT_SPECS.values()}
    uw_ids = set()
    for tracks in _UW_TRACK_SPECS.values():
        for spec in tracks.values():
            uw_ids.add(spec.stat_id)
            uw_ids.add(f"{spec.stat_id}_next_cost")
    # Canonical survivability IDs are assembled from workshop/loadout pathways.
    core_ids = {
        "tower_hp",
        "tower_regen",
        "def_pct",
        "wall_hp",
        "wall_regen",
        "thorns_damage_mult",
        "eals_pct",
        "ehls_pct",
        "wave_attack_index",
        "wave_health_index",
    }
    bc_ids = {"orb_damage_mult", "death_ray_damage_mult", "plasma_cannon_damage_mult", "knockback_mult"}
    edamage_ids = {"tower_damage", "tower_attack_speed", "tower_crit_chance", "tower_crit_multiplier", "tower_dps"}
    return workshop_ids | uw_ids | core_ids | bc_ids | edamage_ids

def test_stat_lineage_manifest_has_every_registry_stat_and_sources() -> None:
    manifest = stat_lineage_manifest()
    registry_ids = {definition.stat_id for definition in default_registry().all_defs()}

    assert set(manifest) == registry_ids
    expected_sources = {"workshop", "lab", "card", "module", "relic", "perk", "bc", "uw"}
    for stat_id, entries in manifest.items():
        assert {entry.contributor for entry in entries} == expected_sources, stat_id


def test_stat_lineage_contract_maps_to_registry_and_stat_input_or_exclusion() -> None:
    registry = default_registry()
    manifest = stat_lineage_manifest()
    ids_snapshot = compile_account_snapshot(parse_ids(Path("tests/fixtures/tower-sim-data/_IDS.csv")))
    canonical_build = build_canonical_stat_inputs(
        problem_spec=_problem_spec(),
        ids_snapshot=ids_snapshot,
        registry=registry,
    )
    present_stat_ids = {item.stat_id for item in canonical_build.stat_inputs}

    for entries in manifest.values():
        for entry in entries:
            registry.validate_stat_id(entry.canonical_stat_id)
            if entry.reaches_stat_input:
                assert entry.canonical_stat_id in _compiler_reachable_stat_ids()
                if entry.canonical_stat_id in present_stat_ids:
                    assert entry.exclusion_reason is None
            else:
                assert entry.exclusion_reason is not None
                assert entry.exclusion_reason.startswith("excluded:")


def test_name_contract_gate_ids_sections_to_compiler_to_registry_to_max_wave_consumption() -> None:
    ids_section_names = {spec.name for spec in SECTION_SPECS}
    sections_by_contributor = contributor_ids_sections()
    manifest = stat_lineage_manifest()
    registry = default_registry()

    assert _WORKSHOP_STAT_SPECS
    assert _UW_TRACK_SPECS

    for contributor, sections in sections_by_contributor.items():
        for section_name in sections:
            assert section_name in ids_section_names, f"{contributor}:{section_name}"

    reached_ids = set()
    for entries in manifest.values():
        for entry in entries:
            registry.validate_stat_id(entry.canonical_stat_id)
            if entry.reaches_stat_input:
                reached_ids.add(entry.canonical_stat_id)

    consumed_ids = set(required_max_wave_stat_input_ids())
    assert consumed_ids.issubset(reached_ids)


def test_stat_lineage_sections_put_required_stats_first() -> None:
    sections = ordered_stat_lineage_sections()
    assert sections[0][0] == "required_max_wave_stat_inputs"
    assert sections[0][1] == required_max_wave_stat_input_ids()

    section_ids = [stat_id for _, stat_ids in sections for stat_id in stat_ids]
    registry_ids = [definition.stat_id for definition in default_registry().all_defs()]
    assert set(section_ids) == set(registry_ids)
    assert len(section_ids) == len(registry_ids)
    consumed_ids = set(required_combat_stat_ids())
    assert consumed_ids.issubset(reached_ids)


def test_only_authoritatively_unmapped_workshop_unlock_stats_remain_unwired() -> None:
    manifest = stat_lineage_manifest()
    unwired = {
        stat_id
        for stat_id, entries in manifest.items()
        if all(not entry.reaches_stat_input for entry in entries)
    }
    assert unwired == {"workshop_knockback", "workshop_land_mine", "workshop_shockwave"}
