from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.incremental_recalc_runtime import IncrementalRecalcRuntime


def test_runtime_plans_health_chain():
    plan = IncrementalRecalcRuntime().plan_from_workshop_overrides({'Health': 1})
    assert plan.fallback_required is False
    assert 'source_input::workshop:Health' in plan.mutated_source_nodes
    assert 'state::tower.hp' in plan.publishable_dirty_nodes
    assert 'state::wall.hp' in plan.publishable_dirty_nodes


def test_runtime_rejects_unknown_mutation_key():
    plan = IncrementalRecalcRuntime().plan_from_workshop_overrides({'Wall Fortification': 1})
    assert plan.fallback_required is True
    assert 'Unsupported mutation keys' in str(plan.fallback_reason)
