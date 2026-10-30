# APFEA Control Tower Report (prototype v0.2)

- **Program**: DemoSoC-1 rev A (first silicon)
- **Current stage reached**: Final test
- **Program health**: **RED**

## Flow status

- Design: done
- Tape-out: done
- Fabrication: done
- Interposer: done
- Wafer sort: done
- 2.5D/3D packaging: done
- Final test: done
- PCBA: pending
- System: pending

## VT feedback - anticipated vs realized (fab corner-lot readout)

| Flavor | Anticipated shift | Realized shift | Delta (estimator bias) |
|---|---|---|---|
| HVT | +0.00% | +0.31% | +0.31% |
| LVT | -6.00% | -5.29% | +0.71% |
| RVT | +2.00% | +2.40% | +0.40% |
| ULVT | -4.00% | -4.59% | -0.59% |

RMS estimator bias this cycle: 0.53%. Residual estimation error for the next tape-out: 0.50% -> **0.26%** (refit from silicon, floored - calibration shrinks humility, never erases it).

**Refit shift rules for the next tape-out** (config/shift_rules.json values):

- HVT: +0.31%
- LVT: -5.29%
- RVT: +2.40%
- ULVT: -4.59%

## Rev-B margin re-check (refit rules, Part One DOE re-run)

| Block | Flavor | Window | Worst-case dev | Verdict |
|---|---|---|---|---|
| CPU cluster | RVT | 9.0% | 6.9% | PASS |
| GPU / fabric | LVT | 8.0% | 7.2% | PASS |
| SRAM cache (foundry-fixed @VT0 - center check) | LVT | 4.0% | 5.3% | **AT RISK** |
| SerDes 112G | ULVT | 7.5% | 6.9% | PASS |
| PLL | RVT | 8.0% | 6.9% | PASS |
| IO bank | HVT | 10.0% | 6.3% | PASS |

## Block health (downstream data)

- **CPU cluster**: GREEN - wafer-sort yield 99.2%
- **GPU / fabric**: GREEN - wafer-sort yield 98.7%
- **IO bank**: GREEN - wafer-sort yield 99.8%
- **PLL**: GREEN - final test: pass all corners
- **SRAM cache**: RED - wafer-sort yield 91.5%
- **SerDes 112G**: GREEN - final test: pass all corners; eye margin nominal
- note: SRAM fails cluster on low-|VT| corner lots - consistent with the Part One redesign flag.
- note: Timing-sensitive blocks validate the VTs-centered design margins.

## Open actions

- HOLD SPEC: SRAM cache is foundry-fixed and stays at VT0 - silicon yield loss CONFIRMED; remedy is CMOS-side only: pull the LVT silicon center within +/-4.0% of VT0 via CMOS VTs centering and foundry process targeting. Never redesign the fixed block.
- Apply silicon-refit shift rules to the next tape-out (est. error 0.50% -> 0.26%)

_Scope note: the tower observes, attributes, and recommends; it does not actuate fab equipment. Planner-level bookkeeping per APFEA v3 Part Two._
