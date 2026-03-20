from __future__ import annotations

import json
import math
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tower_sim.loaders.perk_tables import (
    PerkTableError,
    load_perk_definitions,
    load_perk_pool_weights,
    load_perk_wave_requirement_steps,
)
from tower_sim.engines.perk_timeline_generator import (
    _ideal_wave,
    _offers_count,
    generate_timeline,
)


# ── table loaders ──


def test_load_perk_definitions() -> None:
    perks = load_perk_definitions(REPO_ROOT / "tables/inputs/perks/perks_v1.csv")
    assert perks
    health_perk = next(perk for perk in perks if perk.perk_name == "x1.20 Max Health")
    assert health_perk.stacking_type == "multiplicative"
    assert health_perk.effect_stat_id == "tower_hp"


def test_load_perk_pool_weights() -> None:
    weights = load_perk_pool_weights(REPO_ROOT / "tables/inputs/perks/perk_pool_weights_v1.csv")
    assert weights
    total = sum(weight.weight_percent for weight in weights)
    assert total == 100


def test_load_perk_wave_requirement_steps() -> None:
    steps = load_perk_wave_requirement_steps()
    assert len(steps) == 4
    assert steps[0].perks_taken_threshold == 40
    assert steps[0].base_waves_required == 350
    assert steps[-1].perks_taken_threshold == 0
    assert steps[-1].base_waves_required == 200


# ── reference table verification (WR_LAB=13, SPB=0.25) ──
# Verified against community spreadsheet v0.14.4 and wiki formula

REF_LAB = [187,374,561,748,935,1122,1309,1496,1683,1870,2057,2244,2431,2618,2805,2992,3179,3366,3553,3740,3977,4214,4451,4688,4925,5162,5399,5636,5873,6110,6397,6684,6971,7258,7545,7832,8119,8406,8693,8980,9317,9654,9991,10328,10665]
REF_1PWR = [187,280,420,561,701,841,981,1122,1262,1402,1542,1683,1823,1963,2103,2244,2384,2524,2664,2805,2982,3160,3338,3516,3693,3871,4049,4227,4404,4582,4797,5013,5228,5443,5658,5874,6089,6304,6519,6735,6987,7240,7493,7746,7998]


def test_reference_table_lab_column_45_of_45() -> None:
    """0 PWR stacks must match all 45 reference values exactly."""
    steps = load_perk_wave_requirement_steps()
    for i in range(45):
        computed = _ideal_wave(i + 1, 0, 13, 0.25, steps)
        assert computed == REF_LAB[i], f"Perk {i+1}: expected={REF_LAB[i]} got={computed}"


def test_reference_table_1pwr_column_45_of_45() -> None:
    """1 PWR stack (from perk 2) must match all 45 reference values exactly."""
    steps = load_perk_wave_requirement_steps()
    for i in range(45):
        stacks = 0 if i == 0 else 1
        computed = _ideal_wave(i + 1, stacks, 13, 0.25, steps)
        assert computed == REF_1PWR[i], f"Perk {i+1}: expected={REF_1PWR[i]} got={computed}"


def test_reference_table_section_boundaries() -> None:
    """Verify section transitions at perks 21, 31, 41."""
    steps = load_perk_wave_requirement_steps()
    # Lab column section boundaries
    assert _ideal_wave(20, 0, 13, 0.25, steps) == 3740
    assert _ideal_wave(21, 0, 13, 0.25, steps) == 3977   # +237 (base 250-13)
    assert _ideal_wave(30, 0, 13, 0.25, steps) == 6110
    assert _ideal_wave(31, 0, 13, 0.25, steps) == 6397   # +287 (base 300-13)
    assert _ideal_wave(40, 0, 13, 0.25, steps) == 8980
    assert _ideal_wave(41, 0, 13, 0.25, steps) == 9317   # +337 (base 350-13)


def test_pwr_stacking_is_linear_additive() -> None:
    """PWR uses linear stacking per KB entity-registry stacking_type=additive."""
    steps = load_perk_wave_requirement_steps()
    # 1 stack: reduction = 0.20 * 1.25 = 0.25, residual = 0.75
    # 2 stacks: reduction = 0.40 * 1.25 = 0.50, residual = 0.50
    # 3 stacks: reduction = 0.60 * 1.25 = 0.75, residual = 0.25
    w0 = _ideal_wave(10, 0, 13, 0.25, steps)
    w1 = _ideal_wave(10, 1, 13, 0.25, steps)
    w2 = _ideal_wave(10, 2, 13, 0.25, steps)
    w3 = _ideal_wave(10, 3, 13, 0.25, steps)
    assert w0 == 1870  # 10 * 187
    assert w1 == 1402  # floor(10 * 140.25)
    assert w2 == 935   # floor(10 * 93.5) -- note: matches ref 2PWR at perk 10 exactly
    assert w3 == 467   # floor(10 * 46.75)


def test_offers_count() -> None:
    assert _offers_count(0) == 2
    assert _offers_count(1) == 3
    assert _offers_count(2) == 4
    assert _offers_count(3) == 4


# ── timeline generation with bug fix verification ──


def _write_policy(tmp: Path, overrides: dict) -> Path:
    base = {
        "seed": 42,
        "target_wave": 3000,
        "waves_required_lab": 13,
        "standard_perk_bonus": 0.25,
        "perk_option_quantity": 2,
        "ban_perks_capacity": 6,
        "banned_perks": [],
        "priority_order": [],
        "first_perk_choice": None,
    }
    base.update(overrides)
    path = tmp / "policy.json"
    path.write_text(json.dumps(base), encoding="utf-8")
    return path


def test_timeline_generates_rows(tmp_path: Path) -> None:
    policy = _write_policy(tmp_path, {})
    timeline, diag = generate_timeline(policy)
    assert diag["generated_rows"] > 0
    assert diag["final_wave"] <= 3000
    assert diag["pwr_model"] == "retroactive_linear_additive"
    assert all("wave" in row and "perk_taken" in row for row in timeline)


def test_retroactive_burst_awards_multiple_perks_at_same_wave(tmp_path: Path) -> None:
    """When PWR is picked and retroactive ideal places next perks in the past, award immediately."""
    policy = _write_policy(tmp_path, {
        "target_wave": 50000,
        "priority_order": ["Perk Wave Requirement -20.00%"],
        "first_perk_choice": "Perk Wave Requirement -20.00%",
    })
    timeline, diag = generate_timeline(policy)
    # After 3 PWR picks, several perks should burst at the same wave
    burst_perks = [r for r in timeline if r.get("retroactive_burst")]
    assert len(burst_perks) > 0, "No burst perks detected after PWR picks"


def test_exhausted_perks_removed_from_pool(tmp_path: Path) -> None:
    """Exhausted perks must not appear in offers after reaching max_picks."""
    policy = _write_policy(tmp_path, {
        "target_wave": 50000,
        "priority_order": ["Unlock a Random Ultimate Weapon"],
    })
    timeline, diag = generate_timeline(policy)
    uw_picks = [r for r in timeline if r["perk_taken"] == "Unlock a Random Ultimate Weapon"]
    assert len(uw_picks) <= 1
    assert diag["perks_taken"] > 1
    exhausted = False
    for row in timeline:
        if row["perk_taken"] == "Unlock a Random Ultimate Weapon":
            exhausted = True
            continue
        if exhausted and "Unlock a Random Ultimate Weapon" in row["offered"]:
            raise AssertionError("Exhausted perk appeared in offers")


def test_priority_skips_exhausted_perks(tmp_path: Path) -> None:
    policy = _write_policy(tmp_path, {
        "target_wave": 50000,
        "priority_order": ["Orbs +1", "x1.20 Max Health"],
    })
    timeline, diag = generate_timeline(policy)
    orb_picks = [r for r in timeline if r["perk_taken"] == "Orbs +1"]
    health_picks = [r for r in timeline if r["perk_taken"] == "x1.20 Max Health"]
    assert len(orb_picks) <= 2
    assert len(health_picks) <= 5
    assert diag["perks_taken"] > 7


def test_first_perk_choice_respects_bans(tmp_path: Path) -> None:
    policy = _write_policy(tmp_path, {
        "banned_perks": ["x1.20 Max Health"],
        "first_perk_choice": "x1.20 Max Health",
    })
    timeline, diag = generate_timeline(policy)
    if timeline:
        assert timeline[0]["perk_taken"] != "x1.20 Max Health"


def test_no_perk_exceeds_max_picks(tmp_path: Path) -> None:
    policy = _write_policy(tmp_path, {"target_wave": 50000})
    timeline, diag = generate_timeline(policy)
    perks = {p.perk_name: p for p in load_perk_definitions()}
    for perk_name, count in diag["taken_counts"].items():
        max_picks = perks[perk_name].max_picks
        assert count <= max_picks, f"{perk_name} taken {count} times but max_picks={max_picks}"


def test_timeline_waves_are_monotonically_nondecreasing(tmp_path: Path) -> None:
    """Waves must be non-decreasing (equal is OK for retroactive bursts)."""
    policy = _write_policy(tmp_path, {
        "target_wave": 50000,
        "priority_order": ["Perk Wave Requirement -20.00%"],
        "first_perk_choice": "Perk Wave Requirement -20.00%",
    })
    timeline, _ = generate_timeline(policy)
    waves = [row["wave"] for row in timeline]
    for i in range(1, len(waves)):
        assert waves[i] >= waves[i - 1], f"Decrease at index {i}: {waves[i-1]} > {waves[i]}"


def test_banned_perks_never_taken(tmp_path: Path) -> None:
    policy = _write_policy(tmp_path, {
        "banned_perks": ["Interest x1.50", "x1.15 Cash Bonus"],
    })
    timeline, diag = generate_timeline(policy)
    taken_names = {row["perk_taken"] for row in timeline}
    assert "Interest x1.50" not in taken_names
    assert "x1.15 Cash Bonus" not in taken_names


def test_quantity_field_matches_taken_counts(tmp_path: Path) -> None:
    policy = _write_policy(tmp_path, {"target_wave": 50000})
    timeline, diag = generate_timeline(policy)
    running: dict[str, int] = {}
    for row in timeline:
        name = row["perk_taken"]
        running[name] = running.get(name, 0) + 1
        assert row["quantity"] == running[name]


# ── runner ──

if __name__ == "__main__":
    import tempfile, inspect

    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for test_fn in tests:
        name = test_fn.__name__
        try:
            sig = inspect.signature(test_fn)
            if "tmp_path" in sig.parameters:
                with tempfile.TemporaryDirectory() as td:
                    test_fn(Path(td))
            else:
                test_fn()
            print(f"  PASS: {name}")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {name}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
