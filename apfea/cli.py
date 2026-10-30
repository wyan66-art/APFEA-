"""CLI: python -m apfea run [--pdk ..] [--chip ..] [--rules ..] [--out report.md]"""
from __future__ import annotations

import argparse
from pathlib import Path

from .agent import FoundryProcessAgent, render_agent_report
from .comments import (add_note, approve_note, delete_note, edit_note,
                       meeting_conclusions, notes_for_stage, reject_note,
                       render_note, search_notes)
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
    "entries": ROOT / "data" / "demo_stage_entries.json",
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
    # Human notes on a node: `python -m apfea note add|list|search ...`
    # Handled before any PDK/chip load, because notes need no model data.
    pn = sub.add_parser("note", help="add/list/search human notes on a node")
    pn.add_argument("action", choices=("add", "list", "search", "conclusions",
                                      "approve", "reject", "edit", "delete"))
    pn.add_argument("--file", default=str(ROOT / "data" / "stage_comments.json"))
    pn.add_argument("--stage", default=None)
    pn.add_argument("--id", type=int, default=None)
    pn.add_argument("--approver", default="")
    pn.add_argument("--include-pending", action="store_true")
    pn.add_argument("--kind", default=None,
                    choices=(None, "comment", "meeting_conclusion",
                             "decision", "lesson_learned"))
    pn.add_argument("--author", default="")
    pn.add_argument("--text", default="")
    pn.add_argument("--tags", default="")
    pn.add_argument("--problem", default="")
    pn.add_argument("--query", default="")
    for name in ("estimate", "run", "tower", "agent"):
        p = sub.add_parser(name)
        p.add_argument("--pdk", default=str(DEFAULTS["pdk"]))
        p.add_argument("--chip", default=str(DEFAULTS["chip"]))
        p.add_argument("--rules", default=str(DEFAULTS["rules"]))
        if name in ("run", "tower", "agent"):
            p.add_argument("--out", default=None, help="write report to this file")
            p.add_argument(
                "--mode",
                choices=("foundry", "idm"),
                default=None,
                help="override the chip's business_model (foundry: SRAM fixed at VT0; idm: co-optimize)",
            )
        if name == "tower":
            p.add_argument("--flow", default=str(DEFAULTS["flow"]))
        if name == "agent":
            p.add_argument("--entries", default=str(DEFAULTS["entries"]))
    args = ap.parse_args(argv)
    if args.cmd == "note":
        tags = [t.strip() for t in args.tags.split(",") if t.strip()]
        if args.action == "add":
            note = add_note(args.file, stage=args.stage, kind=args.kind or "comment",
                            author=args.author, text=args.text, tags=tags,
                            problem_ref=args.problem)
            print(render_note(note))
            print("Status: pending — needs approval before it is surfaced.")
        elif args.action == "approve":
            print(render_note(approve_note(args.file, args.id, args.approver)))
        elif args.action == "reject":
            print(render_note(reject_note(args.file, args.id, args.approver,
                                          reason=args.text)))
        elif args.action == "edit":
            note = edit_note(args.file, args.id, args.text, args.approver)
            print(render_note(note))
            print("Status: pending again — edited note needs re-approval.")
        elif args.action == "delete":
            print(render_note(delete_note(args.file, args.id, args.approver)))
        elif args.action == "list":
            found = notes_for_stage(args.file, args.stage, kind=args.kind,
                                    include_pending=args.include_pending)
            print("\n\n".join(render_note(n) for n in found) or "(no notes)")
        elif args.action == "conclusions":
            found = meeting_conclusions(args.file, stage=args.stage,
                                        include_pending=args.include_pending)
            print("\n\n".join(render_note(n) for n in found) or "(no conclusions)")
        else:  # search
            found = search_notes(args.file, args.query, stage=args.stage,
                                 kind=args.kind,
                                 include_pending=args.include_pending)
            print("\n\n".join(render_note(n) for n in found) or "(no matches)")
        return 0
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

    if args.cmd == "agent":
        agent = FoundryProcessAgent(pdk, chip, rules)
        for entry in load_json(args.entries)["entries"]:
            problems = agent.observe(entry)
            for problem in problems:
                print(f"entry problem: {problem}")
        text = render_agent_report(agent.run())
        if args.out:
            Path(args.out).write_text(text, encoding="utf-8")
            print(f"agent report written to {args.out}")
        else:
            print(text)
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
