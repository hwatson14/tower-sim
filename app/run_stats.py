"""
app/run_stats.py -- Thin CLI entrypoint.

Owns: argument parsing, calling pipeline.run_stats_pipeline(), exit code.
Must not own: domain logic.

T6: extracted thin CLI shell from run_stats.py.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description='Tower sim dual-state stats calculator.')
    parser.add_argument('--ids', type=Path, default=ROOT / 'input' / 'imports' / 'ids.csv')
    parser.add_argument('--out', '--output-dir', dest='out', type=Path, default=ROOT / 'out')
    # Single manual input surface: all loadout and perk config come from manual_inputs.yaml.
    # --manual-inputs allows pointing at a different yaml file (e.g., for testing).
    parser.add_argument('--manual-inputs', type=Path, default=None,
                        help='Optional path to manual_inputs.yaml override (default: input/manual_inputs.yaml)')
    parser.add_argument(
        '--perk-mode',
        type=str,
        default='none',
        choices=['none', 'max_progression_policy', 'runtime_timeline'],
        help='Explicit perk materialization mode for the run.',
    )
    parser.add_argument('--perk-state', type=str, default='auto', choices=['auto', 'on', 'off'])
    parser.add_argument(
        '--watch',
        action='store_true',
        help='Keep the run_stats session warm in-process and rerun on demand until quit.',
    )
    parser.add_argument(
        '--server',
        action='store_true',
        help='Start a local warm run_stats server on localhost.',
    )
    parser.add_argument(
        '--use-server',
        action='store_true',
        help='Send this run_stats request to a local warm server instead of running in-process.',
    )
    parser.add_argument('--host', type=str, default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    if args.server:
        from app.pipeline import run_stats_server
        return run_stats_server(args)
    if args.use_server:
        from app.pipeline import run_stats_client
        return run_stats_client(args)
    if args.watch:
        from app.pipeline import run_stats_watch_loop
        return run_stats_watch_loop(args)
    from app.pipeline import run_stats_client, run_stats_local_server_is_healthy, run_stats_pipeline
    if run_stats_local_server_is_healthy(args):
        return run_stats_client(args)
    return run_stats_pipeline(args)


if __name__ == '__main__':
    sys.exit(main())
