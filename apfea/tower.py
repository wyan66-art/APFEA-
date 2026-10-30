"""Part Two control tower - AI AGTs for Fabrication, 2.5D/3D Packaging
& PCBA System/Testing (APFEA v3, Part Two), with the feedback loop
that makes APFEA a system rather than a checklist:

  design -> tapeout -> fab -> interposer -> wafer sort -> 3D packaging
  -> final test -> PCBA -> system, and downstream data back into design.

Two feedback channels are implemented (planner level):

1. VT feedback (fab stage). The real-silicon corner-lot stress test
   (v3 Part One, step III) measures the realized VT center per flavor.
   realized_shift = measured|VT| / |VT0| - 1 is compared with the
   anticipated shift from step I; the delta is the estimator's measured
   bias, and the shift rules are REFIT from silicon for the next
   tape-out. Residual estimation error is re-estimated from the deltas.

2. Yield feedback (wafer sort / final test). Per-block yields and test
   results roll up into block health; a block that Part One flagged and
   silicon then fails is an escalated, evidence-backed action.

Nothing here actuates a fab. The tower observes, attributes, and
recommends - the AGT control-tower role in v3's architecture.
"""
from __future__ import annotations

import math

STAGES = [
    ("design", "Design"),
    ("tapeout", "Tape-out"),
    ("fab", "Fabrication"),
    ("interposer", "Interposer"),
    ("wafer_sort", "Wafer sort"),
    ("packaging_3d", "2.5D/3D packaging"),
    ("final_test", "Final test"),
    ("pcba", "PCBA"),
    ("system", "System"),
]
STAGE_KEYS = [k for k, _ in STAGES]


def realized_shifts(pdk: dict, measured_abs_vt_n: dict) -> dict:
    """flavor -> realized shift % from measured |VT| (N-device center)."""
    out = {}
    for flavor, meas in measured_abs_vt_n.items():
        vt0 = abs(float(pdk["flavors"][flavor]["nmos_vt0"]))
        out[flavor] = (float(meas) / vt0 - 1.0) * 100.0
    return out


def refit_rules(rules: dict, realized: dict) -> tuple[dict, dict]:
    """Return (updated_rules, feedback) with base shifts fitted to silicon.

    updated est_err = RMS(anticipated-vs-realized deltas) / 2, floored
    at 0.2% - one silicon cycle should shrink, not erase, humility.
    """
    old = rules.get("base_shift_pct", {})
    deltas = {f: realized[f] - float(old.get(f, 0.0)) for f in realized}
    rms = math.sqrt(sum(d * d for d in deltas.values()) / len(deltas)) if deltas else 0.0
    new_err = max(0.2, rms / 2.0)
    updated = dict(rules)
    updated["base_shift_pct"] = {**old, **{f: round(realized[f], 2) for f in realized}}
    updated["est_err_pct"] = round(new_err, 2)
    feedback = {
        "anticipated_pct": {f: float(old.get(f, 0.0)) for f in realized},
        "realized_pct": {f: round(realized[f], 2) for f in realized},
        "delta_pct": {f: round(deltas[f], 2) for f in realized},
        "rms_delta_pct": round(rms, 2),
        "old_est_err_pct": float(rules.get("est_err_pct", 0.0)),
        "new_est_err_pct": round(new_err, 2),
    }
    return updated, feedback


def block_health(flow: dict) -> dict:
    """block -> (status, detail) from downstream yield/test observations."""
    health = {}
    for obs in flow.get("observations", []):
        if obs["kind"] == "block_yield":
            for block, y in obs["data"].get("block_yields_pct", {}).items():
                status = "GREEN" if y >= 98.0 else ("YELLOW" if y >= 95.0 else "RED")
                health[block] = (status, f"wafer-sort yield {y:.1f}%")
            if obs["data"].get("note"):
                health.setdefault("_notes", []).append(obs["data"]["note"])
        elif obs["kind"] == "block_test":
            for block, res in obs["data"].get("block_results", {}).items():
                status = "GREEN" if str(res).lower().startswith("pass") else "YELLOW"
                health[block] = (status, f"final test: {res}")
            if obs["data"].get("note"):
                health.setdefault("_notes", []).append(obs["data"]["note"])
    return health


def tower_status(flow: dict, part_one_doe: dict, feedback: dict | None) -> dict:
    """Roll everything up: program stage, health, and open actions."""
    seen = flow.get("stages_seen", [])
    furthest = max((STAGE_KEYS.index(s) for s in seen), default=-1)
    health = block_health(flow)
    block_status = {k: v for k, v in health.items() if not k.startswith("_")}
    worst = "GREEN"
    for status, _ in block_status.values():
        if status == "RED":
            worst = "RED"
        elif status == "YELLOW" and worst == "GREEN":
            worst = "YELLOW"
    actions = []
    idm = part_one_doe.get("business_model") == "idm"
    for name in part_one_doe.get("redesign_required", []):
        confirmed = block_status.get(name, ("", ""))[0] == "RED"
        verb = "CO-OPTIMIZE" if idm else "REDESIGN"
        actions.append(
            f"{verb} {name} before next tape-out"
            + (" - CONFIRMED by silicon yield data" if confirmed else " - per Part One DOE")
        )
    for c in part_one_doe.get("constraints_violated", []):
        name = c["name"]
        confirmed = block_status.get(name, ("", ""))[0] == "RED"
        actions.append(
            f"HOLD SPEC: {name} is foundry-fixed and stays at VT0 - "
            + ("silicon yield loss CONFIRMED; " if confirmed else "")
            + f"remedy is CMOS-side only: pull the {c['flavor']} silicon center "
            f"within +/-{c['center_tol_pct']:.1f}% of VT0 via CMOS VTs centering "
            "and foundry process targeting. Never redesign the fixed block."
        )
    if feedback:
        actions.append(
            "Apply silicon-refit shift rules to the next tape-out "
            f"(est. error {feedback['old_est_err_pct']:.2f}% -> "
            f"{feedback['new_est_err_pct']:.2f}%)"
        )
    return {
        "program": flow.get("program", "unnamed program"),
        "current_stage": STAGES[furthest][1] if furthest >= 0 else "not started",
        "stages_seen": [dict(STAGES)[s] for s in seen],
        "health": worst,
        "block_health": block_status,
        "notes": health.get("_notes", []),
        "actions": actions,
    }
