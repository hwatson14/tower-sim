from qe.models import StatInput
from qe.routing import _resolve_base_times_post_multipliers


def _hp_contributors(*, death_wave_health_value: float) -> list[StatInput]:
    return [
        StatInput(
            stat_name='Health',
            source_family='workshop',
            source_name='Health',
            value=100.0,
            value_type='resolved_value',
            stage='account_state',
        ),
        StatInput(
            stat_name='Health Lab',
            source_family='lab',
            source_name='Health Lab',
            value=3.0,
            value_type='resolved_value',
            stage='account_state',
        ),
        StatInput(
            stat_name='Death Wave Health',
            source_family='lab',
            source_name='Death Wave Health',
            value=death_wave_health_value,
            value_type='resolved_value',
            stage='account_state',
        ),
    ]


def test_hp_death_wave_health_lab_is_post_multiplier_and_zero_is_neutral():
    no_dwh, status_no_dwh, *_ = _resolve_base_times_post_multipliers(
        'tower_hp',
        _hp_contributors(death_wave_health_value=0.0),
        schema={},
    )
    with_dwh, status_with_dwh, *_ = _resolve_base_times_post_multipliers(
        'tower_hp',
        _hp_contributors(death_wave_health_value=12.5),
        schema={},
    )

    assert status_no_dwh == 'resolved'
    assert status_with_dwh == 'resolved'
    assert no_dwh == 300.0
    assert with_dwh == 3750.0
