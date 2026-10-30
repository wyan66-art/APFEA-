"""VT-shift estimator - APFEA v3 Part One, step I ("pre-emptive strike").

The foundry PDK is characterized on a plain test chip. A customer chip
(different size, fabric, specialty devices) realizes different threshold
voltages. APFEA designs against the anticipated VTs = VT0 +/- x%, estimated
from the test-chip vs customer-chip differences plus historical data -
NOT against VT0.

Shift percentages act on |VT| (device strength); the sign of VT0 is kept.
All shift values live in config/shift_rules.json - phenomenology as data,
fitted per foundry/design-house pair, never hard-coded physics.
"""
from __future__ import annotations

import json
import math
from pathlib import Path


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def estimate_vts(pdk: dict, chip: dict, rules: dict) -> dict:
    """Apply the shift rules to every flavor/polarity in the PDK.

    Returns {"rules_apply": bool, "rows": [ {flavor, polarity, vt0,
    shift_pct, vts, sigma_pct}, ... ]}.
    """
    applies = chip.get("chip_type") in rules.get("applies_to_chip_types", [])
    rows = []
    for flavor in sorted(pdk["flavors"]):
        dev = pdk["flavors"][flavor]
        shift = float(rules.get("base_shift_pct", {}).get(flavor, 0.0)) if applies else 0.0
        for polarity, key in (("N", "nmos_vt0"), ("P", "pmos_vt0")):
            vt0 = float(dev[key])
            vts = math.copysign(abs(vt0) * (1.0 + shift / 100.0), vt0)
            rows.append(
                {
                    "flavor": flavor,
                    "polarity": polarity,
                    "vt0": vt0,
                    "shift_pct": shift,
                    "vts": vts,
                    "sigma_pct": float(dev["sigma_pct"]),
                }
            )
    return {"rules_apply": applies, "rows": rows}


def flavor_table(est: dict) -> dict:
    """flavor -> {shift_pct, sigma_pct} summary used by the DOE planner."""
    out = {}
    for r in est["rows"]:
        out[r["flavor"]] = {"shift_pct": r["shift_pct"], "sigma_pct": r["sigma_pct"]}
    return out
