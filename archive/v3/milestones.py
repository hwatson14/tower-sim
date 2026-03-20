"""v3 milestone status evaluators.

Step-7 scope: provide executable milestone checks without inventing mechanics.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from v3.account_input_registry import registry_counts
from v3.mechanics_activation import build_domain_activation_plan
from v3.pipeline import StageRequest, compose_static_stage_from_ids


@dataclass(frozen=True)
class MilestoneStatus:
    milestone: str
    status: str
    evidence: str


def evaluate_milestones(ids_path: Path) -> list[MilestoneStatus]:
    counts = registry_counts()
    all_families_loaded = all(v > 0 for v in counts.values())
    milestone_a = MilestoneStatus(
        milestone="A",
        status="green" if all_families_loaded else "blocked",
        evidence=f"registry_counts={counts}",
    )

    # B remains a parity slice target; executable seed check only.
    stage = compose_static_stage_from_ids(ids_path, StageRequest(stage="baseline_max_progression", strict_kb_routing=False))
    milestone_b = MilestoneStatus(
        milestone="B",
        status="in_progress" if bool(stage.resolved_targets) else "blocked",
        evidence=f"resolved_stat_count={len(stage.resolved_targets)}",
    )

    # C blocked until A/B locked and additional domain activation enabled.
    plan = build_domain_activation_plan()
    enabled_domains = [p.domain for p in plan if p.enabled]
    milestone_c = MilestoneStatus(
        milestone="C",
        status="blocked",
        evidence=f"enabled_domains={enabled_domains}",
    )

    return [milestone_a, milestone_b, milestone_c]
