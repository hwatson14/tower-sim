from tower_sim.libs.card_masteries_lib import load_card_mastery_map, load_card_mastery_rows


def test_load_card_mastery_rows_has_expected_count():
    rows = load_card_mastery_rows()
    assert len(rows) == 31


def test_load_card_mastery_map_includes_damage():
    mastery_map = load_card_mastery_map()
    damage = mastery_map["Damage"]
    assert damage.stone_cost == 750
    assert damage.level_values[0] == "x1.4"
    assert damage.level_values[-1] == "x5"
