# Foundry Process Agent report — DemoSoC-1 (synthetic sample customer chip)

Main chip: SoC ASIC
Stages observed: design, tapeout, fab, interposer, wafer_sort, packaging_3d, final_test

## Stage results
- design: DOE PASS
- fab: VT REFIT APPLIED
- packaging_3d: MULTI-DIE GATE: main SoC ASIC + DRAM, HBM, photonics, analog

## Block health
- CPU cluster: GREEN
- GPU / fabric: GREEN
- IO bank: GREEN
- SRAM cache: RED
- PLL: GREEN
- SerDes 112G: GREEN

## Actions
- HOLD SPEC: SRAM cache is foundry-fixed and stays at VT0; remedy is CMOS-side only (LVT center within +/-4.0% of VT0)
- Apply silicon-refit shift rules to the next tape-out (est. error 0.50% -> 0.26%)
