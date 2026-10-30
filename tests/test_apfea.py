"""Unit tests - runnable with the stdlib only:  python -m unittest discover -s tests
Key checks: the estimator reproduces the APFEA v3 worked example, and the
demo DOE tells the v3 story (VT0 flow leaves blocks at risk; VTs flow
clears all but the honestly-unfixable SRAM window)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apfea.doe import evaluate_blocks  # noqa: E402
from apfea.vtshift import estimate_vts, load_json  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PDK = load_json(ROOT / "data" / "demo_pdk.json")
CHIP = load_json(ROOT / "data" / "demo_chip.json")
RULES = load_json(ROOT / "config" / "shift_rules.json")


class TestEstimator(unittest.TestCase):
    def setUp(self):
        self.est = estimate_vts(PDK, CHIP, RULES)
        self.by = {(r["flavor"], r["polarity"]): r for r in self.est["rows"]}

    def test_rules_apply_to_soc(self):
        self.assertTrue(self.est["rules_apply"])

    def test_v3_example_numbers(self):
        # v3: RVT0+2%, LVT0-6%, ULVT0-4% acting on |VT|
        self.assertAlmostEqual(self.by[("RVT", "N")]["vts"], 0.350 * 1.02, places=6)
        self.assertAlmostEqual(self.by[("LVT", "N")]["vts"], 0.280 * 0.94, places=6)
        self.assertAlmostEqual(self.by[("ULVT", "N")]["vts"], 0.220 * 0.96, places=6)

    def test_pmos_sign_preserved_magnitude_shifted(self):
        r = self.by[("LVT", "P")]
        self.assertLess(r["vts"], 0)
        self.assertAlmostEqual(abs(r["vts"]), 0.260 * 0.94, places=6)

    def test_zero_shift_flavor_unchanged(self):
        self.assertAlmostEqual(self.by[("HVT", "N")]["vts"], 0.420, places=6)

    def test_gate_blocks_rules_for_plain_test_chip(self):
        chip = dict(CHIP, chip_type="test_chip")
        est = estimate_vts(PDK, chip, RULES)
        self.assertFalse(est["rules_apply"])
        self.assertTrue(all(r["shift_pct"] == 0.0 for r in est["rows"]))


class TestDOE(unittest.TestCase):
    def setUp(self):
        est = estimate_vts(PDK, CHIP, RULES)
        self.doe = evaluate_blocks(PDK, CHIP, est, RULES)
        self.by = {b["name"]: b for b in self.doe["blocks"]}

    def test_conventional_flow_exposes_serdes(self):
        # v3 issue I: VT shift hits timing-sensitive blocks -> re-tapeout
        self.assertFalse(self.by["SerDes 112G"]["conv_pass"])
        self.assertFalse(self.by["GPU / fabric"]["conv_pass"])

    def test_apfea_flow_clears_shift_caused_risks(self):
        for name in ("SerDes 112G", "GPU / fabric", "PLL", "CPU cluster", "IO bank"):
            self.assertTrue(self.by[name]["apfea_pass"], name)

    def test_sram_is_constraint_never_redesign_in_foundry_mode(self):
        # Author's rule (2026-10-20): foundry SRAM is fixed for every
        # customer, spec untouchable, keeps VT0. Anticipated LVT shift
        # |-6.0%| exceeds its +/-4.0% center tolerance -> constraint
        # violated; it must NOT appear as a redesign action.
        self.assertEqual(self.doe["redesign_required"], [])
        names = [c["name"] for c in self.doe["constraints_violated"]]
        self.assertEqual(names, ["SRAM cache"])
        sram = self.by["SRAM cache"]
        self.assertTrue(sram["fixed"])
        self.assertFalse(sram["apfea_pass"])


class TestDOEIdmMode(unittest.TestCase):
    """IDM: one owner for design + fab, so VTs co-optimize CMOS + SRAM."""

    def setUp(self):
        chip = dict(CHIP, business_model="idm")
        est = estimate_vts(PDK, chip, RULES)
        self.doe = evaluate_blocks(PDK, chip, est, RULES)
        self.by = {b["name"]: b for b in self.doe["blocks"]}

    def test_sram_designed_at_vts_and_co_optimizable(self):
        sram = self.by["SRAM cache"]
        self.assertFalse(sram["fixed"])
        self.assertTrue(sram["co_optimizable"])
        self.assertEqual(self.doe["constraints_violated"], [])

    def test_sram_margin_failure_is_a_cooptimize_action(self):
        # window 6.0% < APFEA dev 7.4% -> legitimate redesign/co-optimize
        # action in IDM mode (the spec is ours to move).
        self.assertFalse(self.by["SRAM cache"]["apfea_pass"])
        self.assertEqual(self.doe["redesign_required"], ["SRAM cache"])

    def test_apfea_deviation_is_pure_spread_plus_error(self):
        b = self.by["SerDes 112G"]
        self.assertAlmostEqual(
            b["apfea_worst_dev_pct"], 3 * b["sigma_pct"] + self.doe["est_err_pct"], places=6
        )
        self.assertAlmostEqual(
            b["conv_worst_dev_pct"],
            abs(b["shift_pct"]) + 3 * b["sigma_pct"],
            places=6,
        )


if __name__ == "__main__":
    unittest.main()
