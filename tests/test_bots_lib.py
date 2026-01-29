import pytest

from tower_sim.libs import bots_lib


def test_list_bots_includes_expected_names():
    bots = bots_lib.list_bots()
    assert "Flame Bot" in bots
    assert "Thunder Bot" in bots
    assert "Golden Bot" in bots
    assert "Amplify Bot" in bots


def test_get_bot_attribute_returns_value_cost_and_max_flag():
    value, cost, is_max = bots_lib.get_bot_attribute("Flame Bot", "Damage R.", 0)
    assert value == pytest.approx(0.2)
    assert cost == 0.0
    assert is_max is False

    value, cost, is_max = bots_lib.get_bot_attribute("Amplify Bot", "Range", 16)
    assert value == pytest.approx(55.0)
    assert cost is None
    assert is_max is True


def test_unknown_bot_raises():
    with pytest.raises(bots_lib.UnknownBotError):
        bots_lib.list_bot_attributes("Unknown Bot")


def test_unknown_attribute_raises():
    with pytest.raises(bots_lib.UnknownBotAttributeError):
        bots_lib.get_bot_attribute("Flame Bot", "Unknown Attr", 1)
