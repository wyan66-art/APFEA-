"""Human notes attached to Foundry Process Flow nodes.

Winston, 2026-10-30: every node (stage) must accept human-added
comments and meeting conclusions, so that later chip-problem analysis
can find what people already decided, not just what the data recorded.

Design rules (deliberate, to keep human notes from corrupting the
machine record):
- Notes attach to a node; they do NOT change ENTRY_FIELDS, gates,
  VT calculations, or any recorded measurement. A stage entry still
  validates exactly as before. Notes are evidence the agent surfaces,
  never a silent override of a gate.
- APPROVAL GATE (Winston, 2026-10-30): nothing is added, changed,
  or deleted arbitrarily.
  * add_note() only creates a PENDING note. It is stored, but it is
    NOT surfaced by list/search/meeting-conclusions, which return
    approved notes only (unless include_pending=True is asked for
    explicitly, e.g. by a reviewer).
  * approve_note() / reject_note() require an approver name, and
    record approver + time in the note's history. Only an approved
    note is live for chip-problem analysis.
  * edit_note() and delete_note() both REQUIRE an approver name;
    without one they raise ValueError and change nothing. An edit
    is recorded in history (old text kept) and the edited note
    returns to PENDING until re-approved — an approver cannot
    silently rewrite a note that others already relied on.
  * Deletion does not erase history: the note is marked deleted,
    with deleter + approver recorded, and it stops being surfaced.
    The audit trail stays in the file.
- A note carries: stage, kind, author, text, tags, and an optional
  problem_ref (chip / lot / block, e.g. "SerDes 112G") so that a later
  failure on the same block can retrieve the earlier discussion.
- Kinds: "comment" (general note), "meeting_conclusion" (a decision
  or conclusion reached in a meeting), "decision", "lesson_learned".
- Storage is a plain JSON list, one file, so notes survive across
  runs and can be grepped, backed up, or moved with the project.
  Default file: data/stage_comments.json under the prototype root.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .stages import STAGE_BY_KEY

KINDS = ("comment", "meeting_conclusion", "decision", "lesson_learned")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_notes(path: str | Path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"notes file must hold a JSON list: {path}")
    return data


def save_notes(path: str | Path, notes: list[dict]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(notes, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def add_note(path: str | Path, *, stage: str, kind: str, author: str,
             text: str, tags: list[str] | None = None,
             problem_ref: str = "") -> dict:
    """Append one human note to a node; return the stored note.

    Raises ValueError for an unknown stage, an unknown kind, or an
    empty author/text, so a typo cannot file a note under a node
    that does not exist.
    """
    if stage not in STAGE_BY_KEY:
        raise ValueError(f"unknown stage: {stage!r}")
    if kind not in KINDS:
        raise ValueError(f"unknown note kind: {kind!r} (expected one of {KINDS})")
    if not author.strip() or not text.strip():
        raise ValueError("note needs a non-empty author and text")
    notes = load_notes(path)
    note = {
        "id": len(notes) + 1,
        "stage": stage,
        "kind": kind,
        "author": author.strip(),
        "text": text.strip(),
        "tags": list(tags or []),
        "problem_ref": problem_ref.strip(),
        "created_at": _now_iso(),
        # Approval gate: a new note is PENDING, not live, until an
        # approver approves it (see approve_note).
        "status": "pending",
        "approved_by": "",
        "approved_at": "",
        "history": [{"at": _now_iso(), "action": "created",
                     "by": author.strip()}],
    }
    notes.append(note)
    save_notes(path, notes)
    return note


def _find(notes: list[dict], note_id: int) -> dict:
    for n in notes:
        if n["id"] == note_id:
            return n
    raise ValueError(f"no note with id {note_id}")


def _require_approver(approver: str) -> str:
    approver = (approver or "").strip()
    if not approver:
        raise ValueError("this action requires approval: pass an approver name")
    return approver


def approve_note(path: str | Path, note_id: int, approver: str) -> dict:
    notes = load_notes(path)
    note = _find(notes, note_id)
    approver = _require_approver(approver)
    note["status"] = "approved"
    note["approved_by"] = approver
    note["approved_at"] = _now_iso()
    note.setdefault("history", []).append(
        {"at": note["approved_at"], "action": "approved", "by": approver})
    save_notes(path, notes)
    return note


def reject_note(path: str | Path, note_id: int, approver: str,
                reason: str = "") -> dict:
    notes = load_notes(path)
    note = _find(notes, note_id)
    approver = _require_approver(approver)
    note["status"] = "rejected"
    note.setdefault("history", []).append(
        {"at": _now_iso(), "action": "rejected", "by": approver,
         "reason": reason.strip()})
    save_notes(path, notes)
    return note


def edit_note(path: str | Path, note_id: int, new_text: str,
              approver: str) -> dict:
    """Edit only with an approver; the edited note goes back to PENDING.

    The old text is kept in history, so an edit is auditable and
    cannot silently rewrite a note others relied on.
    """
    notes = load_notes(path)
    note = _find(notes, note_id)
    approver = _require_approver(approver)
    if note.get("status") == "deleted":
        raise ValueError(f"note {note_id} is deleted and cannot be edited")
    if not new_text.strip():
        raise ValueError("edit needs non-empty new text")
    note.setdefault("history", []).append(
        {"at": _now_iso(), "action": "edited", "by": approver,
         "old_text": note["text"]})
    note["text"] = new_text.strip()
    note["status"] = "pending"
    note["approved_by"] = ""
    note["approved_at"] = ""
    save_notes(path, notes)
    return note


def delete_note(path: str | Path, note_id: int, approver: str) -> dict:
    """Mark deleted only with an approver; the record is kept, not erased."""
    notes = load_notes(path)
    note = _find(notes, note_id)
    approver = _require_approver(approver)
    note["status"] = "deleted"
    note.setdefault("history", []).append(
        {"at": _now_iso(), "action": "deleted", "by": approver})
    save_notes(path, notes)
    return note


def _live(notes: list[dict], include_pending: bool) -> list[dict]:
    if include_pending:
        return [n for n in notes if n.get("status") != "deleted"
                and n.get("status") != "rejected"]
    return [n for n in notes if n.get("status") == "approved"]


def notes_for_stage(path: str | Path, stage: str,
                    kind: str | None = None,
                    include_pending: bool = False) -> list[dict]:
    notes = _live(load_notes(path), include_pending)
    return [n for n in notes
            if n["stage"] == stage and (kind is None or n["kind"] == kind)]


def meeting_conclusions(path: str | Path, stage: str | None = None,
                        include_pending: bool = False) -> list[dict]:
    notes = _live(load_notes(path), include_pending)
    return [n for n in notes
            if n["kind"] == "meeting_conclusion"
            and (stage is None or n["stage"] == stage)]


def search_notes(path: str | Path, query: str,
                 stage: str | None = None,
                 kind: str | None = None,
                 include_pending: bool = False) -> list[dict]:
    """Keyword search for later chip-problem analysis.

    Matches case-insensitively across the note text, its tags, its
    problem_ref, and its stage key, so searching for a block name
    (e.g. "SerDes") finds both the failure note and the meeting
    conclusion that decided how to handle it. Optional stage/kind
    filters narrow the result without changing the search itself.
    """
    q = query.strip().lower()
    if not q:
        raise ValueError("search needs a non-empty query")
    out = []
    for n in _live(load_notes(path), include_pending):
        if stage is not None and n["stage"] != stage:
            continue
        if kind is not None and n["kind"] != kind:
            continue
        hay = " ".join([n["text"], n["problem_ref"], n["stage"],
                        *n.get("tags", [])]).lower()
        if q in hay:
            out.append(n)
    return out


def render_note(note: dict) -> str:
    ref = f" [{note['problem_ref']}]" if note.get("problem_ref") else ""
    tags = f" tags={','.join(note['tags'])}" if note.get("tags") else ""
    return (f"#{note['id']} {note['stage']} / {note['kind']} / "
            f"{note['author']} / {note['created_at']} / "
            f"{note.get('status', '?')}{ref}{tags}\n"
            f"  {note['text']}")
