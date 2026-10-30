"""Tests for the Part Two control tower: feedback math and roll-up."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apfea.doe import evaluate_blocks  # noqa: E402
from apfea.tower import block_health, realized_shifts, refit_rules, tower_status  # noqa: E402
from apfea.vtshift import estimate_vts, load_json  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PDK = load_json(ROOT / "data" / "demo_pdk.json")
CHIP = load_json(ROOT / "data" / "demo_chip.json")
RULES = load_json(ROOT / "config" / "shift_rules.json")
FLOW = load_json(ROOT / "data" / "demo_flow.json")


class TestFeedback(unittest.TestCase):
    def setUp(self):
        self.realized = realized_shifts(PDK, FLOW["vt_measurement"])
        self.updated, self.fb = refit_rules(RULES, self.realized)

    def test_realized_shift_math(self):
        # LVT measured 0.2652 vs VT0 0.280 -> -5.2857...%
        self.assertAlmostEqual(self.realized["LVT"], (0.2652 / 0.280 - 1) * 100, places=4)
        self.assertAlmostEqual(self.realized["RVT"], 2.4, places=4)

    def test_refit_adopts_realized_shifts(self):
        self.assertAlmostEqual(self.updated["base_shift_pct"]["LVT"], -5.29, places=2)
        self.assertAlmostEqual(self.updated["base_shift_pct"]["ULVT"], -4.59, places=2)

    def test_est_err_shrinks_but_floored(self):
        self.assertLess(self.fb["new_est_err_pct"], self.fb["old_est_err_pct"])
        self.assertGreaterEqual(self.fb["new_est_err_pct"], 0.2)

    def test_rev_b_recheck_sram_stays_a_constraint(self):
        # foundry mode: even after refit (LVT -5.29%), the SRAM center
        # tolerance (+/-4.0%) is still exceeded -> constraint persists;
        # redesign list stays empty (SRAM is never a redesign item).
        est_b = estimate_vts(PDK, CHIP, self.updated)
        doe_b = evaluate_blocks(PDK, CHIP, est_b, self.updated)
        self.assertEqual(doe_b["redesign_required"], [])
        self.assertEqual(
            [c["name"] for c in doe_b["constraints_violated"]], ["SRAM cache"]
        )


class TestRollup(unittest.TestCase):
    def setUp(self):
        est = estimate_vts(PDK, CHIP, RULES)
        doe = evaluate_blocks(PDK, CHIP, est, RULES)
        _u, fb = refit_rules(RULES, realized_shifts(PDK, FLOW["vt_measurement"]))
        self.status = tower_status(FLOW, doe, fb)

    def test_sram_red_from_yield(self):
        health = block_health(FLOW)
        self.assertEqual(health["SRAM cache"][0], "RED")
        self.assertEqual(health["SerDes 112G"][0], "GREEN")

    def test_program_health_and_stage(self):
        self.assertEqual(self.status["health"], "RED")
        self.assertEqual(self.status["current_stage"], "Final test")

    def test_sram_action_is_hold_spec_confirmed_by_silicon(self):
        joined = " ".join(self.status["actions"])
        self.assertIn("HOLD SPEC", joined)
        self.assertIn("SRAM cache", joined)
        self.assertIn("CONFIRMED", joined)
        self.assertIn("Never redesign the fixed block", joined)


if __name__ == "__main__":
    unittest.main()
