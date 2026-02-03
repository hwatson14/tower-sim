from __future__ import annotations

from tower_sim.run import runner


def test_runner_fixture_result_shape() -> None:
    result = runner.run()
    assert result["evaluator"] == "max_wave"
    assert "fail_closed" in result
    assert isinstance(result.get("missing"), list)
