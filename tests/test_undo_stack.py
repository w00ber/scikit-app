"""Tests for sciappkit.undo.stack (snapshot-based undo)."""

from __future__ import annotations

from PySide6.QtGui import QUndoStack

from sciappkit.undo.stack import SnapshotCommand, push_snapshot, snapshot


class Model:
    """A trivial serializable document model."""

    def __init__(self):
        self.data = {"value": 0, "items": []}

    def capture(self):
        # Return a copy so the live model and snapshots don't alias.
        import copy

        return copy.deepcopy(self.data)

    def restore(self, state):
        import copy

        self.data = copy.deepcopy(state)


def test_push_skips_initial_redo(qapp):
    model = Model()
    stack = QUndoStack()
    before = model.capture()
    model.data["value"] = 5  # mutate
    after = model.capture()
    push_snapshot(stack, "set value", before, after, model.restore)
    # Push must not re-apply (or revert) the already-live after-state.
    assert model.data["value"] == 5


def test_undo_then_redo(qapp):
    model = Model()
    stack = QUndoStack()
    before = model.capture()
    model.data["value"] = 5
    push_snapshot(stack, "set value", before, model.capture(), model.restore)

    stack.undo()
    assert model.data["value"] == 0
    stack.redo()
    assert model.data["value"] == 5


def test_no_push_when_unchanged(qapp):
    model = Model()
    stack = QUndoStack()
    before = model.capture()
    cmd = push_snapshot(stack, "noop", before, model.capture(), model.restore)
    assert cmd is None
    assert stack.count() == 0


def test_snapshot_context_manager(qapp):
    model = Model()
    stack = QUndoStack()
    with snapshot(stack, "add item", model.capture, model.restore):
        model.data["items"].append("a")
    assert model.data["items"] == ["a"]
    assert stack.count() == 1
    stack.undo()
    assert model.data["items"] == []


def test_snapshot_context_manager_no_change(qapp):
    model = Model()
    stack = QUndoStack()
    with snapshot(stack, "noop", model.capture, model.restore):
        pass
    assert stack.count() == 0


def test_snapshots_isolated_from_later_mutation(qapp):
    model = Model()
    stack = QUndoStack()
    with snapshot(stack, "add", model.capture, model.restore):
        model.data["items"].append("x")
    # Mutate the live model further without recording.
    model.data["items"].append("y")
    stack.undo()  # should restore to the empty list captured before "add"
    assert model.data["items"] == []


def test_command_text(qapp):
    cmd = SnapshotCommand("My Edit", lambda s: None, {"a": 1}, {"a": 2})
    assert cmd.text() == "My Edit"
