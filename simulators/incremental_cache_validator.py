from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from simulators.incremental_cache_fingerprint import CacheFingerprint
from qe.models import StatBook


@dataclass(frozen=True)
class CacheValidationResult:
    is_valid: bool
    reason: Optional[str] = None


class IncrementalCacheValidator:
    def validate(
        self,
        *,
        cached_statbook: Optional[StatBook],
        cached_workshop_levels_current: Optional[Dict[str, int]],
        requested_workshop_levels_current: Dict[str, int],
        mutated_workshop_keys: list[str],
        cached_reference_fingerprint: Optional[Dict[str, Any]],
        current_fingerprint: CacheFingerprint,
    ) -> CacheValidationResult:
        if cached_statbook is None:
            return CacheValidationResult(False, 'Missing cached_reference_statbook')
        if cached_workshop_levels_current is None:
            return CacheValidationResult(False, 'Missing cached_reference_workshop_levels_current')
        if cached_reference_fingerprint is None:
            return CacheValidationResult(False, 'Missing cached_reference_fingerprint')

        try:
            cached_fp = CacheFingerprint.from_dict(cached_reference_fingerprint)
        except Exception as exc:
            return CacheValidationResult(False, f'Invalid cached_reference_fingerprint: {exc}')
        if cached_fp.to_dict() != current_fingerprint.to_dict():
            return CacheValidationResult(False, 'Cache fingerprint mismatch outside workshop-mutated scope')

        mismatches = []
        mutated = set(mutated_workshop_keys)
        for key, requested_level in requested_workshop_levels_current.items():
            if key in mutated:
                continue
            cached_level = cached_workshop_levels_current.get(key)
            if cached_level != requested_level:
                mismatches.append(key)
        if mismatches:
            return CacheValidationResult(False, f'Cache workshop mismatch outside mutated keys: {sorted(mismatches)}')
        return CacheValidationResult(True, None)
