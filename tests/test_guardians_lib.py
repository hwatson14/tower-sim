import pytest

from tower_sim.libs import guardians_lib


def test_list_guardians_includes_expected_names():
    guardians = guardians_lib.list_guardians()
    assert "Attack" in guardians
    assert "Ally" in guardians
    assert "Bounty" in guardians
    assert "Fetch" in guardians
    assert "Summon" in guardians


def test_get_guardian_attribute_returns_value_cost_and_max_flag():
    value, cost, is_max = guardians_lib.get_guardian_attribute("Attack", "Percentage", 0)
    assert value == pytest.approx(0.01)
    assert cost == 0.0
    assert is_max is False

    value, cost, is_max = guardians_lib.get_guardian_attribute("Attack", "Percentage", 19)
    assert value == pytest.approx(0.2)
    assert cost == pytest.approx(475.0)
    assert is_max is True


def test_unknown_guardian_raises():
    with pytest.raises(guardians_lib.UnknownGuardianError):
        guardians_lib.list_guardian_attributes("Unknown Guardian")


def test_unknown_attribute_raises():
    with pytest.raises(guardians_lib.UnknownGuardianAttributeError):
        guardians_lib.get_guardian_attribute("Attack", "Unknown Attr", 1)
