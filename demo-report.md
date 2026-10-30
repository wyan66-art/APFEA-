# APFEA Pre-Tape-Out Margin Report (prototype v0.2)

- **PDK**: DEMO-PDK (synthetic, 3nm-class values for demonstration only)
- **Customer chip**: DemoSoC-1 (synthetic sample customer chip) - type `soc_large`, die 520 mm^2, specialty devices: serdes, pll
- **Shift rules apply**: yes (chip type gate in config/shift_rules.json)
- **Residual estimation error carried**: 0.50%
- **Business model**: foundry - foundry-fixed blocks (SRAM) keep VT0, spec untouchable; only CMOS VTs change

## Step I - Anticipated VTs (CMOS designs against VTs, not VT0)

| Flavor | Pol | VT0 (V) | Shift | VTs (V) | sigma (% of \|VT\|) |
|---|---|---|---|---|---|
| HVT | N | +0.420 | +0.0% | +0.4200 | 2.0 |
| HVT | P | -0.400 | +0.0% | -0.4000 | 2.0 |
| LVT | N | +0.280 | -6.0% | +0.2632 | 2.3 |
| LVT | P | -0.260 | -6.0% | -0.2444 | 2.3 |
| RVT | N | +0.350 | +2.0% | +0.3570 | 2.2 |
| RVT | P | -0.330 | +2.0% | -0.3366 | 2.2 |
| ULVT | N | +0.220 | -4.0% | +0.2112 | 2.2 |
| ULVT | P | -0.200 | -4.0% | -0.1920 | 2.2 |

Foundry-fixed blocks (e.g. SRAM) are NOT shifted: they keep VT0 as their design point, exactly as the foundry supplies them. VTs apply to the customer's CMOS design only.

## Silicon corner splits around VTs (|VT|, N devices, CMOS flavors)

| Flavor | -3sigma | -2sigma | -1sigma | +0sigma | +1sigma | +2sigma | +3sigma |
|---|---|---|---|---|---|---|---|
| HVT | 0.3948 | 0.4032 | 0.4116 | 0.4200 | 0.4284 | 0.4368 | 0.4452 |
| LVT | 0.2450 | 0.2511 | 0.2571 | 0.2632 | 0.2693 | 0.2753 | 0.2814 |
| RVT | 0.3334 | 0.3413 | 0.3491 | 0.3570 | 0.3649 | 0.3727 | 0.3806 |
| ULVT | 0.1973 | 0.2019 | 0.2066 | 0.2112 | 0.2158 | 0.2205 | 0.2251 |

## Step II - Block checks

### Customer CMOS blocks (worst-case deviation vs block window)

| Block | Flavor | Window | Conv. flow dev | Conv. | APFEA flow dev | APFEA |
|---|---|---|---|---|---|---|
| CPU cluster | RVT | 9.0% | 8.6% | PASS | 7.1% | PASS |
| GPU / fabric | LVT | 8.0% | 12.9% | **AT RISK** | 7.4% | PASS |
| SerDes 112G | ULVT | 7.5% | 10.6% | **AT RISK** | 7.1% | PASS |
| PLL | RVT | 8.0% | 8.6% | **AT RISK** | 7.1% | PASS |
| IO bank | HVT | 10.0% | 6.0% | PASS | 6.5% | PASS |

Conventional flow designs against VT0, so silicon deviates from the design center by |shift| + 3 sigma in the worst case. The APFEA flow designs against VTs, leaving only 3 sigma + residual estimation error.

### Foundry-fixed blocks (design point stays at VT0 - spec untouchable)

| Block | Flavor | Center tolerance | Anticipated center shift | Check |
|---|---|---|---|---|
| SRAM cache | LVT | +/-4.0% | -6.0% | **AT RISK** |

The conventional flow never performs this check before tape-out; APFEA performs it in Step II. A violated constraint is remedied on the CMOS side only - design centering, flavor strategy, process targeting with the foundry. The fixed block's spec is never an action item.

## Verdict

- CMOS blocks at risk under the conventional (VT0) flow: **3 / 5** - each is a mask-fix re-tape-out exposure.
- CMOS blocks at risk under the APFEA (VTs) flow: **0 / 5**.
- **Foundry-fixed constraint violated**: SRAM cache (LVT) - anticipated center shift -6.0% exceeds its +/-4.0% tolerance around VT0. HOLD THE SPEC: SRAM cache stays at VT0; pull the LVT center back via CMOS-side centering and foundry process targeting.
- **VTs1 for silicon corner lots**: VTs (anticipated true center from step I). Use VTs as the center for real silicon corner-lot splits, subject to the foundry-fixed block constraints: the remedy for a violated constraint is CMOS-side (design centering, flavor strategy, process targeting with the foundry) - the fixed block's spec is never touched.

_Scope note: planner-level margin bookkeeping per APFEA v3 Part One. No circuit simulation is run; block windows, tolerances and shift rules are configuration to be fitted from each foundry/design-house pair's own history._
