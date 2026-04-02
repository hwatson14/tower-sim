from __future__ import annotations

import html

DISPLAY_SUFFIXES = [
    (1e24, 'S'),
    (1e21, 's'),
    (1e18, 'Q'),
    (1e15, 'q'),
    (1e12, 'T'),
    (1e9, 'B'),
    (1e6, 'M'),
    (1e3, 'k'),
]


def _trim_decimal_string(text: str) -> str:
    return text.rstrip('0').rstrip('.') if '.' in text else text


def _format_display_number(value) -> str | None:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    sign = '-' if v < 0 else ''
    av = abs(v)
    for threshold, suffix in DISPLAY_SUFFIXES:
        if av >= threshold:
            scaled = av / threshold
            decimals = 2 if scaled < 10 else (1 if scaled < 100 else 0)
            txt = _trim_decimal_string(f"{scaled:.{decimals}f}")
            return f"{sign}{txt}{suffix}"
    if av == int(av):
        return f"{int(v)}"
    return _trim_decimal_string(f"{v:.3f}")



def _format_display_value(value, value_type: str | None) -> str | None:
    if value is None:
        return None
    vt = value_type or ''
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if vt in {'pct', 'percent_display'}:
        num = _format_display_number(value)
        return f"{num}%" if num is not None else str(value)
    if vt in {'multiplier', 'multiplier_display'}:
        num = _format_display_number(value)
        return f"x{num}" if num is not None else f"x{value}"
    return _format_display_number(value) or str(value)


def _contributor_display_type(contributor: dict) -> str | None:
    preferred = contributor.get('input_value_type') or contributor.get('value_type')
    preferred_text = str(preferred or '').strip().lower()
    if preferred_text not in {'', 'scalar', 'resolved_value'}:
        return str(preferred)
    contributor_id = str(contributor.get('contributor_id') or '').lower()
    if '__pct' in contributor_id or 'percent' in contributor_id:
        return 'pct'
    if '__multiplier' in contributor_id or 'multiplier' in contributor_id:
        return 'multiplier'
    return str(preferred) if preferred is not None else None


def annotate_display_fields(statbook_dict: dict) -> None:
    for row in statbook_dict.get('rows', {}).values():
        row['display_value'] = _format_display_value(row.get('final_value'), row.get('value_type'))
        for contributor in row.get('contributors', []):
            contributor_display_type = _contributor_display_type(contributor)
            contributor['display_value'] = _format_display_value(contributor.get('value'), contributor_display_type)



def annotate_compare_display_fields(ep_compare: dict) -> None:
    for payload in ep_compare.values():
        package_value = payload.get('package_value')
        package_value_type = payload.get('package_value_type')
        payload['package_value_display'] = _format_display_value(package_value, package_value_type)

        ep_type = payload.get('ep_value_type')
        ep_value = payload.get('ep_value_parsed')
        compare_notes = set(payload.get('compare_notes') or [])
        if ep_value is None:
            payload['ep_value_display'] = None
        elif 'ep_decimal_fraction_scaled_to_percent_points' in compare_notes:
            payload['ep_value_display'] = _format_display_value(ep_value * 100.0, 'pct')
        elif ep_type in {'multiplier_display'}:
            payload['ep_value_display'] = _format_display_value(ep_value, 'multiplier_display')
        elif ep_type in {'percent_display', 'pct'}:
            payload['ep_value_display'] = _format_display_value(ep_value, 'pct')
        else:
            payload['ep_value_display'] = _format_display_number(ep_value)

        delta = payload.get('delta')
        if delta is None:
            payload['delta_display'] = None
        elif package_value_type in {'pct', 'percent_display'}:
            payload['delta_display'] = _format_display_value(delta, 'pct')
        elif package_value_type in {'multiplier', 'multiplier_display'}:
            payload['delta_display'] = _format_display_value(delta, 'multiplier_display')
        else:
            payload['delta_display'] = _format_display_number(delta)

        rel = payload.get('relative_delta_pct')
        payload['relative_delta_display'] = (f"{_format_display_number(rel)}%" if rel is not None else None)


MODULE_CARD_CSS = """
<style>
.module-card{background:linear-gradient(180deg,#1a2230 0%,#121924 100%);border:1px solid rgba(255,255,255,0.12);border-radius:18px;padding:0;overflow:hidden;box-shadow:0 8px 26px rgba(0,0,0,0.28);margin:0 0 14px 0;}
.module-rolebar{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:8px 12px;font-size:12px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;background:rgba(255,255,255,0.04);border-bottom:1px solid rgba(255,255,255,0.08);}
.module-rolebar.primary{background:linear-gradient(90deg,rgba(64,186,255,0.22),rgba(64,186,255,0.08));color:#9edcff;}
.module-rolebar.assist{background:linear-gradient(90deg,rgba(176,103,255,0.22),rgba(176,103,255,0.08));color:#d2b3ff;}
.module-role-detail{font-size:11px;font-weight:600;letter-spacing:0;text-transform:none;opacity:.95;text-align:right;}
.module-card-body{padding:14px 14px 12px 14px;}
.module-head{display:grid;grid-template-columns:72px 1fr;gap:12px;align-items:center;margin-bottom:10px;}
.module-icon-shell{border:1px solid rgba(255,255,255,0.14);border-radius:16px;padding:6px;background:rgba(255,255,255,0.03);}
.module-icon{height:58px;border:1px solid rgba(255,255,255,0.18);border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:800;letter-spacing:.08em;color:#c9d6e5;background:linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.02));text-transform:uppercase;text-align:center;}
.module-rarity{font-size:11px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:#c7d2df;margin-bottom:2px;}
.module-name{font-size:20px;font-weight:800;line-height:1.05;color:#ffffff;margin-bottom:3px;}
.module-level{font-size:12px;color:#b5c0cc;}
.module-main{display:flex;justify-content:space-between;align-items:flex-end;gap:12px;padding:12px 0 10px 0;border-top:1px solid rgba(255,255,255,0.06);border-bottom:1px solid rgba(255,255,255,0.06);margin-bottom:10px;}
.module-main-value{font-size:28px;font-weight:900;color:#ffffff;line-height:1;}
.module-main-label{font-size:12px;color:#b5c0cc;text-align:right;}
.module-unique{background:rgba(255,255,255,0.035);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:10px 11px;margin-bottom:10px;font-size:12px;line-height:1.35;color:#d7dee6;}
.module-unique-value{color:#87d7ff;font-weight:800;}
.module-effects{display:flex;flex-direction:column;gap:7px;}
.module-effect{display:grid;grid-template-columns:auto auto 1fr;gap:8px;align-items:center;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.05);border-radius:11px;padding:7px 9px;}
.module-effect.state-locked{opacity:.72;background:rgba(255,255,255,0.02);}
.module-effect.state-empty{opacity:.86;}
.module-effect-value{font-weight:800;color:#ffffff;font-size:12px;min-width:56px;}
.module-effect-label{font-size:12px;color:#d7dee6;}
.module-chip{display:inline-flex;align-items:center;justify-content:center;padding:2px 7px;border-radius:999px;border:1px solid rgba(255,255,255,0.16);font-size:10px;font-weight:800;letter-spacing:.05em;text-transform:uppercase;color:#d7dee6;}
.rarity-common{border-color:#9da3ae;color:#c9ced6;}
.rarity-rare{border-color:#63b3ff;color:#8fcbff;}
.rarity-epic{border-color:#c084fc;color:#d8b4fe;}
.rarity-legendary{border-color:#f59e0b;color:#fcd34d;}
.rarity-mythic{border-color:#ef4444;color:#fca5a5;}
.rarity-ancestral{border-color:#4ade80;color:#86efac;}
.text-common{color:#c9ced6;}
.text-rare{color:#8fcbff;}
.text-epic{color:#d8b4fe;}
.text-legendary{color:#fcd34d;}
.text-mythic{color:#fca5a5;}
.text-ancestral{color:#86efac;}
</style>
"""


def _module_card_icon_text(slot_type: str) -> str:
    mapping = {
        'cannon': 'Cannon',
        'armor': 'Armor',
        'generator': 'Generator',
        'core': 'Core',
    }
    return mapping.get(str(slot_type or '').strip().lower(), str(slot_type or '').strip().title())


def _module_unique_html(unique_payload: dict | None) -> str:
    if not isinstance(unique_payload, dict):
        return ''
    prefix = html.escape(str(unique_payload.get('prefix_text') or ''))
    value = html.escape(str(unique_payload.get('value_text') or ''))
    suffix = html.escape(str(unique_payload.get('suffix_text') or ''))
    if not (prefix or value or suffix):
        return ''
    value_html = f'<span class="module-unique-value">{value}</span>' if value else ''
    return f'<div class="module-unique">{prefix}{value_html}{suffix}</div>'


def _module_effect_html(effect: dict) -> str:
    state = html.escape(str(effect.get('state') or ''))
    rarity_key = str(effect.get('rarity_key') or '').strip().lower()
    rarity_text = html.escape(str(effect.get('rarity_text') or ''))
    value_text = html.escape(str(effect.get('value_text') or ''))
    label_text = html.escape(str(effect.get('label_text') or ''))
    chip = '&nbsp;'
    if rarity_text:
        chip = f'<span class="module-chip rarity-{rarity_key}">{rarity_text}</span>'
    value_html = f'<div class="module-effect-value">{value_text}</div>' if value_text else '<div class="module-effect-value"></div>'
    label_class = f'module-effect-label text-{rarity_key}' if rarity_key else 'module-effect-label'
    return f'<div class="module-effect state-{state}">{chip}{value_html}<div class="{label_class}">{label_text}</div></div>'


def render_module_card_html(payload: dict) -> str:
    role = str(payload.get('role') or '').strip().lower()
    rolebar_class = 'primary' if role == 'primary' else 'assist'
    role_label = html.escape(str(payload.get('role_bar_label_text') or role.title()))
    role_detail = html.escape(str(payload.get('role_bar_detail_text') or ''))
    rarity_text = html.escape(str(payload.get('rarity_text') or ''))
    name = html.escape(str(payload.get('module_name') or ''))
    level_text = html.escape(str(payload.get('level_text') or ''))
    main_value = html.escape(str(payload.get('main_value_text') or ''))
    main_label = html.escape(str(payload.get('main_label_text') or ''))
    icon_text = html.escape(_module_card_icon_text(str(payload.get('slot_type') or '')))
    unique_html = _module_unique_html(payload.get('unique_text'))
    effects = ''.join(_module_effect_html(effect) for effect in (payload.get('effect_slots') or []))
    role_detail_html = f'<div class="module-role-detail">{role_detail}</div>' if role_detail else '<div class="module-role-detail"></div>'
    return (
        '<div class="module-card">'
        f'<div class="module-rolebar {rolebar_class}"><div>{role_label}</div>{role_detail_html}</div>'
        '<div class="module-card-body">'
        '<div class="module-head">'
        f'<div class="module-icon-shell"><div class="module-icon">{icon_text}</div></div>'
        '<div>'
        f'<div class="module-rarity">{rarity_text}</div>'
        f'<div class="module-name">{name}</div>'
        f'<div class="module-level">{level_text}</div>'
        '</div>'
        '</div>'
        '<div class="module-main">'
        f'<div class="module-main-value">{main_value}</div>'
        f'<div class="module-main-label">{main_label}</div>'
        '</div>'
        f'{unique_html}'
        f'<div class="module-effects">{effects}</div>'
        '</div>'
        '</div>'
    )
