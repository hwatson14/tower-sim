from __future__ import annotations

from io import StringIO
from pathlib import Path

import pandas as pd
import streamlit as st

from input.loader import load_inputs
from input.runtime_state import build_runtime_state
from input.state_types import ScenarioRuntimeInputs
from simulators.contracts import PerkState
from simulators.run_executor import (
    RunToMaxConfig,
    build_boss_wave_table,
    build_start_of_run_state,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IDS = ROOT / 'input' / 'imports' / 'ids.csv'
DEFAULT_MANUAL_INPUTS = ROOT / 'input' / 'manual_inputs.yaml'


@st.cache_data(show_spinner=False)
def _build_boss_wave_frame(
    *,
    ids_path: str,
    manual_inputs_path: str,
    preset_name: str,
    tier_number: int,
    end_wave: int,
    boss_wave_step: int,
    stop_on_failure: bool,
    orb_boss_hit_pct: float,
    orb_boss_hits_per_second: float,
    electron_hits_per_second: float,
    boss_contact_time_seconds: float,
    effective_damage_reduction_pct: float,
    incoming_damage_multiplier: float,
) -> tuple[pd.DataFrame, dict[str, object]]:
    bundle = load_inputs(
        ids_path=Path(ids_path),
        manual_inputs_path=Path(manual_inputs_path),
    )
    account_state = build_runtime_state(
        bundle.ids_raw,
        loadout_config=bundle.loadout_config,
        perk_config=bundle.perk_config,
    )
    initial_state = build_start_of_run_state(
        account_state,
        preset_name=preset_name,
        perk_state=PerkState(wave=0, counts={}, dirty=False),
    )
    config = RunToMaxConfig(
        execution_mode='table_sweep',
        preset_name=preset_name,
        tier_column=f'Tier {int(tier_number)}',
        start_wave=max(1, int(boss_wave_step)),
        end_wave=int(end_wave),
        boss_wave_step=int(boss_wave_step),
        state_mode='start_of_run',
        scenario_runtime_inputs=ScenarioRuntimeInputs.from_mapping(
            {
                'orb_boss_hit_pct': orb_boss_hit_pct,
                'orb_boss_hits_per_second': orb_boss_hits_per_second,
                'electron_hits_per_second': electron_hits_per_second,
                'boss_contact_time_seconds': boss_contact_time_seconds,
                'effective_damage_reduction_pct': effective_damage_reduction_pct,
                'incoming_damage_multiplier': incoming_damage_multiplier,
            }
        ),
    )
    rows = build_boss_wave_table(
        account_state=account_state,
        initial_projected_state=initial_state,
        config=config,
        stop_on_failure=bool(stop_on_failure),
    )
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame['changed_workshop_tracks_last_step'] = frame['changed_workshop_tracks_last_step'].fillna('')
    surviving_rows = frame[frame['survives_boss'] == True] if not frame.empty else frame
    diagnostics = {
        'preset_name': preset_name,
        'tier_column': config.tier_column,
        'boss_wave_step': config.boss_wave_step,
        'row_count': int(len(frame)),
        'max_surviving_wave': int(surviving_rows['display_wave'].max()) if not surviving_rows.empty else 0,
        'state_mode': config.state_mode,
        'checkpoint_mode': 'boss_wave_only',
    }
    return frame, diagnostics


def _to_csv_bytes(frame: pd.DataFrame) -> bytes:
    buffer = StringIO()
    frame.to_csv(buffer, index=False)
    return buffer.getvalue().encode('utf-8')


def main() -> None:
    st.set_page_config(page_title='TowerSim Inspector', layout='wide')
    st.title('TowerSim Inspector')
    st.caption('Boss-wave table from the live table-sweep simulator path.')

    st.sidebar.header('Boss Wave Controls')
    ids_path = st.sidebar.text_input('IDS path', value=str(DEFAULT_IDS))
    manual_inputs_path = st.sidebar.text_input('Manual inputs', value=str(DEFAULT_MANUAL_INPUTS))
    preset_name = st.sidebar.selectbox('Loadout preset', options=['Farming', 'Tourney', 'Milestone'], index=0)
    tier_number = st.sidebar.number_input('Tier', min_value=1, max_value=18, value=14, step=1)
    end_wave = st.sidebar.number_input('End wave', min_value=10, max_value=100000, value=500, step=10)
    boss_wave_step = st.sidebar.number_input('Boss wave step', min_value=1, max_value=1000, value=10, step=1)
    stop_on_failure = st.sidebar.checkbox('Stop on first failed boss', value=False)

    st.sidebar.subheader('Runtime assumptions')
    orb_boss_hit_pct = st.sidebar.number_input('Orb boss hit %', min_value=0.0, max_value=100.0, value=2.5, step=0.1)
    orb_boss_hits_per_second = st.sidebar.number_input('Orb boss hits / sec', min_value=0.1, max_value=100.0, value=5.0, step=0.1)
    electron_hits_per_second = st.sidebar.number_input('Electron hits / sec', min_value=0.1, max_value=100.0, value=5.0, step=0.1)
    boss_contact_time_seconds = st.sidebar.number_input('Boss contact time (s)', min_value=0.0, max_value=120.0, value=1.0, step=0.1)
    effective_damage_reduction_pct = st.sidebar.number_input('Effective DR %', min_value=0.0, max_value=100.0, value=90.0, step=0.1)
    incoming_damage_multiplier = st.sidebar.number_input('Incoming damage multiplier', min_value=0.0, max_value=100.0, value=1.0, step=0.1)

    frame, diagnostics = _build_boss_wave_frame(
        ids_path=ids_path,
        manual_inputs_path=manual_inputs_path,
        preset_name=preset_name,
        tier_number=int(tier_number),
        end_wave=int(end_wave),
        boss_wave_step=int(boss_wave_step),
        stop_on_failure=bool(stop_on_failure),
        orb_boss_hit_pct=float(orb_boss_hit_pct),
        orb_boss_hits_per_second=float(orb_boss_hits_per_second),
        electron_hits_per_second=float(electron_hits_per_second),
        boss_contact_time_seconds=float(boss_contact_time_seconds),
        effective_damage_reduction_pct=float(effective_damage_reduction_pct),
        incoming_damage_multiplier=float(incoming_damage_multiplier),
    )

    summary_tab, boss_table_tab = st.tabs(['Summary', 'Boss Waves'])

    with summary_tab:
        metrics = st.columns(4)
        metrics[0].metric('Rows', diagnostics['row_count'])
        metrics[1].metric('Max surviving wave', diagnostics['max_surviving_wave'])
        metrics[2].metric('Tier', diagnostics['tier_column'])
        metrics[3].metric('Preset', diagnostics['preset_name'])
        st.json(diagnostics)
        st.caption(
            'Rows are stepped only at boss-wave checkpoints. Free upgrades and enemy level skips are accumulated '
            'across the intervening waves using the interval-start resolved values.'
        )

    with boss_table_tab:
        st.dataframe(frame, use_container_width=True, hide_index=True)
        st.download_button(
            'Download CSV',
            data=_to_csv_bytes(frame),
            file_name=f'{preset_name.lower()}_tier_{int(tier_number)}_boss_waves.csv',
            mime='text/csv',
            use_container_width=True,
        )


if __name__ == '__main__':
    main()
