"""Corner-lot DOE planner - APFEA v3 Part One, step II.

Post-design, pre-tape-out: run the DOE with the SAME splits as a real
silicon corner lot (VTs +/- 3 sigma) for each functional block and, by
extension, the whole chip.

Two kinds of blocks, two different logics:

* Customer CMOS blocks (the design house's own logic). Margin model in
  % of |VT|: the chip's true VT center is the anticipated VTs.
    - Conventional flow designs against VT0 -> worst-case deviation of
      silicon from the design center = |shift| + 3*sigma.
    - APFEA flow designs against VTs -> worst-case deviation =
      3*sigma + est_err (residual estimation error only).
  A block passes a flow iff worst-case deviation <= its window_pct.
  Failing blocks are the design house's own logic: REDESIGN is a
  legitimate action (widen the margin) - v3 step II.

* Foundry-fixed blocks (e.g. SRAM). The foundry supplies the macro and
  its spec; it is IDENTICAL for every customer and its spec is NOT to
  be touched. There is no redesign action for it - ever. What the DOE
  checks instead is a CONSTRAINT: the foundry characterizes the macro
  around VT0 with a tolerance on the chip-level VT center shift
  (center_tol_pct). If the anticipated shift for its flavor exceeds
  that tolerance, the constraint is violated and the remedy is entirely
  on the CMOS side: CMOS design centering (VTs), flavor strategy, and
  process targeting agreed with the foundry - never the SRAM spec.

VTs1 (v3 II.d) - the center to use for real silicon corner-lot splits -
equals VTs, subject to the foundry-fixed constraints above.
"""
from __future__ import annotations

from .vtshift import flavor_table

CORNERS = (-3, -2, -1, 0, 1, 2, 3)


def evaluate_blocks(pdk: dict, chip: dict, est: dict, rules: dict) -> dict:
    ft = flavor_table(est)
    est_err = float(rules.get("est_err_pct", 0.0))
    # Business model decides what is adjustable (rule set by the APFEA
    # author, 2026-10-20):
    #   foundry - SRAM is foundry-fixed, identical for every customer:
    #             spec untouchable, design point stays at VT0; only the
    #             customer's CMOS VTs change. SRAM enters as a CONSTRAINT.
    #   idm     - one company owns design AND fab, SRAM included: VTs are
    #             co-optimized for CMOS and SRAM together, so the SRAM
    #             block is designed at VTs and evaluated (and, if needed,
    #             redesigned) like any CMOS block.
    mode = str(chip.get("business_model", "foundry")).lower()
    blocks = []
    for b in chip["blocks"]:
        f = ft[b["flavor"]]
        shift, sigma = f["shift_pct"], f["sigma_pct"]
        spread = 3.0 * sigma
        if b.get("fixed") and mode != "idm":
            tol = float(b["center_tol_pct"])
            blocks.append(
                {
                    "name": b["name"],
                    "flavor": b["flavor"],
                    "fixed": True,
                    "center_tol_pct": tol,
                    "window_pct": tol,  # display parity with CMOS rows
                    "timing_sensitive": bool(b.get("timing_sensitive", False)),
                    "note": b.get("note", ""),
                    "shift_pct": shift,
                    "sigma_pct": sigma,
                    "spread3_pct": spread,
                    # exposure is the center shift itself; the conventional
                    # flow simply never checks it before tape-out.
                    "conv_worst_dev_pct": abs(shift),
                    "apfea_worst_dev_pct": abs(shift),
                    "conv_pass": None,  # unchecked in the conventional flow
                    "apfea_pass": abs(shift) <= tol,
                }
            )
        else:
            conv_dev = abs(shift) + spread
            apfea_dev = spread + est_err
            window = float(b["window_pct"])
            blocks.append(
                {
                    "name": b["name"],
                    "flavor": b["flavor"],
                    "fixed": False,
                    # in IDM mode a nominally "fixed" block (SRAM) is in
                    # fact ours: designed at VTs and co-optimized.
                    "co_optimizable": bool(b.get("fixed")) and mode == "idm",
                    "window_pct": window,
                    "timing_sensitive": bool(b.get("timing_sensitive", False)),
                    "note": b.get("note", ""),
                    "shift_pct": shift,
                    "sigma_pct": sigma,
                    "spread3_pct": spread,
                    "conv_worst_dev_pct": conv_dev,
                    "apfea_worst_dev_pct": apfea_dev,
                    "conv_pass": conv_dev <= window,
                    "apfea_pass": apfea_dev <= window,
                }
            )
    redesign = [b["name"] for b in blocks if not b["fixed"] and not b["apfea_pass"]]
    constraints = [
        {
            "name": b["name"],
            "flavor": b["flavor"],
            "center_tol_pct": b["center_tol_pct"],
            "shift_pct": b["shift_pct"],
        }
        for b in blocks
        if b["fixed"] and not b["apfea_pass"]
    ]
    return {
        "blocks": blocks,
        "business_model": mode,
        "est_err_pct": est_err,
        "redesign_required": redesign,
        "constraints_violated": constraints,
        "vts1_center": "VTs (anticipated true center from step I)",
        "vts1_note": (
            "Use VTs as the center for real silicon corner-lot splits; "
            "in IDM mode the same VTs co-optimize CMOS and SRAM together."
            if mode == "idm"
            else "Use VTs as the center for real silicon corner-lot splits, "
            "subject to the foundry-fixed block constraints: the remedy "
            "for a violated constraint is CMOS-side (design centering, "
            "flavor strategy, process targeting with the foundry) - "
            "the fixed block's spec is never touched."
        ),
    }


def corner_table(pdk: dict, est: dict) -> list:
    """Silicon corner values of |VT| around VTs for each flavor (k = -3..+3 sigma)."""
    by_flavor = {}
    for r in est["rows"]:
        if r["polarity"] == "N":  # |VT| table is polarity-symmetric by construction
            by_flavor[r["flavor"]] = r
    out = []
    for flavor in sorted(by_flavor):
        r = by_flavor[flavor]
        base = abs(r["vts"])
        corners = {k: base * (1.0 + k * r["sigma_pct"] / 100.0) for k in CORNERS}
        out.append({"flavor": flavor, "vts_abs": base, "sigma_pct": r["sigma_pct"], "corners": corners})
    return out
