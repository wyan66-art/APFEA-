"""Pre-tape-out margin report - the APFEA deliverable a design house acts on."""
from __future__ import annotations


def _verdict(ok) -> str:
    if ok is None:
        return "unchecked"
    return "PASS" if ok else "**AT RISK**"


def render_report(pdk: dict, chip: dict, est: dict, doe: dict, corners: list) -> str:
    lines = []
    lines.append("# APFEA Pre-Tape-Out Margin Report (prototype v0.2)")
    lines.append("")
    lines.append(f"- **PDK**: {pdk['name']}")
    lines.append(
        f"- **Customer chip**: {chip['name']} - type `{chip['chip_type']}`, "
        f"die {chip['die_area_mm2']} mm^2, specialty devices: "
        f"{', '.join(chip.get('specialty_devices', [])) or 'none'}"
    )
    lines.append(
        f"- **Shift rules apply**: {'yes' if est['rules_apply'] else 'no'} "
        f"(chip type gate in config/shift_rules.json)"
    )
    lines.append(f"- **Residual estimation error carried**: {doe['est_err_pct']:.2f}%")
    _mode = doe.get("business_model", "foundry")
    lines.append(
        f"- **Business model**: {_mode} - "
        + (
            "foundry-fixed blocks (SRAM) keep VT0, spec untouchable; only CMOS VTs change"
            if _mode != "idm"
            else "SRAM is ours: VTs are co-optimized for CMOS and SRAM together"
        )
    )
    lines.append("")

    lines.append("## Step I - Anticipated VTs (CMOS designs against VTs, not VT0)")
    lines.append("")
    lines.append("| Flavor | Pol | VT0 (V) | Shift | VTs (V) | sigma (% of \\|VT\\|) |")
    lines.append("|---|---|---|---|---|---|")
    for r in est["rows"]:
        lines.append(
            f"| {r['flavor']} | {r['polarity']} | {r['vt0']:+.3f} | "
            f"{r['shift_pct']:+.1f}% | {r['vts']:+.4f} | {r['sigma_pct']:.1f} |"
        )
    lines.append("")
    lines.append(
        "Foundry-fixed blocks (e.g. SRAM) are NOT shifted: they keep VT0 as their "
        "design point, exactly as the foundry supplies them. VTs apply to the "
        "customer's CMOS design only."
    )
    lines.append("")

    lines.append("## Silicon corner splits around VTs (|VT|, N devices, CMOS flavors)")
    lines.append("")
    header = "| Flavor | " + " | ".join(f"{k:+d}sigma" for k in (-3, -2, -1, 0, 1, 2, 3)) + " |"
    lines.append(header)
    lines.append("|" + "---|" * 8)
    for c in corners:
        cells = " | ".join(f"{c['corners'][k]:.4f}" for k in (-3, -2, -1, 0, 1, 2, 3))
        lines.append(f"| {c['flavor']} | {cells} |")
    lines.append("")

    lines.append("## Step II - Block checks")
    lines.append("")
    lines.append("### Customer CMOS blocks (worst-case deviation vs block window)")
    lines.append("")
    lines.append(
        "| Block | Flavor | Window | Conv. flow dev | Conv. | APFEA flow dev | APFEA |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    for b in doe["blocks"]:
        if b["fixed"]:
            continue
        disp = b["name"] + (" (IDM co-optimized @VTs)" if b.get("co_optimizable") else "")
        lines.append(
            f"| {disp} | {b['flavor']} | {b['window_pct']:.1f}% | "
            f"{b['conv_worst_dev_pct']:.1f}% | {_verdict(b['conv_pass'])} | "
            f"{b['apfea_worst_dev_pct']:.1f}% | {_verdict(b['apfea_pass'])} |"
        )
    lines.append("")
    lines.append(
        "Conventional flow designs against VT0, so silicon deviates from the design "
        "center by |shift| + 3 sigma in the worst case. The APFEA flow designs against "
        "VTs, leaving only 3 sigma + residual estimation error."
    )
    lines.append("")

    fixed = [b for b in doe["blocks"] if b["fixed"]]
    if fixed:
        lines.append("### Foundry-fixed blocks (design point stays at VT0 - spec untouchable)")
        lines.append("")
        lines.append("| Block | Flavor | Center tolerance | Anticipated center shift | Check |")
        lines.append("|---|---|---|---|---|")
        for b in fixed:
            lines.append(
                f"| {b['name']} | {b['flavor']} | +/-{b['center_tol_pct']:.1f}% | "
                f"{b['shift_pct']:+.1f}% | {_verdict(b['apfea_pass'])} |"
            )
        lines.append("")
        lines.append(
            "The conventional flow never performs this check before tape-out; APFEA "
            "performs it in Step II. A violated constraint is remedied on the CMOS "
            "side only - design centering, flavor strategy, process targeting with "
            "the foundry. The fixed block's spec is never an action item."
        )
        lines.append("")

    cmos = [b for b in doe["blocks"] if not b["fixed"]]
    n_risk_conv = sum(1 for b in cmos if not b["conv_pass"])
    n_risk_apfea = sum(1 for b in cmos if not b["apfea_pass"])
    lines.append("## Verdict")
    lines.append("")
    lines.append(
        f"- CMOS blocks at risk under the conventional (VT0) flow: "
        f"**{n_risk_conv} / {len(cmos)}** - each is a mask-fix re-tape-out exposure."
    )
    lines.append(
        f"- CMOS blocks at risk under the APFEA (VTs) flow: **{n_risk_apfea} / {len(cmos)}**."
    )
    if doe["redesign_required"]:
        label = (
            "Re-design / co-optimize before tape-out (IDM - SRAM included)"
            if doe.get("business_model") == "idm"
            else "Re-design before tape-out (customer CMOS)"
        )
        lines.append(
            f"- **{label}**: "
            + ", ".join(doe["redesign_required"])
            + " - design margin too small (v3 step II)."
        )
    for c in doe["constraints_violated"]:
        lines.append(
            f"- **Foundry-fixed constraint violated**: {c['name']} ({c['flavor']}) - "
            f"anticipated center shift {c['shift_pct']:+.1f}% exceeds its "
            f"+/-{c['center_tol_pct']:.1f}% tolerance around VT0. HOLD THE SPEC: "
            f"{c['name']} stays at VT0; pull the {c['flavor']} center back via "
            "CMOS-side centering and foundry process targeting."
        )
    lines.append(f"- **VTs1 for silicon corner lots**: {doe['vts1_center']}. {doe['vts1_note']}")
    lines.append("")
    lines.append(
        "_Scope note: planner-level margin bookkeeping per APFEA v3 Part One. "
        "No circuit simulation is run; block windows, tolerances and shift rules "
        "are configuration to be fitted from each foundry/design-house pair's "
        "own history._"
    )
    return "\n".join(lines) + "\n"
