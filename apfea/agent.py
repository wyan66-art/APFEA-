"""Foundry Process Agent (planner level, v0.3).

The agent runs one loop over the Foundry Process Flow entries:

    observe (stage entry) -> reason (DOE / VT refit / yield health)
    -> act (actions, gates, report) -> learn (refit rules for the
    next tape-out)

It observes, attributes, and recommends. It does NOT actuate a fab:
it changes no recipe, no equipment setting, and no tape-out decision.
A human (design house / foundry tech manager) makes the decision;
the agent makes the evidence for it legible.

Scope: main chip is a SoC ASIC; the packaging stage integrates
companion dies (DRAM/HBM, photonics, analog, etc.) on an interposer.
Demo data is synthetic.
"""
from __future__ import annotations

from .doe import evaluate_blocks
from .stages import STAGE_KEYS, STAGE_SCHEMA, validate_entry
from .tower import block_health, realized_shifts, refit_rules
from .vtshift import estimate_vts


class FoundryProcessAgent:
    """Stateful agent over one program's stage entries."""

    def __init__(self, pdk: dict, chip: dict, rules: dict):
        self.pdk = pdk
        self.chip = chip
        self.rules = rules
        self.entries: dict[str, dict] = {}
        self.problems: list[str] = []

    def observe(self, entry: dict) -> list[str]:
        """Record one stage entry; return its validation problems."""
        problems = validate_entry(entry)
        self.problems.extend(problems)
        if not problems:
            self.entries[entry["stage"]] = entry
        return problems

    def run(self) -> dict:
        """Reason over all observed entries and return the agent report."""
        est = estimate_vts(self.pdk, self.chip, self.rules)
        doe = evaluate_blocks(self.pdk, self.chip, est, self.rules)
        actions: list[str] = []
        stage_results: dict[str, str] = {}
        feedback = None
        updated_rules = self.rules

        # Design gate: Part One DOE.
        if doe["redesign_required"]:
            actions.append(
                "REDESIGN before tape-out: "
                + ", ".join(doe["redesign_required"])
            )
        if doe["constraints_violated"]:
            for c in doe["constraints_violated"]:
                actions.append(
                    f"HOLD SPEC: {c['name']} is foundry-fixed and stays "
                    f"at VT0; remedy is CMOS-side only ({c['flavor']} "
                    f"center within +/-{c['center_tol_pct']:.1f}% of VT0)"
                )
        stage_results["design"] = (
            "GATE BLOCKED" if doe["redesign_required"] else "DOE PASS"
        )

        # Fab: VT feedback / refit from silicon.
        fab = self.entries.get("fab", {})
        if fab.get("vt_measurement"):
            realized = realized_shifts(self.pdk, fab["vt_measurement"])
            updated_rules, feedback = refit_rules(self.rules, realized)
            actions.append(
                "Apply silicon-refit shift rules to the next tape-out "
                f"(est. error {feedback['old_est_err_pct']:.2f}% -> "
                f"{feedback['new_est_err_pct']:.2f}%)"
            )
            stage_results["fab"] = "VT REFIT APPLIED"
        elif "fab" in self.entries:
            stage_results["fab"] = "OBSERVED, no VT measurement"

        # Packaging: heterogeneous integration gate.
        pkg = self.entries.get("packaging_3d", {})
        if pkg:
            kinds = [c["kind"] for c in pkg.get("companion_dies", [])]
            stage_results["packaging_3d"] = (
                "MULTI-DIE GATE: main SoC ASIC + " + ", ".join(kinds)
            )
            if pkg.get("thermal_within_plan") is False:
                actions.append(
                    "THERMAL: packaging thermal dispersion out of plan; "
                    "feed back to interposer placement before system test"
                )

        # Yield health from wafer-sort / final-test observations.
        flow = {"observations": []}
        for key in ("wafer_sort", "final_test"):
            entry = self.entries.get(key, {})
            for obs in entry.get("observations", []):
                flow["observations"].append(obs)
        health = block_health(flow)
        block_status = {k: v for k, v in health.items()
                        if not k.startswith("_")}
        for name, (status, detail) in block_status.items():
            if status == "RED" and name in doe["redesign_required"]:
                actions.append(
                    f"REDESIGN {name} CONFIRMED by silicon data ({detail})"
                )

        seen = [k for k in STAGE_KEYS if k in self.entries]
        return {
            "program": self.chip.get("name", "unnamed program"),
            "main_chip": "SoC ASIC",
            "stages_seen": seen,
            "stage_results": stage_results,
            "block_health": {k: v[0] for k, v in block_status.items()},
            "actions": actions,
            "feedback": feedback,
            "updated_rules": updated_rules,
            "entry_problems": self.problems,
            "schema": STAGE_SCHEMA,
        }


def render_agent_report(result: dict) -> str:
    """Render the agent report as Markdown."""
    lines = [
        f"# Foundry Process Agent report — {result['program']}",
        "",
        f"Main chip: {result['main_chip']}",
        f"Stages observed: {', '.join(result['stages_seen']) or 'none'}",
        "",
        "## Stage results",
    ]
    for key, value in result["stage_results"].items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Block health")
    for name, status in result["block_health"].items():
        lines.append(f"- {name}: {status}")
    if not result["block_health"]:
        lines.append("- (no wafer-sort / final-test observations yet)")
    lines.append("")
    lines.append("## Actions")
    for action in result["actions"]:
        lines.append(f"- {action}")
    if not result["actions"]:
        lines.append("- (no actions)")
    if result["entry_problems"]:
        lines.append("")
        lines.append("## Entry problems")
        for problem in result["entry_problems"]:
            lines.append(f"- {problem}")
    return "\n".join(lines) + "\n"
