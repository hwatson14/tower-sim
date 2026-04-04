from qe.models import StatInput
from qe.routing import _resolve_free_upgrade_chance_pct


def test_free_upgrade_chance_applies_enhancement_to_workshop_base_only() -> None:
    contributors = [
        StatInput(
            stat_name='Free Attack Upgrade',
            source_family='workshop',
            source_name='Free Attack Upgrade',
            value=50.0,
            value_type='resolved_value',
            stage='account_state',
        ),
        StatInput(
            stat_name='Free Upgrades +',
            source_family='enhancement',
            source_name='Free Upgrades +',
            value=1.15,
            value_type='resolved_value',
            stage='account_state',
        ),
        StatInput(
            stat_name='Free Upgrades Card',
            source_family='card',
            source_name='Free Upgrades',
            value=10.0,
            value_type='percent_display',
            stage='account_state',
        ),
        StatInput(
            stat_name='Relic Free Attack',
            source_family='relic',
            source_name='Relic Free Attack',
            value=6.0,
            value_type='percent_display',
            stage='account_state',
        ),
    ]

    final, status, *_ = _resolve_free_upgrade_chance_pct(
        'free_attack_upgrade_chance_pct',
        contributors,
        schema={},
    )

    assert status == 'resolved'
    assert final == 73.5


def test_free_upgrade_chance_normalizes_fractional_module_substat_bonus() -> None:
    contributors = [
        StatInput(
            stat_name='Free Utility Upgrade',
            source_family='workshop',
            source_name='Free Utility Upgrade',
            value=50.0,
            value_type='resolved_value',
            stage='account_state',
        ),
        StatInput(
            stat_name='Free Upgrades +',
            source_family='enhancement',
            source_name='Free Upgrades +',
            value=1.15,
            value_type='resolved_value',
            stage='account_state',
        ),
        StatInput(
            stat_name='Generator Utility Substat',
            source_family='module_substat',
            source_name='Generator Utility Substat',
            value=0.6,
            value_type='resolved_value',
            stage='account_state',
        ),
        StatInput(
            stat_name='Generator Utility Substat',
            source_family='module_substat',
            source_name='Generator Utility Substat',
            value=10.0,
            value_type='percent_display',
            stage='account_state',
        ),
        StatInput(
            stat_name='Free Upgrades Card',
            source_family='card',
            source_name='Free Upgrades',
            value=10.0,
            value_type='percent_display',
            stage='account_state',
        ),
        StatInput(
            stat_name='Relic Free Utility',
            source_family='relic',
            source_name='Relic Free Utility',
            value=5.0,
            value_type='percent_display',
            stage='account_state',
        ),
    ]

    final, status, *_ = _resolve_free_upgrade_chance_pct(
        'free_utility_upgrade_chance_pct',
        contributors,
        schema={},
    )

    assert status == 'resolved'
    assert final == 83.1


def test_free_upgrade_chance_remains_uncapped_when_no_kb_cap_is_registered() -> None:
    contributors = [
        StatInput(
            stat_name='Free Attack Upgrade',
            source_family='workshop',
            source_name='Free Attack Upgrade',
            value=99.0,
            value_type='resolved_value',
            stage='account_state',
        ),
        StatInput(
            stat_name='Free Upgrades +',
            source_family='enhancement',
            source_name='Free Upgrades +',
            value=2.0,
            value_type='resolved_value',
            stage='account_state',
        ),
        StatInput(
            stat_name='Free Upgrades Card',
            source_family='card',
            source_name='Free Upgrades',
            value=50.0,
            value_type='percent_display',
            stage='account_state',
        ),
    ]

    final, status, *_ = _resolve_free_upgrade_chance_pct(
        'free_attack_upgrade_chance_pct',
        contributors,
        schema={},
    )

    assert status == 'resolved'
    assert final == 248.0
