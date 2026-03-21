from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Dict, Iterable, Optional

from models.stat_input import StatInput

FINGERPRINT_VERSION = 'r68_non_workshop_stat_inputs_v1'


@dataclass(frozen=True)
class CacheFingerprint:
    version: str
    non_workshop_stat_inputs_sha256: str
    state_mode: str
    preset_name: str
    card_preset_name: Optional[str]
    module_preset_name: Optional[str]
    perk_preset_name: Optional[str]
    perks_enabled: bool
    perk_counts_override: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'version': self.version,
            'non_workshop_stat_inputs_sha256': self.non_workshop_stat_inputs_sha256,
            'state_mode': self.state_mode,
            'preset_name': self.preset_name,
            'card_preset_name': self.card_preset_name,
            'module_preset_name': self.module_preset_name,
            'perk_preset_name': self.perk_preset_name,
            'perks_enabled': self.perks_enabled,
            'perk_counts_override': dict(self.perk_counts_override),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> 'CacheFingerprint':
        return cls(
            version=str(payload['version']),
            non_workshop_stat_inputs_sha256=str(payload['non_workshop_stat_inputs_sha256']),
            state_mode=str(payload['state_mode']),
            preset_name=str(payload['preset_name']),
            card_preset_name=payload.get('card_preset_name'),
            module_preset_name=payload.get('module_preset_name'),
            perk_preset_name=payload.get('perk_preset_name'),
            perks_enabled=bool(payload['perks_enabled']),
            perk_counts_override={str(k): int(v) for k, v in dict(payload.get('perk_counts_override') or {}).items()},
        )


class IncrementalCacheFingerprintBuilder:
    def build(
        self,
        *,
        stat_inputs: Iterable[StatInput],
        state_mode: str,
        preset_name: str,
        card_preset_name: Optional[str],
        module_preset_name: Optional[str],
        perk_preset_name: Optional[str],
        perks_enabled: bool,
        perk_counts_override: Optional[Dict[str, int]],
    ) -> CacheFingerprint:
        filtered_rows = []
        for row in stat_inputs:
            if row.source_family == 'workshop':
                continue
            filtered_rows.append({
                'stat_name': row.stat_name,
                'source_family': row.source_family,
                'source_name': row.source_name,
                'value': row.value,
                'value_type': row.value_type,
                'stage': row.stage,
                'active': row.active,
                'preset_name': row.preset_name,
                'provenance': row.provenance,
                'notes': row.notes,
                'contributor_id': row.contributor_id,
                'destination_object_type': row.destination_object_type,
                'destination_id': row.destination_id,
                'resolver_id': row.resolver_id,
                'kb_mapped': row.kb_mapped,
            })
        filtered_rows.sort(key=lambda item: (
            item['stat_name'],
            item['source_family'],
            item['source_name'],
            item['stage'],
            item['value_type'],
            json.dumps(item['value'], sort_keys=True, default=str),
            item['contributor_id'] or '',
        ))
        payload = json.dumps(filtered_rows, sort_keys=True, separators=(',', ':'), default=str)
        digest = hashlib.sha256(payload.encode('utf-8')).hexdigest()
        return CacheFingerprint(
            version=FINGERPRINT_VERSION,
            non_workshop_stat_inputs_sha256=digest,
            state_mode=state_mode,
            preset_name=preset_name,
            card_preset_name=card_preset_name,
            module_preset_name=module_preset_name,
            perk_preset_name=perk_preset_name,
            perks_enabled=perks_enabled,
            perk_counts_override={str(k): int(v) for k, v in dict(perk_counts_override or {}).items()},
        )
