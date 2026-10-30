"""Tests for per-node human comments / meeting conclusions (2026-10-30).

Approval gate (Winston, 2026-10-30): nothing is added, changed, or
deleted arbitrarily. A new note is PENDING and is not surfaced until
an approver approves it; edits and deletions both require an
approver; an edit returns the note to PENDING for re-approval, with
the old text kept in history.
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apfea.comments import (add_note, approve_note, delete_note,  # noqa: E402
                            edit_note, load_notes, meeting_conclusions,
                            notes_for_stage, reject_note, search_notes)
from apfea.stages import validate_entry  # noqa: E402


class TestNodeComments(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "stage_comments.json"

    def tearDown(self):
        self.tmp.cleanup()

    def _approved(self, **kw):
        note = add_note(self.path, **kw)
        return approve_note(self.path, note["id"], approver="Approver")

    def test_add_is_pending_until_approved(self):
        note = add_note(self.path, stage="fab", kind="comment", author="W. Yan",
                        text="Not yet approved.")
        self.assertEqual(note["status"], "pending")
        self.assertEqual(notes_for_stage(self.path, "fab"), [])
        self.assertEqual(notes_for_stage(self.path, "fab", include_pending=True),
                         [note])
        approve_note(self.path, note["id"], approver="Approver")
        self.assertEqual(len(notes_for_stage(self.path, "fab")), 1)

    def test_add_and_list_by_stage(self):
        self._approved(stage="fab", kind="comment", author="W. Yan",
                       text="Corner lot readout late by one day, WAT still complete.",
                       problem_ref="lot-12")
        self._approved(stage="fab", kind="meeting_conclusion", author="W. Yan",
                       text="Meeting conclusion: refit VT rules from realized silicon, do not re-tapeout yet.",
                       tags=["VT", "refit"], problem_ref="LVT")
        notes = notes_for_stage(self.path, "fab")
        self.assertEqual(len(notes), 2)
        self.assertEqual(meeting_conclusions(self.path, "fab")[0]["kind"],
                         "meeting_conclusion")

    def test_search_finds_prior_conclusion_by_block(self):
        self._approved(stage="wafer_sort", kind="meeting_conclusion",
                       author="W. Yan",
                       text="SerDes sort yield dip traced to VT shift, not to package.",
                       problem_ref="SerDes 112G")
        found = search_notes(self.path, "SerDes")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["problem_ref"], "SerDes 112G")

    def test_unknown_stage_or_kind_rejected(self):
        with self.assertRaises(ValueError):
            add_note(self.path, stage="no_such_stage", kind="comment",
                     author="W. Yan", text="x")
        with self.assertRaises(ValueError):
            add_note(self.path, stage="fab", kind="gossip",
                     author="W. Yan", text="x")

    def test_edit_and_delete_require_approver(self):
        note = self._approved(stage="fab", kind="comment", author="W. Yan",
                              text="Original.")
        with self.assertRaises(ValueError):
            edit_note(self.path, note["id"], "Changed.", approver="")
        with self.assertRaises(ValueError):
            delete_note(self.path, note["id"], approver="")
        # With an approver, an edit is auditable and goes back to pending.
        edited = edit_note(self.path, note["id"], "Changed.", approver="Approver")
        self.assertEqual(edited["status"], "pending")
        self.assertEqual(edited["text"], "Changed.")
        self.assertEqual(notes_for_stage(self.path, "fab"), [])
        self.assertIn("Original.", edited["history"][-1]["old_text"])
        approve_note(self.path, note["id"], approver="Approver")
        self.assertEqual(notes_for_stage(self.path, "fab")[0]["text"], "Changed.")
        # Deletion keeps the record but stops surfacing it.
        delete_note(self.path, note["id"], approver="Approver")
        self.assertEqual(notes_for_stage(self.path, "fab"), [])
        self.assertEqual(load_notes(self.path)[0]["status"], "deleted")

    def test_reject_keeps_note_unsurfaced(self):
        note = add_note(self.path, stage="fab", kind="comment", author="W. Yan",
                        text="Rejected note.")
        reject_note(self.path, note["id"], approver="Approver",
                    reason="Not verified.")
        self.assertEqual(notes_for_stage(self.path, "fab"), [])

    def test_notes_do_not_change_entry_validation(self):
        entry = {"stage": "fab", "input": "GDS", "output": "wafers",
                 "recorded": "VT centers", "gate": "readout complete",
                 "feedback": "design"}
        self.assertEqual(validate_entry(entry), [])
        self._approved(stage="fab", kind="comment", author="W. Yan",
                       text="A note must never make an invalid entry valid.")
        self.assertEqual(validate_entry(entry), [])

    def test_notes_persist_across_loads(self):
        self._approved(stage="final_test", kind="lesson_learned",
                       author="W. Yan",
                       text="Final-test failure first: check sort, then package.")
        self.assertEqual(len(load_notes(self.path)), 1)


if __name__ == "__main__":
    unittest.main()
