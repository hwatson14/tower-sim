from __future__ import annotations

import csv
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compilers.account_state_compiler import compile_account_state
from engine.progression_recalc_bridge import ProgressionRecalcBridge, ProgressionRecalcRequest
from parsers.ids_parser import parse_ids


def _build_state():
    ids_raw = parse_ids(ROOT / 'input' / '_IDS.csv')
    return compile_account_state(ids_raw, default_preset='Farming')


def _make_request(state, workshop_levels_current: Dict[str, int], *, recompute_mode: str, runtime_target_display_wave: int | None = None, cache_bundle: Dict[str, Any] | None = None):
    kwargs: Dict[str, Any] = dict(
        account_state=state,
        preset_name='Farming',
        workshop_levels_current=workshop_levels_current,
        recompute_mode=recompute_mode,
        runtime_target_display_wave=runtime_target_display_wave,
    )
    if cache_bundle is not None:
        kwargs.update(
            cached_reference_statbook=cache_bundle['statbook'],
            cached_reference_workshop_levels_current=cache_bundle['workshop_levels_current'],
            cached_reference_fingerprint=cache_bundle['fingerprint'],
        )
    return ProgressionRecalcRequest(**kwargs)


def _time_call(bridge: ProgressionRecalcBridge, request: ProgressionRecalcRequest) -> Tuple[float, Dict[str, float]]:
    start = time.perf_counter()
    result = bridge.recompute(request)
    elapsed = time.perf_counter() - start
    phase = ((result.incremental_diagnostics or {}).get('phase_timing_ms') or {})
    return elapsed, {str(k): float(v) for k, v in phase.items()}


def _summarise(samples: List[float]) -> Dict[str, float]:
    return {
        'runs': len(samples),
        'mean_ms': round(statistics.mean(samples) * 1000.0, 3),
        'median_ms': round(statistics.median(samples) * 1000.0, 3),
        'min_ms': round(min(samples) * 1000.0, 3),
        'max_ms': round(max(samples) * 1000.0, 3),
    }


def _summarise_phase_timings(samples: List[Dict[str, float]]) -> Dict[str, float]:
    keys = sorted({key for sample in samples for key in sample.keys()})
    out: Dict[str, float] = {}
    for key in keys:
        vals = [sample[key] for sample in samples if key in sample]
        if vals:
            out[key] = round(statistics.mean(vals), 3)
    return out


def run_benchmark(runs: int = 40, warmup: int = 5) -> Dict[str, Any]:
    state = _build_state()
    bridge = ProgressionRecalcBridge()

    health_level = state.workshop['Health'].preset_levels['Farming']
    eals_level = state.workshop['Enemy Attack Level Skip'].preset_levels['Farming']
    free_attack_level = state.workshop['Free Attack Upgrade'].preset_levels['Farming']

    base_result = bridge.recompute(
        _make_request(
            state,
            {'Health': health_level},
            recompute_mode='full_safe',
        )
    )
    cache_bundle = {
        'statbook': base_result.statbook,
        'workshop_levels_current': {'Health': health_level},
        'fingerprint': (base_result.incremental_diagnostics or {}).get('cache_fingerprint'),
    }
    if cache_bundle['fingerprint'] is None:
        fp_result = bridge.recompute(
            _make_request(
                state,
                {'Health': health_level},
                recompute_mode='incremental_publish_guarded',
            )
        )
        cache_bundle['statbook'] = fp_result.statbook
        cache_bundle['fingerprint'] = fp_result.incremental_diagnostics['cache_fingerprint']

    scenarios = [
        {
            'name': 'health_canonical',
            'workshop_levels_current': {'Health': health_level + 1},
            'runtime_target_display_wave': None,
        },
        {
            'name': 'free_attack_canonical',
            'workshop_levels_current': {'Free Attack Upgrade': min(99, free_attack_level + 1)},
            'runtime_target_display_wave': None,
        },
        {
            'name': 'eals_runtime',
            'workshop_levels_current': {'Enemy Attack Level Skip': max(0, eals_level - 1)},
            'runtime_target_display_wave': 1000,
        },
    ]

    modes = [
        'full_safe',
        'incremental_targeted_probe_guarded',
        'incremental_cached_publish_guarded',
    ]

    rows: List[Dict[str, Any]] = []
    phase_rows: List[Dict[str, Any]] = []
    for scenario in scenarios:
        scenario_cache = {
            'statbook': base_result.statbook,
            'workshop_levels_current': scenario['workshop_levels_current'],
            'fingerprint': cache_bundle['fingerprint'],
        }
        for mode in modes:
            req = _make_request(
                state,
                scenario['workshop_levels_current'],
                recompute_mode=mode,
                runtime_target_display_wave=scenario['runtime_target_display_wave'],
                cache_bundle=scenario_cache if mode == 'incremental_cached_publish_guarded' else None,
            )
            for _ in range(warmup):
                bridge.recompute(req)
            elapsed_samples: List[float] = []
            phase_samples: List[Dict[str, float]] = []
            for _ in range(runs):
                elapsed, phase = _time_call(bridge, req)
                elapsed_samples.append(elapsed)
                phase_samples.append(phase)
            summary = _summarise(elapsed_samples)
            summary.update({'scenario': scenario['name'], 'mode': mode})
            rows.append(summary)
            phase_summary = _summarise_phase_timings(phase_samples)
            for phase_name, mean_ms in phase_summary.items():
                phase_rows.append({
                    'scenario': scenario['name'],
                    'mode': mode,
                    'phase': phase_name,
                    'mean_ms': mean_ms,
                })

    by_scenario = {}
    for row in rows:
        by_scenario.setdefault(row['scenario'], {})[row['mode']] = row
    comparisons = []
    for scenario, scenario_rows in by_scenario.items():
        full_mean = scenario_rows['full_safe']['mean_ms']
        for mode, row in scenario_rows.items():
            if mode == 'full_safe':
                continue
            comparisons.append({
                'scenario': scenario,
                'mode': mode,
                'mean_speedup_vs_full_safe_x': round(full_mean / row['mean_ms'], 3) if row['mean_ms'] else None,
                'mean_ms_saved_vs_full_safe': round(full_mean - row['mean_ms'], 3),
            })

    phase_by_scenario_mode: Dict[str, Dict[str, Dict[str, float]]] = {}
    for row in phase_rows:
        phase_by_scenario_mode.setdefault(row['scenario'], {}).setdefault(row['mode'], {})[row['phase']] = row['mean_ms']
    attribution = []
    for scenario, modes_map in phase_by_scenario_mode.items():
        full = modes_map.get('full_safe', {})
        for mode in ('incremental_targeted_probe_guarded', 'incremental_cached_publish_guarded'):
            current = modes_map.get(mode, {})
            all_keys = sorted(set(full.keys()) | set(current.keys()))
            for phase_name in all_keys:
                attribution.append({
                    'scenario': scenario,
                    'mode': mode,
                    'phase': phase_name,
                    'full_safe_mean_ms': round(full.get(phase_name, 0.0), 3),
                    'mode_mean_ms': round(current.get(phase_name, 0.0), 3),
                    'delta_ms_vs_full_safe': round(current.get(phase_name, 0.0) - full.get(phase_name, 0.0), 3),
                })

    return {
        'runs': runs,
        'warmup': warmup,
        'rows': rows,
        'comparisons': comparisons,
        'phase_rows': phase_rows,
        'phase_attribution_vs_full_safe': attribution,
    }


if __name__ == '__main__':
    out = run_benchmark()
    out_dir = ROOT / 'out' / 'benchmarks'
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / 'incremental_closed_subset_benchmark.json'
    csv_path = out_dir / 'incremental_closed_subset_benchmark.csv'
    phase_csv_path = out_dir / 'incremental_closed_subset_benchmark_phase_rows.csv'
    attribution_csv_path = out_dir / 'incremental_closed_subset_benchmark_phase_attribution.csv'
    json_path.write_text(json.dumps(out, indent=2), encoding='utf-8')
    with csv_path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['scenario', 'mode', 'runs', 'mean_ms', 'median_ms', 'min_ms', 'max_ms'])
        writer.writeheader()
        writer.writerows(out['rows'])
    with phase_csv_path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['scenario', 'mode', 'phase', 'mean_ms'])
        writer.writeheader()
        writer.writerows(out['phase_rows'])
    with attribution_csv_path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['scenario', 'mode', 'phase', 'full_safe_mean_ms', 'mode_mean_ms', 'delta_ms_vs_full_safe'])
        writer.writeheader()
        writer.writerows(out['phase_attribution_vs_full_safe'])
    print(json.dumps(out, indent=2))
    print(f'Wrote {json_path}')
    print(f'Wrote {csv_path}')
    print(f'Wrote {phase_csv_path}')
    print(f'Wrote {attribution_csv_path}')
