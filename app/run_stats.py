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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


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
        default='max_progression_policy',
        choices=['none', 'max_progression_policy', 'runtime_timeline'],
        help='Explicit perk materialization mode for the run.',
    )
    parser.add_argument('--perk-state', type=str, default='auto', choices=['auto', 'on', 'off'])
    args = parser.parse_args()
    from app.pipeline import run_stats_pipeline
    return run_stats_pipeline(args)


if __name__ == '__main__':
    sys.exit(main())
