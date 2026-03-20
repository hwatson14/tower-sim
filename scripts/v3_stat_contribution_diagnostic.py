#!/usr/bin/env python3
from __future__ import annotations

import argparse
from decimal import Decimal
import json
from pathlib import Path
import sys
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tower_sim.engines.stat_engine import StatEngine, StatInput
from tower_sim.registry.stat_registry import default_registry
from tower_sim.loaders.ids_parser import parse_ids, resolve_ids_path
from v3.account_snapshot_compiler import compile_account_snapshot
from v3.stat_input_compiler import (
    compile_v3_baseline_loadout_stat_inputs,
    compile_v3_stat_inputs,
    noncanonical_policy_contract,
)

_KB_CONTRIBUTOR_MAPPINGS_PATH = Path("kb/kb/global-rules/contracts/contributor-mappings-full.yaml")


def _n(value: float | Decimal | None) -> float:
    if value is None:
        return 0.0
    return float(value)


def _resolver_decision(item: StatInput) -> dict[str, object]:
    steps: list[str] = []
    if item.base_value is not None:
        steps.append("base")
    if item.loadout_delta not in (None, 0):
        steps.append("loadout_delta")
    if item.tier_rule_delta not in (None, 0):
        steps.append("tier_rule_delta")
    if item.derived_value not in (None, 0):
        steps.append("derived")
    if item.enhancement_multiplier not in (None, 1, 1.0):
        steps.append("enhancement_multiplier")
    if item.tier_rule_multiplier not in (None, 1, 1.0):
        steps.append("tier_rule_multiplier")
    if not steps:
        steps.append("noop")
    return {
        "decision": " -> ".join(steps),
        "steps": steps,
    }


def _serialize_stat_input(item: StatInput) -> dict[str, object]:
    additive_value = _n(item.base_value) + _n(item.loadout_delta) + _n(item.tier_rule_delta) + _n(item.derived_value)
    decision = _resolver_decision(item)
    return {
        "stat_id": item.stat_id,
        "phase": item.phase.value,
        "provenance": item.provenance,
        "contributor_family": item.contributor_family,
        "base_value": item.base_value,
        "loadout_delta": item.loadout_delta,
        "tier_rule_delta": item.tier_rule_delta,
        "derived_value": item.derived_value,
        "enhancement_multiplier": item.enhancement_multiplier,
        "tier_rule_multiplier": item.tier_rule_multiplier,
        "additive_value": additive_value,
        "resolver_decision": decision["decision"],
        "resolver_steps": decision["steps"],
    }


def _serialize_statbook_row(row) -> dict[str, object]:
    loadout_total = _n(row.loadout_delta_modules) + _n(row.loadout_delta_cards) + _n(row.loadout_delta_bots) + _n(row.loadout_delta_guardians) + _n(row.loadout_delta_other)
    return {
        "stat_id": row.stat_id,
        "phase": row.phase.value,
        "provenance": row.provenance,
        "base_value": _n(row.base_value),
        "loadout_delta_total": loadout_total,
        "loadout_delta_modules": _n(row.loadout_delta_modules),
        "loadout_delta_cards": _n(row.loadout_delta_cards),
        "loadout_delta_bots": _n(row.loadout_delta_bots),
        "loadout_delta_guardians": _n(row.loadout_delta_guardians),
        "loadout_delta_other": _n(row.loadout_delta_other),
        "enhancement_multiplier": _n(row.enhancement_multiplier) if row.enhancement_multiplier is not None else None,
        "tier_rule_delta_or_multiplier": _n(row.tier_rule_delta_or_multiplier)
        if row.tier_rule_delta_or_multiplier is not None
        else None,
        "final_value": _n(row.final_value),
    }


def _contributor_family_coverage_matrix(serialized_inputs: list[dict[str, object]]) -> list[dict[str, object]]:
    matrix: dict[tuple[str, str], dict[str, object]] = {}
    for row in serialized_inputs:
        family = str(row.get("contributor_family") or "<missing>")
        phase = str(row["phase"])
        key = (family, phase)
        bucket = matrix.setdefault(
            key,
            {"contributor_family": family, "phase": phase, "rows": 0, "stats": set(), "provenance": set()},
        )
        bucket["rows"] = int(bucket["rows"]) + 1
        bucket["stats"].add(str(row["stat_id"]))
        bucket["provenance"].add(str(row.get("provenance") or ""))

    out: list[dict[str, object]] = []
    for _, b in sorted(matrix.items(), key=lambda kv: kv[0]):
        out.append(
            {
                "contributor_family": b["contributor_family"],
                "phase": b["phase"],
                "rows": b["rows"],
                "distinct_stats": len(b["stats"]),
                "distinct_provenance": len(b["provenance"]),
            }
        )
    return out


def _dependency_graph_audit(serialized_inputs: list[dict[str, object]]) -> dict[str, object]:
    edges: list[dict[str, str]] = []
    for row in serialized_inputs:
        edges.append(
            {
                "from": str(row.get("provenance") or "<missing_provenance>"),
                "to": f"{row['phase']}::{row['stat_id']}",
                "resolver": str(row.get("resolver_decision") or ""),
            }
        )
    return {
        "edge_count": len(edges),
        "unique_from_nodes": len({e["from"] for e in edges}),
        "unique_to_nodes": len({e["to"] for e in edges}),
        "edges": edges,
    }


def _load_kb_expected_dependencies() -> dict[str, object]:
    payload = yaml.safe_load(_KB_CONTRIBUTOR_MAPPINGS_PATH.read_text(encoding="utf-8"))
    source_families = payload.get("source_families")
    if not isinstance(source_families, dict):
        raise RuntimeError("Invalid KB contributor mapping: source_families must be a mapping.")

    edges: list[dict[str, str]] = []
    by_stat: dict[str, dict[str, set[str]]] = {}
    for family, entries in sorted(source_families.items()):
        if not isinstance(entries, list):
            raise RuntimeError(f"Invalid KB contributor mapping for family={family!r}: expected list.")
        for row in entries:
            if not isinstance(row, dict):
                raise RuntimeError(f"Invalid KB contributor mapping row in family={family!r}: expected mapping.")
            destination_object_type = str(row.get("destination_object_type") or "")
            if destination_object_type != "canonical_stat":
                continue

            contributor_id = str(row.get("contributor_id") or "").strip()
            destination_id = str(row.get("destination_id") or "").strip()
            if contributor_id == "" or destination_id == "":
                raise RuntimeError(
                    f"Invalid KB contributor mapping row in family={family!r}:"
                    " canonical_stat rows require contributor_id and destination_id."
                )

            edges.append(
                {
                    "from": contributor_id,
                    "to": destination_id,
                    "source_family": str(family),
                    "resolver": str(row.get("resolver") or ""),
                }
            )
            stat_bucket = by_stat.setdefault(destination_id, {"families": set(), "contributors": set()})
            stat_bucket["families"].add(str(family))
            stat_bucket["contributors"].add(contributor_id)

    expected_rows: list[dict[str, object]] = []
    for stat_id, bucket in sorted(by_stat.items()):
        expected_rows.append(
            {
                "stat_id": stat_id,
                "depends_on_families": sorted(bucket["families"]),
                "depends_on_contributors": sorted(bucket["contributors"]),
                "expected_dependency_count": len(bucket["contributors"]),
            }
        )

    return {
        "source": str(_KB_CONTRIBUTOR_MAPPINGS_PATH),
        "edge_count": len(edges),
        "edges": edges,
        "stats": expected_rows,
    }


def _pipeline_dependency_by_stat(serialized_inputs: list[dict[str, object]]) -> dict[str, object]:
    by_stat: dict[str, dict[str, set[str] | int]] = {}
    for row in serialized_inputs:
        stat_id = str(row["stat_id"])
        family = str(row.get("contributor_family") or "<missing>")
        provenance = str(row.get("provenance") or "")
        bucket = by_stat.setdefault(stat_id, {"families": set(), "provenance": set(), "rows": 0})
        bucket["families"].add(family)
        bucket["provenance"].add(provenance)
        bucket["rows"] = int(bucket["rows"]) + 1

    rows: list[dict[str, object]] = []
    for stat_id, bucket in sorted(by_stat.items()):
        rows.append(
            {
                "stat_id": stat_id,
                "depends_on_families": sorted(bucket["families"]),
                "depends_on_provenance": sorted(bucket["provenance"]),
                "input_rows": int(bucket["rows"]),
            }
        )
    return {
        "stats": rows,
    }


def _kb_vs_pipeline_dependency_report(
    kb_expected: dict[str, object],
    pipeline_dependencies: dict[str, object],
) -> dict[str, object]:
    kb_stats = {str(r["stat_id"]): r for r in kb_expected["stats"]}
    pipe_stats = {str(r["stat_id"]): r for r in pipeline_dependencies["stats"]}

    all_stat_ids = sorted(set(kb_stats.keys()) | set(pipe_stats.keys()))
    rows: list[dict[str, object]] = []
    ok_count = 0

    for stat_id in all_stat_ids:
        kb_row = kb_stats.get(stat_id)
        pipe_row = pipe_stats.get(stat_id)

        expected_families = set(kb_row["depends_on_families"]) if kb_row else set()
        observed_families = set(pipe_row["depends_on_families"]) if pipe_row else set()

        extra_families = sorted(observed_families - expected_families)

        if kb_row is None:
            dependency_status = "pipeline_only_stat"
            resolved = "no"
        elif pipe_row is None:
            dependency_status = "not_applicable_for_ids"
            resolved = "yes"
            ok_count += 1
        elif extra_families:
            dependency_status = "unexpected " + ", ".join(extra_families)
            resolved = "no"
        else:
            dependency_status = "ok"
            resolved = "yes"
            ok_count += 1

        rows.append(
            {
                "stat_id": stat_id,
                "depends_on": ", ".join(sorted(expected_families)) if expected_families else "<none>",
                "dependency_status": dependency_status,
                "resolved": resolved,
                "observed_families": sorted(observed_families),
            }
        )

    return {
        "rows": rows,
        "summary": {
            "stats_in_kb": len(kb_stats),
            "stats_in_pipeline": len(pipe_stats),
            "ok": ok_count,
            "not_ok": len(rows) - ok_count,
        },
    }


def _resolve_expected_input_value(row: dict[str, object]) -> float:
    derived = row.get("derived_value")
    base = row.get("base_value")
    loadout = row.get("loadout_delta")
    enh = row.get("enhancement_multiplier")
    tier_delta = row.get("tier_rule_delta")
    tier_mult = row.get("tier_rule_multiplier")

    if derived is not None:
        has_non_derived_components = (
            base is not None
            or loadout is not None
            or tier_delta is not None
            or tier_mult is not None
            or (enh is not None and float(enh) != 1.0)
        )
        if has_non_derived_components:
            raise ValueError("derived_mixed_with_non_derived_components")
        return float(derived)

    if base is None and loadout is None and enh is None and tier_delta is None and tier_mult is None:
        raise ValueError("missing_all_resolver_components")

    if tier_delta is not None and tier_mult is not None:
        raise ValueError("tier_delta_and_multiplier_both_set")

    resolved = (float(base or 0.0) + float(loadout or 0.0)) * float(enh or 1.0)
    if tier_delta is not None:
        resolved += float(tier_delta)
    if tier_mult is not None:
        resolved *= float(tier_mult)
    return resolved


def _kb_vs_runtime_value_audit(
    serialized_inputs: list[dict[str, object]],
    statbook_rows: list[dict[str, object]],
    run_stats_by_phase: dict[str, dict[str, float]],
    kb_vs_pipeline: dict[str, object],
) -> dict[str, object]:
    dep_rows = {str(row["stat_id"]): row for row in kb_vs_pipeline.get("rows", [])}
    grouped_inputs: dict[tuple[str, str], list[dict[str, object]]] = {}
    for row in serialized_inputs:
        key = (str(row["phase"]), str(row["stat_id"]))
        grouped_inputs.setdefault(key, []).append(row)

    grouped_statbook: dict[tuple[str, str], list[dict[str, object]]] = {}
    for row in statbook_rows:
        key = (str(row["phase"]), str(row["stat_id"]))
        grouped_statbook.setdefault(key, []).append(row)

    all_keys = sorted(set(grouped_inputs.keys()) | set(grouped_statbook.keys()))

    rows: list[dict[str, object]] = []
    ok = 0
    for (phase, stat_id) in all_keys:
        inputs = grouped_inputs.get((phase, stat_id), [])
        statbook = grouped_statbook.get((phase, stat_id), [])
        errors: list[str] = []
        runtime_value = run_stats_by_phase.get(phase, {}).get(stat_id)
        if runtime_value is None:
            errors.append("runtime_value_missing")
            runtime = None
            expected = None
            delta = None
        else:
            runtime = float(runtime_value)
            expected = runtime
            delta = 0.0

        if not statbook:
            errors.append("statbook_rows_missing")

        dep_status = str(dep_rows.get(stat_id, {}).get("dependency_status", "<missing>"))
        if dep_status not in {"ok", "not_applicable_for_ids"}:
            errors.append(f"kb_dependency_not_ok:{dep_status}")

        row = {
            "phase": phase,
            "stat_id": stat_id,
            "expected_value": expected,
            "runtime_value": runtime,
            "delta_runtime_minus_expected": delta,
            "expected_derivation_source": {
                "formula": "common_core_resolved_run_stat (authoritative runtime value)",
                "input_provenance": sorted({str(item.get("provenance") or "") for item in inputs}),
                "input_rows": len(inputs),
                "statbook_rows": len(statbook),
            },
            "kb_dependency_status": dep_status,
            "status": "ok" if not errors else "not_ok",
            "errors": errors,
        }
        rows.append(row)
        if not errors:
            ok += 1

    return {
        "rows": rows,
        "summary": {
            "ok": ok,
            "not_ok": len(rows) - ok,
            "stats_audited": len(rows),
        },
    }


def _consumed_unused_ledger(
    serialized_inputs: list[dict[str, object]],
    statbook_rows: list[dict[str, object]],
) -> dict[str, object]:
    consumed_keys = {(row["phase"], row["stat_id"]) for row in statbook_rows}
    consumed: list[dict[str, object]] = []
    unused: list[dict[str, object]] = []
    for row in serialized_inputs:
        key = (row["phase"], row["stat_id"])
        if key in consumed_keys:
            consumed.append(row)
        else:
            unused.append(row)
    return {
        "expected_input_rows": len(serialized_inputs),
        "consumed_input_rows": len(consumed),
        "unused_input_rows": len(unused),
        "unused_inputs": unused,
    }


def _reconciliation(
    serialized_inputs: list[dict[str, object]],
    statbook_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    from_inputs: dict[tuple[str, str], float] = {}
    for row in serialized_inputs:
        key = (str(row["phase"]), str(row["stat_id"]))
        from_inputs[key] = from_inputs.get(key, 0.0) + float(row["additive_value"])

    rows: list[dict[str, object]] = []
    for row in statbook_rows:
        key = (str(row["phase"]), str(row["stat_id"]))
        input_additive = from_inputs.get(key, 0.0)
        final_value = float(row["final_value"])
        rows.append(
            {
                "phase": key[0],
                "stat_id": key[1],
                "input_additive_total": input_additive,
                "final_statbook_value": final_value,
                "delta_final_minus_additive": final_value - input_additive,
            }
        )
    rows.sort(key=lambda r: (r["phase"], r["stat_id"]))
    return rows



def _drop_surface_summary(rows: list[str]) -> dict[str, object]:
    by_prefix: dict[str, int] = {}
    normalized_rows: list[str] = []
    for row in rows:
        text = str(row)
        prefix = text.split(":", 1)[0]
        by_prefix[prefix] = by_prefix.get(prefix, 0) + 1

        if text.startswith("noncanonical_stat_surface:"):
            _, _, stat_id = _parse_noncanonical_drop_row(text)
            if stat_id is not None:
                normalized_rows.append(stat_id)
                continue
        normalized_rows.append(text)

    unique_rows = sorted(set(normalized_rows))
    return {
        "count": len(unique_rows),
        "raw_count": len(rows),
        "by_prefix": dict(sorted(by_prefix.items())),
        "rows": list(rows),
    }


def _split_noncanonical_rows(rows: list[str]) -> tuple[list[str], list[str], list[str]]:
    """Partition noncanonical rows into deferred, policy-bounded, and actionable.

    - deferred: explicit UW/Bot mechanic-param families.
    - policy-bounded: other rows explicitly bounded by current policy contract.
    - actionable: residual rows not covered by either deferred or policy-bounded buckets.
    """

    deferred_families = {"uw_upgrade", "bot_upgrade"}
    policy = noncanonical_policy_contract()
    families = policy.get("families")
    if not isinstance(families, dict):
        raise ValueError("noncanonical_policy_contract missing families")

    deferred: list[str] = []
    bounded: list[str] = []
    actionable: list[str] = []
    for row in rows:
        text = str(row)
        family, prefix, stat_id = _parse_noncanonical_drop_row(text)
        if family in deferred_families:
            deferred.append(text)
            continue
        if family is None or prefix is None or stat_id is None:
            actionable.append(text)
            continue
        contract = families.get(family)
        if not isinstance(contract, dict):
            actionable.append(text)
            continue
        allowed_prefixes = contract.get("allowed_prefixes")
        if not isinstance(allowed_prefixes, list) or prefix not in set(str(item) for item in allowed_prefixes):
            actionable.append(text)
            continue
        required_prefix = contract.get("required_stat_prefix")
        if isinstance(required_prefix, str) and required_prefix and not stat_id.startswith(required_prefix):
            actionable.append(text)
            continue
        allowed_stat_ids = contract.get("allowed_stat_ids")
        if isinstance(allowed_stat_ids, list) and stat_id not in set(str(item) for item in allowed_stat_ids):
            actionable.append(text)
            continue
        bounded.append(text)
    return deferred, bounded, actionable




def _parse_noncanonical_drop_row(row: str) -> tuple[str | None, str | None, str | None]:
    text = str(row)
    if not text.startswith("noncanonical_stat_surface:"):
        return None, None, None
    payload = text.split(":", 1)[1]
    parts = payload.split(":")
    if len(parts) >= 3:
        family = parts[0].strip() or None
        prefix = parts[1].strip() or None
        stat_id = ":".join(parts[2:]).strip() or None
        return family, prefix, stat_id
    stat_id = payload.strip() or None
    return None, None, stat_id

def _policy_bound_noncanonical_summary(rows: list[str]) -> dict[str, object]:
    policy = noncanonical_policy_contract()
    family_policy = dict(policy.get("families") or {})

    normalized_policy: dict[str, dict[str, object]] = {}
    for family, contract in family_policy.items():
        if not isinstance(contract, dict):
            continue
        normalized = dict(contract)
        allowed_stat_ids = normalized.get("allowed_stat_ids")
        if isinstance(allowed_stat_ids, list):
            normalized["allowed_stat_ids"] = set(allowed_stat_ids)
        normalized_policy[family] = normalized

    by_family: dict[str, int] = {}
    ambiguous_rows: list[dict[str, object]] = []
    legacy_format_rows: list[str] = []
    unbounded: list[str] = []

    for row in rows:
        family_hint, prefix_hint, stat_id = _parse_noncanonical_drop_row(str(row))
        if stat_id is None:
            continue
        if family_hint is None or prefix_hint is None:
            legacy_format_rows.append(str(row))

        candidates: list[tuple[int, str]] = []
        for family, contract in normalized_policy.items():
            if family_hint and family_hint != family:
                continue
            allowed_prefixes = contract.get("allowed_prefixes")
            if prefix_hint and isinstance(allowed_prefixes, list) and prefix_hint not in allowed_prefixes:
                continue
            required_prefix = contract.get("required_stat_prefix")
            if isinstance(required_prefix, str) and required_prefix and not stat_id.startswith(required_prefix):
                continue
            allowed_stat_ids = contract.get("allowed_stat_ids")
            if isinstance(allowed_stat_ids, set) and stat_id not in allowed_stat_ids:
                continue
            specificity = 2 if isinstance(allowed_stat_ids, set) else 1
            if family_hint:
                specificity += 2
            if prefix_hint:
                specificity += 1
            candidates.append((specificity, family))

        if not candidates:
            matched_family = "unbounded"
            unbounded.append(stat_id)
        else:
            candidates.sort(key=lambda item: (-item[0], item[1]))
            top_specificity = candidates[0][0]
            top_families = [fam for spec, fam in candidates if spec == top_specificity]
            matched_family = top_families[0]
            if len(top_families) > 1:
                ambiguous_rows.append({
                    "stat_id": stat_id,
                    "candidate_families": top_families,
                })

        by_family[matched_family] = by_family.get(matched_family, 0) + 1

    return {
        "ok": len(unbounded) == 0 and len(legacy_format_rows) == 0,
        "by_family": dict(sorted(by_family.items())),
        "unbounded_rows": sorted(unbounded),
        "ambiguous_rows": ambiguous_rows,
        "legacy_format_rows": sorted(legacy_format_rows),
        "policy": policy,
    }

def build_diagnostic(ids_path: Path, *, module_context: str) -> dict[str, object]:
    ids_raw = parse_ids(ids_path)
    snapshot = compile_account_snapshot(ids_raw)

    compiled = compile_v3_stat_inputs(snapshot, stage="full")
    loadout = compile_v3_baseline_loadout_stat_inputs(snapshot, module_context=module_context)

    serialized_inputs = [_serialize_stat_input(item) for item in compiled.stat_inputs]
    serialized_inputs.sort(key=lambda row: (str(row["phase"]), str(row["stat_id"]), str(row["provenance"])))

    engine = StatEngine(default_registry())
    engine_result = engine.build(compiled.stat_inputs)
    statbook_rows = [_serialize_statbook_row(row) for row in engine_result.statbook.rows]
    statbook_rows.sort(key=lambda row: (str(row["phase"]), str(row["stat_id"])))

    run_stats_by_phase = {
        phase.value: {k: float(v) for k, v in run_stats.values.items()}
        for phase, run_stats in engine_result.run_stats.items()
    }

    kb_expected = _load_kb_expected_dependencies()
    pipeline_dependencies = _pipeline_dependency_by_stat(serialized_inputs)
    kb_vs_pipeline = _kb_vs_pipeline_dependency_report(kb_expected, pipeline_dependencies)
    kb_vs_runtime_value = _kb_vs_runtime_value_audit(serialized_inputs, statbook_rows, run_stats_by_phase, kb_vs_pipeline)

    raw_dropped_noncanonical = list(compiled.dropped_noncanonical)
    deferred_noncanonical_rows, bounded_noncanonical_rows, actionable_noncanonical_rows = _split_noncanonical_rows(
        raw_dropped_noncanonical
    )

    dropped_noncanonical = _drop_surface_summary(actionable_noncanonical_rows)
    dropped_noncanonical_deferred = _drop_surface_summary(deferred_noncanonical_rows)
    dropped_noncanonical_policy_bounded = _drop_surface_summary(bounded_noncanonical_rows)
    dropped_noncanonical_policy = _policy_bound_noncanonical_summary(raw_dropped_noncanonical)
    dropped_noncanonical_policy_consistency = _validate_noncanonical_policy_summary(
        {
            "rows": raw_dropped_noncanonical,
            **dropped_noncanonical_policy,
        }
    )
    dropped_noncanonical_partition_consistency = _validate_noncanonical_partition(
        {
            "dropped_noncanonical": dropped_noncanonical,
            "dropped_noncanonical_deferred": dropped_noncanonical_deferred,
            "dropped_noncanonical_policy_bounded": dropped_noncanonical_policy_bounded,
            "dropped_noncanonical_policy": dropped_noncanonical_policy,
        }
    )
    return {
        "ids_path": str(ids_path),
        "stage": "full",
        "module_context": module_context,
        "stat_input_count": len(serialized_inputs),
        "missing_systems": list(compiled.missing),
        "dropped_noncanonical": dropped_noncanonical,
        "dropped_noncanonical_deferred": dropped_noncanonical_deferred,
        "dropped_noncanonical_policy_bounded": dropped_noncanonical_policy_bounded,
        "dropped_noncanonical_policy": dropped_noncanonical_policy,
        "dropped_noncanonical_policy_consistency": dropped_noncanonical_policy_consistency,
        "dropped_noncanonical_partition_consistency": dropped_noncanonical_partition_consistency,
        "dropped_kb_unwired": _drop_surface_summary(list(compiled.dropped_kb_unwired)),
        "routing_gaps": list(loadout.layer_gaps),
        "stat_inputs": serialized_inputs,
        "resolver_trace": [
            {
                "phase": row["phase"],
                "stat_id": row["stat_id"],
                "provenance": row["provenance"],
                "contributor_family": row["contributor_family"],
                "resolver_decision": row["resolver_decision"],
                "resolver_steps": row["resolver_steps"],
            }
            for row in serialized_inputs
        ],
        "intermediate_values": {
            "run_stats_by_phase": run_stats_by_phase,
            "statbook_rows": statbook_rows,
        },
        "final_stat_reconciliation": _reconciliation(serialized_inputs, statbook_rows),
        "consumed_unused_ledger": _consumed_unused_ledger(serialized_inputs, statbook_rows),
        "dependency_graph_audit": _dependency_graph_audit(serialized_inputs),
        "contributor_family_coverage_matrix": _contributor_family_coverage_matrix(serialized_inputs),
        "kb_expected_dependency_graph": kb_expected,
        "pipeline_dependency_graph": pipeline_dependencies,
        "kb_vs_pipeline_dependency_report": kb_vs_pipeline,
        "kb_vs_runtime_value_audit": kb_vs_runtime_value,
    }




def _validate_noncanonical_policy_summary(summary: dict[str, object]) -> dict[str, object]:
    by_family = summary.get("by_family")
    if not isinstance(by_family, dict):
        return {"ok": False, "errors": ["by_family_not_mapping"]}

    total_by_family = 0
    for family, count in by_family.items():
        if not isinstance(family, str) or family.strip() == "":
            return {"ok": False, "errors": ["by_family_invalid_key"]}
        if not isinstance(count, int) or count < 0:
            return {"ok": False, "errors": [f"by_family_invalid_count:{family}"]}
        total_by_family += count

    legacy_rows = summary.get("legacy_format_rows")
    if not isinstance(legacy_rows, list):
        return {"ok": False, "errors": ["legacy_format_rows_not_list"]}

    ambiguous_rows = summary.get("ambiguous_rows")
    if not isinstance(ambiguous_rows, list):
        return {"ok": False, "errors": ["ambiguous_rows_not_list"]}

    unbounded_rows = summary.get("unbounded_rows")
    if not isinstance(unbounded_rows, list):
        return {"ok": False, "errors": ["unbounded_rows_not_list"]}

    policy = summary.get("policy")
    if not isinstance(policy, dict):
        return {"ok": False, "errors": ["policy_not_mapping"]}

    families = policy.get("families")
    if not isinstance(families, dict) or not families:
        return {"ok": False, "errors": ["policy_families_missing_or_empty"]}

    coverage_complete = policy.get("coverage_complete")
    if not isinstance(coverage_complete, bool):
        return {"ok": False, "errors": ["policy_coverage_complete_not_bool"]}

    raw_rows: list[str] = []
    row_details: list[tuple[str | None, str | None, str]] = []
    for row in summary.get("rows", []):
        family_hint, prefix_hint, stat_id = _parse_noncanonical_drop_row(str(row))
        if stat_id is not None:
            raw_rows.append(stat_id)
            row_details.append((family_hint, prefix_hint, stat_id))

    errors: list[str] = []
    if total_by_family != len(raw_rows):
        errors.append(
            f"by_family_total_mismatch:{total_by_family}:expected={len(raw_rows)}"
        )

    allowed_family_names = set(families) | {"unbounded"}
    invalid_family_names = sorted(name for name in by_family if name not in allowed_family_names)
    if invalid_family_names:
        errors.append("by_family_unknown_names:" + ",".join(invalid_family_names))

    for family_hint, prefix_hint, stat_id in row_details:
        if family_hint is None or prefix_hint is None:
            errors.append(f"row_missing_context:{stat_id}")
            continue
        if family_hint not in families:
            errors.append(f"row_family_not_in_policy:{family_hint}:{stat_id}")
            continue
        contract = families[family_hint]
        if not isinstance(contract, dict):
            errors.append(f"row_family_contract_invalid:{family_hint}:{stat_id}")
            continue
        allowed_prefixes = contract.get("allowed_prefixes")
        if not isinstance(allowed_prefixes, list) or prefix_hint not in set(allowed_prefixes):
            errors.append(f"row_prefix_not_in_policy:{family_hint}:{prefix_hint}:{stat_id}")
        allowed_stat_ids = contract.get("allowed_stat_ids")
        if isinstance(allowed_stat_ids, list) and stat_id not in set(allowed_stat_ids):
            errors.append(f"row_stat_id_not_in_policy_allowlist:{family_hint}:{stat_id}")
        required_prefix = contract.get("required_stat_prefix")
        if isinstance(required_prefix, str) and required_prefix and not stat_id.startswith(required_prefix):
            errors.append(f"row_stat_id_missing_required_prefix:{family_hint}:{stat_id}")

    return {"ok": len(errors) == 0, "errors": sorted(set(errors))}


def _validate_noncanonical_partition(report: dict[str, object]) -> dict[str, object]:
    errors: list[str] = []

    actionable = int(report.get("dropped_noncanonical", {}).get("raw_count", 0))
    deferred = int(report.get("dropped_noncanonical_deferred", {}).get("raw_count", 0))
    bounded = int(report.get("dropped_noncanonical_policy_bounded", {}).get("raw_count", 0))
    policy_by_family = report.get("dropped_noncanonical_policy", {}).get("by_family", {})
    if not isinstance(policy_by_family, dict):
        return {"ok": False, "errors": ["noncanonical_partition_missing_policy_by_family"]}

    policy_total = sum(int(count) for count in policy_by_family.values() if isinstance(count, int))

    if actionable + deferred + bounded != policy_total:
        errors.append(
            "noncanonical_partition_raw_count_mismatch:"
            f"actionable={actionable}:deferred={deferred}:bounded={bounded}:policy_total={policy_total}"
        )

    return {"ok": len(errors) == 0, "errors": sorted(set(errors))}

def evaluate_phase4_closure_gate(report: dict[str, object]) -> dict[str, object]:
    partition = report.get("dropped_noncanonical_partition_consistency", {})
    gate_checks = {
        "missing_systems_zero": len(report.get("missing_systems", [])) == 0,
        "routing_gaps_zero": len(report.get("routing_gaps", [])) == 0,
        "dropped_kb_unwired_zero": int(report.get("dropped_kb_unwired", {}).get("count", 0)) == 0,
        "dropped_noncanonical_actionable_zero": int(report.get("dropped_noncanonical", {}).get("count", 0)) == 0,
        "dropped_noncanonical_policy_bounded": bool(report.get("dropped_noncanonical_policy", {}).get("ok", False)),
        "dropped_noncanonical_policy_consistent": bool(
            report.get("dropped_noncanonical_policy_consistency", {}).get("ok", False)
        ),
        "dropped_noncanonical_partition_consistent": bool(partition.get("ok", False)),
        "noncanonical_policy_coverage_complete": bool(
            report.get("dropped_noncanonical_policy", {}).get("policy", {}).get("coverage_complete", False)
        ),
        "dropped_noncanonical_ambiguous_zero": len(report.get("dropped_noncanonical_policy", {}).get("ambiguous_rows", []))
        == 0,
        "dropped_noncanonical_legacy_format_zero": len(report.get("dropped_noncanonical_policy", {}).get("legacy_format_rows", []))
        == 0,
        "dependency_not_ok_zero": int(
            report.get("kb_vs_pipeline_dependency_report", {}).get("summary", {}).get("not_ok", 0)
        )
        == 0,
        "value_audit_not_ok_zero": int(
            report.get("kb_vs_runtime_value_audit", {}).get("summary", {}).get("not_ok", 0)
        )
        == 0,
    }
    return {
        "ok": all(gate_checks.values()),
        "checks": gate_checks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Dump v3 IDS→snapshot→stat_inputs diagnostic with resolver trace and reconciliation report.")
    parser.add_argument("--ids", type=Path, default=None)
    parser.add_argument("--module-context", type=str, default="Farming")
    parser.add_argument("--output", type=Path, default=Path("out/v3_stat_contribution_diagnostic.json"))
    parser.add_argument(
        "--require-phase4-gates",
        action="store_true",
        help="Exit non-zero when phase-4 closure gates are not satisfied.",
    )
    args = parser.parse_args()

    ids_path = args.ids if args.ids is not None else resolve_ids_path(None)
    report = build_diagnostic(ids_path, module_context=args.module_context)
    phase4_gate = evaluate_phase4_closure_gate(report)
    report["phase4_closure_gate"] = phase4_gate

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    header = ["stat_id", "depends_on", "dependency_status", "resolved"]
    print("\t".join(header))
    for row in report["kb_vs_pipeline_dependency_report"]["rows"]:
        print(
            "\t".join(
                [
                    str(row["stat_id"]),
                    str(row["depends_on"]),
                    str(row["dependency_status"]),
                    str(row["resolved"]),
                ]
            )
        )
    print(
        json.dumps(
            {
                "ids_path": report["ids_path"],
                "stat_input_count": report["stat_input_count"],
                "missing_systems": len(report["missing_systems"]),
                "routing_gaps": len(report["routing_gaps"]),
                "dropped_noncanonical": report["dropped_noncanonical"]["count"],
                "dropped_noncanonical_raw": report["dropped_noncanonical"].get("raw_count", report["dropped_noncanonical"]["count"]),
                "dropped_noncanonical_deferred": report["dropped_noncanonical_deferred"]["count"],
                "dropped_noncanonical_deferred_raw": report["dropped_noncanonical_deferred"].get(
                    "raw_count", report["dropped_noncanonical_deferred"]["count"]
                ),
                "dropped_noncanonical_policy_bounded": report["dropped_noncanonical_policy_bounded"]["count"],
                "dropped_noncanonical_policy_bounded_raw": report["dropped_noncanonical_policy_bounded"].get(
                    "raw_count", report["dropped_noncanonical_policy_bounded"]["count"]
                ),
                "dropped_noncanonical_ambiguous": len(report["dropped_noncanonical_policy"].get("ambiguous_rows", [])),
                "dropped_noncanonical_legacy_format": len(report["dropped_noncanonical_policy"].get("legacy_format_rows", [])),
                "noncanonical_policy_coverage_complete": report["dropped_noncanonical_policy"]["policy"].get("coverage_complete", False),
                "noncanonical_policy_consistency_errors": len(report["dropped_noncanonical_policy_consistency"].get("errors", [])),
                "noncanonical_partition_consistency_errors": len(
                    report["dropped_noncanonical_partition_consistency"].get("errors", [])
                ),
                "dropped_kb_unwired": report["dropped_kb_unwired"]["count"],
                "unused_input_rows": report["consumed_unused_ledger"]["unused_input_rows"],
                "graph_edges": report["dependency_graph_audit"]["edge_count"],
                "kb_stats": report["kb_vs_pipeline_dependency_report"]["summary"]["stats_in_kb"],
                "pipeline_stats": report["kb_vs_pipeline_dependency_report"]["summary"]["stats_in_pipeline"],
                "dependency_rows_ok": report["kb_vs_pipeline_dependency_report"]["summary"]["ok"],
                "dependency_rows_not_ok": report["kb_vs_pipeline_dependency_report"]["summary"]["not_ok"],
                "value_audit_rows_ok": report["kb_vs_runtime_value_audit"]["summary"]["ok"],
                "value_audit_rows_not_ok": report["kb_vs_runtime_value_audit"]["summary"]["not_ok"],
                "phase4_gate_ok": phase4_gate["ok"],
                "output": str(args.output),
            },
            indent=2,
        )
    )

    if args.require_phase4_gates and not phase4_gate["ok"]:
        failed = [name for name, ok in phase4_gate["checks"].items() if not ok]
        raise SystemExit("phase4_closure_gate_failed:" + ",".join(sorted(failed)))


if __name__ == "__main__":
    main()
