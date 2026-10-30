import unittest
from pathlib import Path

from apfea.agent import FoundryProcessAgent, render_agent_report
from apfea.stages import (
    COMPANION_KINDS,
    ENTRY_FIELDS,
    STAGE_KEYS,
    STAGE_SCHEMA,
    validate_entry,
)
from apfea.vtshift import load_json

ROOT = Path(__file__).resolve().parent.parent


class TestStages(unittest.TestCase):
    def test_nine_stages_in_flow_order(self):
        self.assertEqual(
            STAGE_KEYS,
            ["design", "tapeout", "fab", "interposer", "wafer_sort",
             "packaging_3d", "final_test", "pcba", "system"],
        )

    def test_every_stage_schema_has_all_entry_fields(self):
        for stage in STAGE_SCHEMA:
            for field in ENTRY_FIELDS:
                self.assertTrue(stage[field], f"{stage['key']}.{field}")

    def test_packaging_requires_companion_dies(self):
        base = {f: "x" for f in ENTRY_FIELDS}
        base["stage"] = "packaging_3d"
        self.assertTrue(validate_entry(base))  # no companions
        good = dict(base, companion_dies=[{"kind": "HBM"}])
        self.assertEqual(validate_entry(good), [])
        bad = dict(base, companion_dies=[{"kind": "mystery"}])
        self.assertTrue(validate_entry(bad))

    def test_companion_kinds_cover_user_list(self):
        for kind in ("DRAM", "HBM", "photonics", "analog"):
            self.assertIn(kind, COMPANION_KINDS)


class TestAgent(unittest.TestCase):
    def setUp(self):
        self.pdk = load_json(ROOT / "data" / "demo_pdk.json")
        self.chip = load_json(ROOT / "data" / "demo_chip.json")
        self.rules = load_json(ROOT / "config" / "shift_rules.json")
        self.entries = load_json(ROOT / "data" / "demo_stage_entries.json")["entries"]

    def test_agent_runs_demo_flow(self):
        agent = FoundryProcessAgent(self.pdk, self.chip, self.rules)
        for entry in self.entries:
            self.assertEqual(agent.observe(entry), [])
        result = agent.run()
        self.assertEqual(result["main_chip"], "SoC ASIC")
        self.assertIn("packaging_3d", result["stages_seen"])
        self.assertIn("MULTI-DIE GATE", result["stage_results"]["packaging_3d"])
        self.assertIn("HBM", result["stage_results"]["packaging_3d"])
        self.assertIsNotNone(result["feedback"])  # fab VT refit applied
        self.assertTrue(result["actions"])
        report = render_agent_report(result)
        self.assertIn("Foundry Process Agent report", report)
        self.assertIn("SoC ASIC", report)


if __name__ == "__main__":
    unittest.main()
