import pytest

from qe.models import StatInput
from qe.models import StatRow
from qe.routing import _resolve_free_upgrade_chance_pct


def test_free_upgrade_chance_applies_enhancement_to_full_additive_bucket() -> None:
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
    assert final == pytest.approx(75.9)


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
    assert final == pytest.approx(86.94)


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
    assert final == pytest.approx(298.0)


def test_free_upgrade_chance_uses_resolved_support_multiplier_when_direct_enhancement_is_absent() -> None:
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
            stat_name='Relic Free Attack',
            source_family='relic',
            source_name='Relic Free Attack',
            value=0.06,
            value_type='resolved_value',
            stage='account_state',
        ),
        StatInput(
            stat_name='Generator Attack Substat',
            source_family='module_substat',
            source_name='Singularity Harness',
            value=8.0,
            value_type='percent_display',
            stage='loadout_resolved',
        ),
    ]
    resolved_rows = {
        'state::tower.free_upgrade_multiplier': StatRow(
            stat_name='state::tower.free_upgrade_multiplier',
            final_value=1.17,
            value_type='multiplier',
            source_count=1,
            status='resolved',
            contributors=[],
            schema=None,
        ),
    }

    final, status, *_ = _resolve_free_upgrade_chance_pct(
        'free_attack_upgrade_chance_pct',
        contributors,
        schema={},
        resolved_rows=resolved_rows,
    )

    assert status == 'resolved'
    assert final == pytest.approx(74.88)
