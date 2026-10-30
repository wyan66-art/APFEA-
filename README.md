# APFEA — AI-assisted Phenomenological Foundry Engineering Approach

**One-liner: eliminate yield-driven mask re-tapeouts.**

APFEA is a foundry process-flow approach for advanced chip design
(SoC, FPGA, AI, large ASIC, system chips), by Winston Y Yan (Apollo AI).
The full chain is the spine: design → tape-out → fab → interposer →
wafer sort → 2.5D/3D packaging → final test → PCBA → system, with an
AI agentic (AGT) control tower closing feedback loops from downstream
data back into design.

This repository contains a working computational core (stdlib-only
Python), not a production EDA tool. Demo data is synthetic; a real
engagement replaces it with the pair's own PDK extract and chip profile.

## The core idea (v3, March 2026)

Design to anticipated threshold voltages, not to the PDK nominal:

1. **Pre-emptive strike.** Estimate **VTs = VT0 ± x%** from the
   differences between the foundry PDK test chip and the customer chip
   to be designed, plus historical data. Seeded example (fabric/SoC):
   RVT +2%, LVT −6%, ULVT −4%, acting on |VT|.
2. **Pre-tape-out corner DOE.** After design, before tape-out / GDS
   transfer, simulate functional blocks (each treated as a single chip)
   and the whole chip against real silicon corner-lot splits
   (**VTs ± 3σ**, the same splits as a silicon corner lot). Fix any
   block that fails. If the DOE yields a new VT set, call it VTs1 and
   use it for the real silicon corner-lot splits.
3. **Silicon corner-lot stress test.** Verify the chip and catch
   design-margin issues early in product qualification.

If a block's window is narrower than the 3σ spread itself, the tool
says **redesign** — re-centering cannot fix physics.

## Business-model rule (author's ruling, 2026-10-20)

What may be adjusted follows the boundary of ownership:

- **Foundry mode** (`--mode foundry`): SRAM is a foundry-fixed macro —
  identical for every customer, spec untouchable, design point stays
  at VT0. It enters the DOE as a *constraint* (anticipated flavor
  center shift vs. its ±tolerance around VT0); remedy is CMOS-side
  only (CMOS centering, flavor strategy, process targeting).
  SRAM is never a redesign action.
- **IDM mode** (`--mode idm`): one owner for design + fab, SRAM
  included — VTs are co-optimized for CMOS and SRAM together, and
  SRAM may legitimately be redesigned / co-optimized.

## Run it

```bash
python3 -m apfea estimate           # Step I table only
python3 -m apfea run                # full report to stdout
python3 -m apfea run --out rpt.md   # full report to file
python3 -m apfea tower              # control-tower report
python3 -m apfea agent              # Foundry Process Agent report (v0.3)
python3 -m unittest discover -s tests   # 23 tests, stdlib only
```

Zero dependencies: Python 3 standard library only.

## Layout

```
apfea/            vtshift.py · doe.py · report.py · tower.py · cli.py
config/           shift_rules.json   (phenomenology as data)
data/             demo_pdk.json · demo_chip.json · demo_flow.json (synthetic)
tests/            test_apfea.py · test_tower.py
demo-report.md / demo-report-idm.md / tower-report.md   (generated demo output)
```

## Foundry Process Agent (v0.3)

`apfea/stages.py` defines the 9 flow stages as entries, each with
input / output / recorded / gate / feedback. `apfea/agent.py` runs
the loop: observe an entry → reason (DOE, VT refit, yield health) →
act (actions, gates, report) → learn (refit rules for the next
tape-out). Main chip is a SoC ASIC; the 2.5D/3D packaging stage
integrates companion dies (DRAM/HBM, photonics, analog, etc.) on an
interposer via TSVs. The agent is planner level only: it observes,
attributes, and recommends — it does not actuate a fab. Demo:
`python -m apfea agent` (see `agent-report.md`).

## Control tower (Part Two)

The tower models the full foundry process flow and closes two feedback
loops back into design:

- **VT feedback:** the fab corner-lot readout gives the realized VT
  center per flavor; realized vs. anticipated shift yields the
  estimator's measured bias, and the shift rules are refit from silicon
  for the next tape-out.
- **Yield feedback:** wafer-sort / final-test results roll up into
  per-block health; a Part One redesign flag that silicon then
  confirms is escalated as an evidence-backed action.

## Roadmap (not yet built)

- Estimator fitting from historical test-chip / customer-chip pairs
  (least-squares over past tape-outs) instead of static rules.
- Optional SPICE-deck export of the corner splits for block-level DOE.

## Status, authorship and use

This project was proposed and written solely by Winston Y Yan during a
period between jobs, with no association with any company, firm,
government organization or other individual. It is released free of
charge to US semiconductor companies for technology advancement and
social benefit, as a defensive publication: no individual, company or
firm may use its content, in part or in full, to be patented.
