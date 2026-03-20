from __future__ import annotations

from tower_sim.engines.edamage_formulas import (
    bullet_per_second,
    epd_aspd,
    epd_crit_chance,
    epd_critical,
)


def test_edamage_formula_wrappers_route_through_registry(monkeypatch) -> None:
    calls: list[tuple[str, dict[str, float]]] = []

    def _fake_eval(name: str, args: dict[str, float]) -> float:
        calls.append((name, args))
        return 123.0

    monkeypatch.setattr("tower_sim.engines.edamage_formulas.evaluate_lambda", _fake_eval)

    assert bullet_per_second(1.5) == 123.0
    assert epd_aspd(1, 2, 3, True, 4, 5, 6, 7, False, 8) == 123.0
    assert epd_crit_chance(1, True, 2, 3, 4, 5, False, 6) == 123.0
    assert epd_critical(1, 2, 3, 4, 5) == 123.0

    names = [name for name, _ in calls]
    assert names == [
        "BULLET_PER_SECOND",
        "EPD_ASPD",
        "EPD_CRIT_CHANCE",
        "EPD_CRITICAL",
    ]
