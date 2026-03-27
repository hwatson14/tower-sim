"""
app/run_stats.py -- Thin CLI entrypoint.

Owns: argument parsing, calling pipeline.run_pipeline(), exit code.
Must not own: domain logic.

T6: extracted thin CLI shell from run_stats.py.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description='Tower sim stat calculator.')
    parser.add_argument('--ids', type=Path, default=ROOT / 'input' / 'imports' / 'ids.csv')
    parser.add_argument('--out', '--output-dir', dest='out', type=Path, default=ROOT / 'out')
    parser.add_argument('--preset', type=str, default='Farming')
    parser.add_argument('--state-mode', type=str, default='max_progression')
    parser.add_argument('--loadout', type=str, default=str(ROOT / 'input' / 'loadout.json'))
    parser.add_argument('--perks', type=str, default=str(ROOT / 'input' / 'perks.json'))
    parser.add_argument('--perk-state', type=str, default='auto', choices=['auto', 'on', 'off'])
    args = parser.parse_args()
    from app.pipeline import run_pipeline
    return run_pipeline(args)


if __name__ == '__main__':
    sys.exit(main())
