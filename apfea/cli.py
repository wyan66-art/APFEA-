"""CLI: python -m apfea run [--pdk ..] [--chip ..] [--rules ..] [--out report.md]"""
from __future__ import annotations

import argparse
from pathlib import Path

from .doe import corner_table, evaluate_blocks
from .report import render_report
from .tower import realized_shifts, refit_rules, tower_status
from .tower_report import render_tower_report
from .vtshift import estimate_vts, load_json

ROOT = Path(__file__).resolve().parent.parent
DEFAULTS = {
    "pdk": ROOT / "data" / "demo_pdk.json",
    "chip": ROOT / "data" / "demo_chip.json",
    "rules": ROOT / "config" / "shift_rules.json",
    "flow": ROOT / "data" / "demo_flow.json",
}


def _load(args):
    return (
        load_json(args.pdk),
        load_json(args.chip),
        load_json(args.rules),
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="apfea", description="APFEA prototype v0.1")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("estimate", "run", "tower"):
        p = sub.add_parser(name)
        p.add_argument("--pdk", default=str(DEFAULTS["pdk"]))
        p.add_argument("--chip", default=str(DEFAULTS["chip"]))
        p.add_argument("--rules", default=str(DEFAULTS["rules"]))
        if name in ("run", "tower"):
            p.add_argument("--out", default=None, help="write report to this file")
            p.add_argument(
                "--mode",
                choices=("foundry", "idm"),
                default=None,
                help="override the chip's business_model (foundry: SRAM fixed at VT0; idm: co-optimize)",
            )
        if name == "tower":
            p.add_argument("--flow", default=str(DEFAULTS["flow"]))
    args = ap.parse_args(argv)
    pdk, chip, rules = _load(args)
    if getattr(args, "mode", None):
        chip = dict(chip, business_model=args.mode)
    est = estimate_vts(pdk, chip, rules)

    if args.cmd == "estimate":
        for r in est["rows"]:
            print(
                f"{r['flavor']:>5} {r['polarity']}  VT0 {r['vt0']:+.3f} V  "
                f"shift {r['shift_pct']:+.1f}%  ->  VTs {r['vts']:+.4f} V"
            )
        return 0

    if args.cmd == "tower":
        flow = load_json(args.flow)
        doe_a = evaluate_blocks(pdk, chip, est, rules)
        feedback, updated_rules = None, rules
        if flow.get("vt_measurement"):
            realized = realized_shifts(pdk, flow["vt_measurement"])
            updated_rules, feedback = refit_rules(rules, realized)
        est_b = estimate_vts(pdk, chip, updated_rules)
        doe_b = evaluate_blocks(pdk, chip, est_b, updated_rules)
        status = tower_status(flow, doe_a, feedback)
        text = render_tower_report(flow, status, feedback, updated_rules, doe_b)
        if args.out:
            Path(args.out).write_text(text, encoding="utf-8")
            print(f"tower report written to {args.out}")
        else:
            print(text)
        return 0

    doe = evaluate_blocks(pdk, chip, est, rules)
    corners = corner_table(pdk, est)
    text = render_report(pdk, chip, est, doe, corners)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"report written to {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
