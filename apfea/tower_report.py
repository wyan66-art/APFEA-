"""Control-tower report - Part Two's deliverable: status + feedback + actions."""
from __future__ import annotations

from .tower import STAGES


def render_tower_report(flow, status, feedback, updated_rules, doe_rev_b) -> str:
    lines = []
    lines.append("# APFEA Control Tower Report (prototype v0.2)")
    lines.append("")
    lines.append(f"- **Program**: {status['program']}")
    lines.append(f"- **Current stage reached**: {status['current_stage']}")
    lines.append(f"- **Program health**: **{status['health']}**")
    lines.append("")

    lines.append("## Flow status")
    lines.append("")
    seen_names = set(status["stages_seen"])
    for _key, name in STAGES:
        mark = "done" if name in seen_names else "pending"
        lines.append(f"- {name}: {mark}")
    lines.append("")

    if feedback:
        lines.append("## VT feedback - anticipated vs realized (fab corner-lot readout)")
        lines.append("")
        lines.append("| Flavor | Anticipated shift | Realized shift | Delta (estimator bias) |")
        lines.append("|---|---|---|---|")
        for f in sorted(feedback["realized_pct"]):
            lines.append(
                f"| {f} | {feedback['anticipated_pct'][f]:+.2f}% | "
                f"{feedback['realized_pct'][f]:+.2f}% | {feedback['delta_pct'][f]:+.2f}% |"
            )
        lines.append("")
        lines.append(
            f"RMS estimator bias this cycle: {feedback['rms_delta_pct']:.2f}%. "
            f"Residual estimation error for the next tape-out: "
            f"{feedback['old_est_err_pct']:.2f}% -> **{feedback['new_est_err_pct']:.2f}%** "
            "(refit from silicon, floored - calibration shrinks humility, never erases it)."
        )
        lines.append("")
        lines.append("**Refit shift rules for the next tape-out** (config/shift_rules.json values):")
        lines.append("")
        for f in sorted(updated_rules["base_shift_pct"]):
            lines.append(f"- {f}: {updated_rules['base_shift_pct'][f]:+.2f}%")
        lines.append("")

    lines.append("## Rev-B margin re-check (refit rules, Part One DOE re-run)")
    lines.append("")
    lines.append("| Block | Flavor | Window | Worst-case dev | Verdict |")
    lines.append("|---|---|---|---|---|")
    for b in doe_rev_b["blocks"]:
        disp = b["name"]
        if b.get("fixed"):
            disp += " (foundry-fixed @VT0 - center check)"
        elif b.get("co_optimizable"):
            disp += " (IDM co-optimized @VTs)"
        lines.append(
            f"| {disp} | {b['flavor']} | {b['window_pct']:.1f}% | "
            f"{b['apfea_worst_dev_pct']:.1f}% | "
            f"{'PASS' if b['apfea_pass'] else '**AT RISK**'} |"
        )
    lines.append("")

    lines.append("## Block health (downstream data)")
    lines.append("")
    if status["block_health"]:
        for block, (st, detail) in sorted(status["block_health"].items()):
            lines.append(f"- **{block}**: {st} - {detail}")
    else:
        lines.append("- no downstream block data yet")
    for note in status["notes"]:
        lines.append(f"- note: {note}")
    lines.append("")

    lines.append("## Open actions")
    lines.append("")
    if status["actions"]:
        for a in status["actions"]:
            lines.append(f"- {a}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append(
        "_Scope note: the tower observes, attributes, and recommends; it does not "
        "actuate fab equipment. Planner-level bookkeeping per APFEA v3 Part Two._"
    )
    return "\n".join(lines) + "\n"
