from __future__ import annotations

from typing import Dict, Iterable, List

from engine.stat_engine import resolve_stats
from models.stat_input import StatInput
from models.statbook import StatRow

_ALIAS_OUTPUTS = {
    'support_surface::free_upgrade_multiplier': 'canonical_stat::free_upgrade_multiplier',
}


class IncrementalSubsetExecutor:
    def execute(self, stat_inputs: List[StatInput], target_nodes: Iterable[str]) -> Dict[str, StatRow]:
        reference = resolve_stats(stat_inputs)
        resolved: Dict[str, StatRow] = {}
        for node in target_nodes:
            normalized = self._normalize_target(node)
            row = reference.rows.get(normalized)
            if row is None:
                raise ValueError(f'Unsupported bounded query target nodes: {normalized!r}')
            resolved[node] = row
            if normalized in _ALIAS_OUTPUTS:
                resolved[_ALIAS_OUTPUTS[normalized]] = row
        if any(self._normalize_target(node) in {
            'canonical_stat::free_attack_upgrade_chance_pct',
            'canonical_stat::free_defense_upgrade_chance_pct',
            'canonical_stat::free_utility_upgrade_chance_pct',
        } for node in target_nodes):
            support_row = reference.rows.get('canonical_stat::free_upgrade_multiplier')
            if support_row is not None:
                resolved['canonical_stat::free_upgrade_multiplier'] = support_row
        return resolved

    @staticmethod
    def _normalize_target(node: str) -> str:
        return str(node)
