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
        '--run-tracker-csv',
        type=Path,
        default=None,
        help='Optional Tower Run Tracker CSV export used only for external observation diagnostics.',
    )
    parser.add_argument(
        '--approve-tracker-empirical-farming-cph',
        action='store_true',
        help=(
            'Explicitly approve tracker-derived farming CPH diagnostics as an empirical '
            'default candidate. This removes only the operator-approval blocker; it does '
            'not override missing formula validation blockers.'
        ),
    )
    parser.add_argument(
        '--approve-tracker-empirical-run-coin-duration-integrals',
        action='store_true',
        help=(
            'Explicitly approve the tracker-backed integrated coins-per-run and '
            'run-duration CPH identity when all component links are already closed. '
            'Closes only that final farming CPH blocker.'
        ),
    )
    parser.add_argument(
        '--approve-tracker-current-export-account-state-validation',
        action='store_true',
        help=(
            'Explicitly approve the supplied tracker export as the current account '
            'state validation basis. Closes only the multi-export/account-state '
            'validation blocker when tracker identity evidence is present.'
        ),
    )
    parser.add_argument(
        '--approve-tracker-empirical-kill-density-transform',
        action='store_true',
        help=(
            'Explicitly approve tracker-derived spawn-rate to kill-density transform '
            'as an empirical farming CPH input. Requires tracker evidence and closes '
            'only that formula link.'
        ),
    )
    parser.add_argument(
        '--approve-tracker-empirical-run-duration-projection',
        action='store_true',
        help=(
            'Explicitly approve tracker-backed run-duration projection as an empirical '
            'farming CPH input. Requires tracker duration evidence and closes only '
            'that formula link.'
        ),
    )
    parser.add_argument(
        '--approve-tracker-empirical-wave-skip-reward',
        action='store_true',
        help=(
            'Explicitly approve tracker-backed Wave Skip reward evidence as an '
            'empirical farming CPH input. Requires tracker reward fields and closes '
            'only that formula link.'
        ),
    )
    parser.add_argument(
        '--approve-tracker-wave-skip-intro-semantics',
        action='store_true',
        help=(
            'Explicitly approve the tracker wavesSkipped Intro Sprint semantics '
            'inference when the published candidate is close enough for review. '
            'Closes only that farming CPH validation blocker.'
        ),
    )
    parser.add_argument(
        '--approve-source-intro-sprint-coin-window',
        action='store_true',
        help=(
            'Explicitly approve source-backed Intro Sprint no-coin window handling '
            'as a farming CPH input. Requires the Intro Sprint runtime surface and '
            'closes only that formula link.'
        ),
    )
    parser.add_argument(
        '--approve-tracker-empirical-econ-window-overlap',
        action='store_true',
        help=(
            'Explicitly approve tracker-backed econ-window overlap evidence as an '
            'empirical farming CPH input. Requires tracker econ-source fields and '
            'closes only that formula link.'
        ),
    )
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
    clean_reference_group = parser.add_mutually_exclusive_group()
    clean_reference_group.set_defaults(boss_wave_align_clean_reference_rows=True)
    clean_reference_group.add_argument(
        '--boss-wave-align-clean-reference-rows',
        dest='boss_wave_align_clean_reference_rows',
        action='store_true',
        help='Align clean Boss Waves matrix rows to their active IDS milestone/Dissonant PB reference while preserving raw candidate calculations. This is the default product view.',
    )
    clean_reference_group.add_argument(
        '--boss-wave-compare-clean-reference-rows',
        dest='boss_wave_align_clean_reference_rows',
        action='store_false',
        help='Use comparison-only clean Boss Waves matrix rows instead of IDS/PB-aligned selected values.',
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
        '--boss-wave-pressure-factor',
        type=float,
        default=None,
        help='Optional matrix runtime input: explicit scenario pressure factor applied to boss HP and incoming boss-hit damage.',
    )
    parser.add_argument(
        '--approve-boss-wave-pressure-factor-review-default',
        action='store_true',
        help=(
            'Explicitly approve the matrix-published comparison pressure-factor '
            "review input as this run's Boss Waves pressure-factor approximation. "
            'Leaves default runs unchanged.'
        ),
    )
    parser.add_argument(
        '--approve-boss-wave-empirical-pressure-transform',
        action='store_true',
        help=(
            'Explicitly approve the empirical Boss Waves pressure-transform candidate '
            'as a review/default candidate. This removes only the operator-approval '
            'blocker; it does not apply a hidden pressure factor or close validation gaps.'
        ),
    )
    parser.add_argument(
        '--boss-wave-comparison-pressure-factor',
        type=float,
        default=None,
        help='Optional comparison overlay pressure factor. Leaves the default matrix at account truth and compares against this explicit boss HP + incoming-damage factor.',
    )
    parser.add_argument(
        '--boss-wave-comparison-fleet-terminal-max-wave',
        type=float,
        default=None,
        help='Optional comparison overlay closure: max wave before fleet non-boss pressure ends the run. Leaves the default matrix at account truth.',
    )
    parser.add_argument(
        '--boss-wave-comparison-elite-terminal-max-wave',
        type=float,
        default=None,
        help='Optional comparison overlay closure: max wave before elite non-boss pressure ends the run. Leaves the default matrix at account truth.',
    )
    parser.add_argument(
        '--boss-wave-comparison-protector-terminal-max-wave',
        type=float,
        default=None,
        help='Optional comparison overlay closure: max wave before protector non-boss pressure ends the run. Leaves the default matrix at account truth.',
    )
    parser.add_argument(
        '--boss-wave-comparison-armored-terminal-max-wave',
        type=float,
        default=None,
        help='Optional comparison overlay closure: max wave before armored non-boss pressure ends the run. Leaves the default matrix at account truth.',
    )
    parser.add_argument(
        '--boss-wave-comparison-boss-terminal-max-wave',
        type=float,
        default=None,
        help='Optional comparison overlay closure: max wave before boss-specific deferred pressure ends the run. Leaves the default matrix at account truth.',
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
        '--boss-wave-boss-terminal-max-wave',
        type=float,
        default=None,
        help='Optional matrix runtime closure: max wave before boss-specific deferred pressure ends the run.',
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
