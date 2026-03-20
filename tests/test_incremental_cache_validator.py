from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.incremental_cache_fingerprint import CacheFingerprint
from engine.incremental_cache_validator import IncrementalCacheValidator
from models.statbook import StatBook


def _fingerprint(*, perks_enabled: bool = True) -> CacheFingerprint:
    return CacheFingerprint(
        version='r68_non_workshop_stat_inputs_v1',
        non_workshop_stat_inputs_sha256='abc123' if perks_enabled else 'def456',
        state_mode='start_of_run',
        preset_name='Farming',
        card_preset_name=None,
        module_preset_name=None,
        perk_preset_name=None,
        perks_enabled=perks_enabled,
        perk_counts_override={},
    )


def test_cache_validator_accepts_matching_non_mutated_levels_and_fingerprint():
    fp = _fingerprint()
    result = IncrementalCacheValidator().validate(
        cached_statbook=StatBook(rows={}),
        cached_workshop_levels_current={'Health': 10, 'Damage': 20},
        requested_workshop_levels_current={'Health': 11, 'Damage': 20},
        mutated_workshop_keys=['Health'],
        cached_reference_fingerprint=fp.to_dict(),
        current_fingerprint=fp,
    )
    assert result.is_valid is True


def test_cache_validator_rejects_non_mutated_level_mismatch():
    fp = _fingerprint()
    result = IncrementalCacheValidator().validate(
        cached_statbook=StatBook(rows={}),
        cached_workshop_levels_current={'Health': 10, 'Damage': 19},
        requested_workshop_levels_current={'Health': 11, 'Damage': 20},
        mutated_workshop_keys=['Health'],
        cached_reference_fingerprint=fp.to_dict(),
        current_fingerprint=fp,
    )
    assert result.is_valid is False
    assert 'Damage' in result.reason


def test_cache_validator_rejects_fingerprint_mismatch():
    result = IncrementalCacheValidator().validate(
        cached_statbook=StatBook(rows={}),
        cached_workshop_levels_current={'Health': 10, 'Damage': 20},
        requested_workshop_levels_current={'Health': 11, 'Damage': 20},
        mutated_workshop_keys=['Health'],
        cached_reference_fingerprint=_fingerprint().to_dict(),
        current_fingerprint=_fingerprint(perks_enabled=False),
    )
    assert result.is_valid is False
    assert 'fingerprint mismatch' in result.reason
