#!/usr/bin/env python3
from __future__ import annotations

import argparse
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.lines import Line2D

def luminance(hex_color: str) -> float:
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    return 0.2126*r + 0.7152*g + 0.0722*b

def text_color_for(bg_hex: str) -> str:
    if bg_hex == "none":
        return "black"
    return "white" if luminance(bg_hex) < 0.55 else "black"

def box(ax, x, y, w, h, heading, body, fill,
        fs_head=9.0, fs_body=6.8, head_y=0.86, body_y=0.44, lw=1.15,
        linesp=1.00, align="center", head_wrap=False, pad=0.010,
        ec="black", ls="-"):
    tc = text_color_for(fill)
    patch = FancyBboxPatch((x, y), w, h,
                           boxstyle=f"round,pad={pad},rounding_size=0.02",
                           linewidth=lw, edgecolor=ec,
                           facecolor=fill if fill != "none" else "none",
                           linestyle=ls)
    ax.add_patch(patch)
    ax.text(x + w/2, y + h*head_y, heading,
            ha="center", va="center",
            fontsize=fs_head, fontweight="bold",
            color=tc, wrap=head_wrap)
    if body:
        ha = "center" if align == "center" else "left"
        x_text = x + w/2 if align == "center" else x + 0.010
        ax.text(x_text, y + h*body_y, body,
                ha=ha, va="center",
                fontsize=fs_body, color=tc,
                wrap=True, linespacing=linesp)
    return (x, y, w, h, y + h/2)

def arrow(ax, x1, y1, x2, y2, lw=1.05, head=9, dashed=False, alpha=1.0):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2),
                                 arrowstyle="-|>",
                                 mutation_scale=head,
                                 linewidth=lw,
                                 color="black",
                                 linestyle="--" if dashed else "-",
                                 alpha=alpha))

COL = {
    "external": "#1F77B4",
    "composition": "#003B73",
    "runtime": "#FF7F0E",
    "rules": "#7B52AB",
    "builder": "#2CA02C",
    "atwave": "#1B9E77",
    "artifacts": "#F4F4F4",
    "eval": "#D62728",
    "infra": "#8C564B",
    "guard": "#6E6E6E",
    "contracts": "#444444",
    "agent": "#0B5FA5",
}

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out/contract_diagram_v35_draft/towersim_contract_diagram_v35_draft.png")
    args = ap.parse_args()

    fig, ax = plt.subplots(figsize=(18.5, 11.2))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")

    ax.text(0.5, 0.975, "TowerSim Target-State Canonical Pipeline (Contract Diagram)", ha="center", va="top",
            fontsize=16, fontweight="bold")
    ax.text(0.5, 0.948,
            "Alignment-driven layout: dependencies + Agent/CI outputs align exactly to their pipeline stage (same top/bottom).",
            ha="center", va="top", fontsize=11)
    ax.add_line(Line2D([0.02, 0.98], [0.93, 0.93], linewidth=1.0, alpha=0.3))

    legend_x, legend_w = 0.02, 0.16
    deps_x, deps_w     = 0.20, 0.23
    pipe_x, pipe_w     = 0.45, 0.28
    out_x, out_w       = 0.75, 0.23
    top, bottom = 0.89, 0.08

    legend_h = 0.81; legend_y = bottom
    ax.add_patch(FancyBboxPatch((legend_x, legend_y), legend_w, legend_h,
                                boxstyle="round,pad=0.012,rounding_size=0.02",
                                linewidth=1.2, edgecolor="black", facecolor="#FFFFFF"))
    ax.text(legend_x + legend_w/2, legend_y + legend_h - 0.035, "Legend", ha="center", va="center",
            fontsize=12, fontweight="bold")

    legend_items = [
        ("External Entry", "GitHub Actions / Agents", COL["external"]),
        ("Composition Root", "standard ⊕ overlay", COL["composition"]),
        ("Runtime Inputs", "AccountSnapshot + Loadout", COL["runtime"]),
        ("Rule Resolution", "immutable ruleset", COL["rules"]),
        ("Canonical Builder", "Base + Start only", COL["builder"]),
        ("AtWave Engine", "time evolution only", COL["atwave"]),
        ("Artifacts", "serialized stage states", COL["artifacts"]),
        ("Evaluators", "metrics only", COL["eval"]),
        ("Dependencies", "Tables / Registry", COL["infra"]),
        ("Contracts/Gates", "CI enforcement", COL["contracts"]),
        ("Guardrails", "scope constraints", COL["guard"]),
        ("Agent/CI Outputs", "stage-aligned", COL["agent"]),
    ]
    li_h = 0.050; li_gap = 0.010
    yy = legend_y + legend_h - 0.10
    for htxt, btxt, col in legend_items:
        box(ax, legend_x + 0.012, yy - li_h, legend_w - 0.024, li_h,
            htxt, btxt, col, fs_head=8.0, fs_body=6.5, head_y=0.70, body_y=0.30,
            lw=1.0, pad=0.007, linesp=1.0)
        yy -= li_h + li_gap

    gap = 0.020
    hmap = {"ext":0.074,"comp":0.088,"acct":0.158,"load":0.094,"rules":0.112,"build":0.116,"atwave":0.146,"art":0.118,"eval":0.110}
    total = sum(hmap.values()) + gap*8
    scale = min(1.0, (top-bottom)/total)
    for k in hmap: hmap[k] *= scale
    gap *= scale

    account_snapshot_body = "Workshop\nEnhancements\nLabs\nRelics\nUltimate Weapons\nBots (owned)\nUnlocks\nAccount toggles\nCurrencies"
    loadout_body = "Cards\nModules\nBots (equipped)\nScenario toggles\nPerk plan (optional)"
    ruleset_body = "Tier → BC → Heat (order enforced)\nStatic for entire run\nTable-driven magnitudes\nNo wave-index logic"
    builder_body = "Outputs: BaseState + StartOfRunState\nNo rule computation\nValidates via Stat Registry\nNo CSV reads (typed tables only)"
    atwave_body = "Inputs: Start + Ruleset + WaveTimeline\nApplies: perks • free-ups • ramps • events\nUses registry IDs only\nCannot create/rename stat IDs\nNo table loads (typed tables only)"
    artifacts_body = "BaseState\nStartOfRunState\nAtWaveState\n(provenance + cache keys)\nByte-deterministic serialization"
    eval_body = "Consume artifacts only\nMetrics only\nNo compile • No table loads\nNo forward simulation"

    pipeline = [
        ("External Entry", "GitHub Actions + Agents", COL["external"], hmap["ext"], dict(fs_body=8.0, head_y=0.78, body_y=0.44, linesp=1.03)),
        ("Composition Root (wiring)", "run/api.py\nmerge standard ⊕ overlay\nOverlay logged in provenance\nNo hidden defaults", COL["composition"], hmap["comp"], dict(fs_body=6.9, head_y=0.86, body_y=0.44, linesp=1.00)),
        ("1) AccountSnapshot (ingested)", account_snapshot_body, COL["runtime"], hmap["acct"], dict(fs_body=6.4, head_y=0.90, body_y=0.46, linesp=1.00)),
        ("2) LoadoutSpec (resolved)", loadout_body, COL["runtime"], hmap["load"], dict(fs_body=7.0, head_y=0.86, body_y=0.46, linesp=1.02)),
        ("3) ResolvedRuleset (immutable)", ruleset_body, COL["rules"], hmap["rules"], dict(fs_body=6.8, head_y=0.86, body_y=0.46, linesp=1.00)),
        ("4) Canonical Builder", builder_body, COL["builder"], hmap["build"], dict(fs_body=6.7, head_y=0.86, body_y=0.46, linesp=1.00)),
        ("5) AtWave Engine", atwave_body, COL["atwave"], hmap["atwave"], dict(fs_body=6.3, head_y=0.88, body_y=0.48, linesp=0.98)),
        ("6) Stage API + Artifacts", artifacts_body, COL["artifacts"], hmap["art"], dict(fs_body=6.9, head_y=0.86, body_y=0.46, linesp=1.00)),
        ("7) Evaluators (pure)", eval_body, COL["eval"], hmap["eval"], dict(fs_body=6.9, head_y=0.86, body_y=0.46, linesp=1.00)),
    ]

    pipe_pos = {}
    y = top
    for heading, body, col, hh, kw in pipeline:
        pipe_pos[heading] = box(ax, pipe_x, y - hh, pipe_w, hh, heading, body, col,
                                fs_head=9.0, fs_body=kw["fs_body"],
                                head_y=kw["head_y"], body_y=kw["body_y"],
                                linesp=kw["linesp"], pad=0.010)
        y -= hh + gap

    for a, b in zip([p[0] for p in pipeline[:-1]], [p[0] for p in pipeline[1:]]):
        xmid = pipe_x + pipe_w/2
        y1 = pipe_pos[a][1]
        y2 = pipe_pos[b][1] + pipe_pos[b][3]
        arrow(ax, xmid, y1, xmid, y2, lw=1.1, head=10)

    dep_defs = {
        "3) ResolvedRuleset (immutable)": ("Typed Tables (loaded)", "Loaded + validated\nTyped table objects\nOnly interface to engines", COL["infra"], False),
        "4) Canonical Builder": ("Stat Registry (authoritative)", "Stat IDs\nCaps / floors\nModifier contracts\nValidation rules\nNo stat ID creation\noutside registry", COL["infra"], False),
        "5) AtWave Engine": ("Typed Tables + Registry", "Uses Typed Tables (no CSV)\nRegistry IDs only\nNo stat creation", COL["infra"], False),
        "6) Stage API + Artifacts": ("Contracts + CI Gates", "1) Ruleset immutability hash\n2) Loader boundary check\n3) Artifact byte-diff determinism", COL["contracts"], True),
        "7) Evaluators (pure)": ("Guardrails (enforced)", "Consume artifacts only\nNo table loads\nNo forward simulation\nNo parallel stat assembly", COL["guard"], True),
        "Composition Root (wiring)": ("Guardrails (enforced)", "Wiring only\nOverlay logged\nNo hidden defaults\nNo patching registry/tables", COL["guard"], True),
    }

    for stage_key, (dtitle, dbody, dcol, dashed) in dep_defs.items():
        sx, sy, sw, sh, scy = pipe_pos[stage_key]
        box(ax, deps_x, sy, deps_w, sh, dtitle, dbody, dcol,
            fs_head=8.6, fs_body=6.2 if dcol != COL["infra"] else 6.4,
            head_y=0.86, body_y=0.46, linesp=1.00,
            pad=0.010, ls="--" if dashed else "-", ec="black")
        arrow(ax, deps_x + deps_w, scy, pipe_x, scy, lw=1.0, head=9, dashed=dashed, alpha=0.75 if dashed else 1.0)

    rules_y = pipe_pos["3) ResolvedRuleset (immutable)"][1]
    rules_h = pipe_pos["3) ResolvedRuleset (immutable)"][3]
    raw_sources = box(ax, deps_x, rules_y + rules_h + 0.010, deps_w, rules_h*0.78,
                      "Raw Tables (sources)",
                      "CSV/YAML sources\n(authoritative)\nNot accessible by engines",
                      COL["infra"],
                      fs_head=8.6, fs_body=6.4, head_y=0.86, body_y=0.46, pad=0.010)
    typed_center_x = deps_x + deps_w/2
    arrow(ax, typed_center_x, raw_sources[1], typed_center_x, rules_y + rules_h, lw=1.0, head=9)

    pipe_right = pipe_x + pipe_w
    def out_stage(stage_key, title, body, fs_body):
        sx, sy, sw, sh, scy = pipe_pos[stage_key]
        box(ax, out_x, sy, out_w, sh, title, body, COL["agent"],
            fs_head=7.6, fs_body=fs_body,
            head_y=0.90, body_y=0.46, linesp=0.95,
            align="left", head_wrap=True, pad=0.006)
        arrow(ax, pipe_right, scy, out_x, scy, lw=1.0, head=9)

    out_stage(
        "1) AccountSnapshot (ingested)",
        "Agent/CI outputs @ AccountSnapshot",
        "stats_dump.yml\n• out/account_snapshot.json\n• out/account_snapshot.summary.json\n• out/ids_dump_latest.json",
        fs_body=6.05
    )
    out_stage(
        "4) Canonical Builder",
        "Agent/CI outputs @ Canonical Builder",
        "stats_dump.yml\n• out/base_stats.json; out/inventory.json; out/loadout.json\n• out/*_components.json\n• out/compiled_stat_inputs.json; out/stat_engine.json\n• out/resolved_problem_spec.json\n• out/stage_1..3_*.json",
        fs_body=5.85
    )
    out_stage(
        "5) AtWave Engine",
        "Agent/CI outputs @ AtWave Engine",
        "stats_dump.yml\n• out/stage_4_with_battle_conditions.json\n• out/stage_5_end_of_run.json\n• out/max_wave.json\nmax_wave_runner.yml\n• out/runner_output_latest.json\nperk_timeline_runner.yml\n• out/perk_timeline/latest.json",
        fs_body=5.65
    )
    out_stage(
        "7) Evaluators (pure)",
        "Agent/CI outputs @ Evaluators",
        "max_wave_runner.yml\n• out/ep_export_final_stats_report_latest.json\n• out/stat_lineage_manifest_latest.json\n• out/stat_lineage_contract_gate_latest.json\nperk_timeline_runner.yml\n• out/perk_timeline/diagnostics.json",
        fs_body=5.65
    )

    ax.add_line(Line2D([out_x-0.008, out_x-0.008], [bottom, top], linewidth=0.8, alpha=0.10))

    scope_x = pipe_x - 0.01
    scope_w = (out_x + out_w) - scope_x + 0.01
    scope_y = bottom - 0.01
    scope_h = (top - bottom) + 0.02
    ax.add_patch(FancyBboxPatch((scope_x, scope_y), scope_w, scope_h,
                                boxstyle="round,pad=0.005,rounding_size=0.02",
                                linewidth=1.0, edgecolor="black", facecolor="none",
                                linestyle="--", alpha=0.16))

    plt.savefig(args.out, bbox_inches="tight")
    print(f"Wrote: {args.out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
