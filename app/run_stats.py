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
        '--runtime-state-overlay',
        type=str,
        default=None,
        help='Optional named manual_inputs.yaml:runtime_state_overlays entry to apply for this calculation only.',
    )
    parser.add_argument(
        '--perk-mode',
        type=str,
        default='max_progression_policy',
        choices=['none', 'max_progression_policy', 'runtime_timeline'],
        help='Explicit perk materialization mode for the run.',
    )
    parser.add_argument('--perk-state', type=str, default='auto', choices=['auto', 'on', 'off'])
    parser.add_argument(
        '--perk-policy-preset',
        type=str,
        default=None,
        help='Optional named perk policy preset from manual_inputs.yaml:perk_policy.policy_presets.',
    )
    parser.add_argument(
        '--tier',
        type=int,
        default=None,
        help='Optional farming tier override for tier-scoped stat surfaces such as Dissonance.',
    )
    parser.add_argument(
        '--dissonance-run-category',
        type=str,
        default=None,
        help='Optional Dissonant Run scenario category for stat calculations: none, attack, defense, utility, ultimate_weapons.',
    )
    parser.add_argument(
        '--include-boss-wave-milestone-matrix',
        action='store_true',
        help='Also publish the optional all-tier Boss Waves milestone/Dissonant Run best-loadout matrix.',
    )
    parser.add_argument(
        '--boss-wave-contact-time-seconds',
        type=float,
        default=None,
        help='Optional matrix runtime override: boss spawn-to-wall contact time in seconds. Omit to derive from 2s base plus CF/EN/Slow Aura effects.',
    )
    parser.add_argument(
        '--boss-wave-orb-boss-total-damage-pct',
        type=float,
        default=None,
        help='Optional matrix runtime input: total orb damage to boss percent.',
    )
    parser.add_argument(
        '--boss-wave-flame-bot-boss-hit-chance-pct',
        type=float,
        default=None,
        help='Optional matrix runtime override: average chance that Flame Bot DR applies to boss hits. Omit to use the static Boss Waves path-overlap estimate.',
    )
    parser.add_argument(
        '--boss-wave-flame-bot-damage-reduction-pct',
        type=float,
        default=None,
        help='Optional matrix runtime override: Flame Bot damage reduction percent.',
    )
    parser.add_argument(
        '--boss-wave-flame-bot-duration-seconds',
        type=float,
        default=None,
        help='Optional matrix runtime input: Flame Bot active duration in seconds.',
    )
    parser.add_argument(
        '--boss-wave-flame-bot-cooldown-seconds',
        type=float,
        default=None,
        help='Optional matrix runtime input: Flame Bot cooldown in seconds.',
    )
    parser.add_argument(
        '--boss-wave-fleet-terminal-max-wave',
        type=float,
        default=None,
        help='Optional matrix runtime closure: max wave before fleet non-boss pressure ends the run.',
    )
    parser.add_argument(
        '--boss-wave-elite-terminal-max-wave',
        type=float,
        default=None,
        help='Optional matrix runtime closure: max wave before elite non-boss pressure ends the run.',
    )
    parser.add_argument(
        '--boss-wave-protector-terminal-max-wave',
        type=float,
        default=None,
        help='Optional matrix runtime closure: max wave before protector non-boss pressure ends the run.',
    )
    parser.add_argument(
        '--boss-wave-armored-terminal-max-wave',
        type=float,
        default=None,
        help='Optional matrix runtime closure: max wave before armored non-boss pressure ends the run.',
    )
    parser.add_argument(
        '--boss-wave-bridge-target-share',
        type=float,
        default=0.0,
        help='Optional comparison overlay factor: share of QE eDamage directed at the boss.',
    )
    parser.add_argument(
        '--boss-wave-bridge-cadence-uptime',
        type=float,
        default=0.0,
        help='Optional comparison overlay factor: cadence/uptime of QE eDamage during boss contact.',
    )
    parser.add_argument(
        '--boss-wave-bridge-reliability',
        type=float,
        default=0.0,
        help='Optional comparison overlay factor: reliability/shock component of boss-applicable eDamage.',
    )
    parser.add_argument(
        '--boss-wave-bridge-semantic-normalizer',
        type=float,
        default=0.0,
        help='Optional comparison overlay factor: semantic/unit normalizer from QE eDamage to boss DPS.',
    )
    args = parser.parse_args()
    from app.pipeline import run_stats_pipeline
    return run_stats_pipeline(args)


if __name__ == '__main__':
    sys.exit(main())
