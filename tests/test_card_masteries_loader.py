from tower_sim.loaders.card_masteries import load_card_masteries


def test_load_card_masteries_includes_damage():
    mastery_map = load_card_masteries()
    damage = mastery_map["Damage"]
    assert damage.stone_cost == 750
    assert damage.level_values[0] == "x1.4"
    assert damage.level_values[-1] == "x5"
