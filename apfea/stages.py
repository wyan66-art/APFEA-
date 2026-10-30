"""Step-by-step Foundry Process Flow schematics, with entries.

Each stage is an *entry*, not just a name. An entry is the unit the
Foundry Process Agent observes: what arrives, what leaves, what data
is recorded, what gate must pass, and which earlier stage its data
feeds back into. Without entries, the tower can only say which stage
a program reached; with entries, it can say why it may proceed.

Scope assumptions (Winston, 2026-10-29):
- Main chip: a SoC ASIC (demo: DemoSoC-1, CPU cluster, GPU/fabric,
  SRAM cache, SerDes 112G, PLL, IO bank).
- 2.5D/3D packaging is heterogeneous integration: the SoC ASIC plus
  companion dies (DRAM/HBM, photonics, analog, etc.) on an interposer
  via TSVs. Companion dies are NOT redesigned through the main
  chip's VTs; each keeps its own process and sensitivities.
"""
from __future__ import annotations

ENTRY_FIELDS = ("input", "output", "recorded", "gate", "feedback")

# Companion-die kinds the packaging stage must list explicitly.
COMPANION_KINDS = ("DRAM", "HBM", "photonics", "analog")

STAGE_SCHEMA = [
    {
        "key": "design",
        "name": "Design",
        "input": "PDK VT0 per flavor/polarity, customer SoC ASIC profile "
                 "(size, fabric, specialty devices)",
        "output": "SoC ASIC design at anticipated VTs (VTs = VT0 +/- x%)",
        "recorded": "VTs per flavor, shift rules used, block VT windows",
        "gate": "Part One DOE at VTs +/- 3 sigma passes, or blocks are "
                "flagged for redesign before tape-out",
        "feedback": "none yet; this stage is the prediction to be checked "
                    "by silicon",
    },
    {
        "key": "tapeout",
        "name": "Tape-out",
        "input": "GDS, VTs set, Part One DOE report, VTs1 if the DOE "
                 "produced one",
        "output": "Mask order, GDS transferred to the foundry",
        "recorded": "GDS version, VTs/VTs1 actually taped out, DOE sign-off",
        "gate": "DOE sign-off present; no unflagged block at risk",
        "feedback": "design",
    },
    {
        "key": "fab",
        "name": "Fabrication",
        "input": "GDS, VTs/VTs1, lot plan, recipes",
        "output": "Wafers, corner-lot readout, WAT data",
        "recorded": "realized VT center per flavor, lot IDs, process data",
        "gate": "corner-lot readout complete for all flavors",
        "feedback": "design (VT shift rules are refit from realized silicon)",
    },
    {
        "key": "interposer",
        "name": "Interposer",
        "input": "SoC ASIC die, companion dies, interposer layout, TSV plan",
        "output": "Interposer with TSVs routed for main + companion dies",
        "recorded": "interposer layout version, TSV map, die placement",
        "gate": "TSV/interposer layout passes design rules for every die",
        "feedback": "design (placement or TSV constraints that force a "
                    "re-spin are reported back, not silently absorbed)",
    },
    {
        "key": "wafer_sort",
        "name": "Wafer sort",
        "input": "Fabricated wafers, sort test program",
        "output": "Known-good dies, per-block sort yields",
        "recorded": "per-block yields, failing blocks, sort notes",
        "gate": "sort yields meet the program target, or failing blocks "
                "are escalated as evidence-backed actions",
        "feedback": "design (a Part One flag confirmed by sort yield is "
                    "escalated, not re-argued)",
    },
    {
        "key": "packaging_3d",
        "name": "2.5D/3D packaging",
        "input": "SoC ASIC main die + companion dies (DRAM/HBM, photonics, "
                 "analog, etc.), interposer, thermal plan",
        "output": "Packaged heterogeneous system: main die + companion dies "
                 "on interposer via TSVs",
        "recorded": "companion dies actually integrated, thermal dispersion "
                 "data, package yield",
        "gate": "co-test passes for main + companion dies; thermal "
                 "dispersion within plan",
        "feedback": "design and interposer (thermal or co-test failures "
                    "feed back to placement and, where owned, to design)",
    },
    {
        "key": "final_test",
        "name": "Final test",
        "input": "Packaged systems, final-test program",
        "output": "Pass/fail per packaged system, per-block test results",
        "recorded": "per-block final-test results, system-level failures",
        "gate": "final-test pass rate meets target, or failures are "
                "attributed to a stage, not left unattributed",
        "feedback": "wafer_sort and packaging_3d (final-test failures are "
                    "traced back to sort or package, not to design alone)",
    },
    {
        "key": "pcba",
        "name": "PCBA",
        "input": "Packaged systems, board design, assembly plan",
        "output": "Assembled boards with the packaged system mounted",
        "recorded": "board assembly yield, assembly defects",
        "gate": "assembly yield meets target",
        "feedback": "packaging_3d (assembly defects traceable to the package "
                    "are reported back to packaging)",
    },
    {
        "key": "system",
        "name": "System",
        "input": "Assembled boards, system test / rack plan",
        "output": "Qualified system, system-test results",
        "recorded": "system-test results, field-relevant failures",
        "gate": "system test passes; product qualification can proceed",
        "feedback": "design (system-level failures close the loop: the next "
                    "tape-out starts from what silicon and system "
                    "actually showed)",
    },
]

STAGE_KEYS = [s["key"] for s in STAGE_SCHEMA]
STAGE_BY_KEY = {s["key"]: s for s in STAGE_SCHEMA}


def validate_entry(entry: dict) -> list[str]:
    """Return a list of problems with a stage entry; empty means valid.

    A valid entry names a known stage and fills every ENTRY_FIELD,
    plus, for the packaging stage, lists at least one companion die
    with a kind from COMPANION_KINDS.
    """
    problems = []
    key = entry.get("stage")
    if key not in STAGE_BY_KEY:
        return [f"unknown stage: {key!r}"]
    for field in ENTRY_FIELDS:
        if not entry.get(field):
            problems.append(f"{key}: missing entry field {field!r}")
    if key == "packaging_3d":
        companions = entry.get("companion_dies") or []
        kinds = [c.get("kind") for c in companions if isinstance(c, dict)]
        if not companions:
            problems.append("packaging_3d: no companion dies listed")
        for kind in kinds:
            if kind not in COMPANION_KINDS:
                problems.append(f"packaging_3d: unknown companion kind {kind!r}")
    return problems
