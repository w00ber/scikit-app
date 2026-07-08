"""Snapshot-based undo on top of ``QUndoStack``.

The plan standardizes new apps on Qt's ``QUndoStack`` but also offers a
snapshot helper, so apps with a serializable document model (graphulator's
JSON-snapshot style) get undo/redo without writing a ``QUndoCommand`` per
operation. You capture the document state before and after a mutation; the
command restores whichever side undo/redo asks for.

Typical use with the :func:`snapshot` context manager::

    with snapshot(scene.undo_stack, "Move nodes", model.to_dict, model.load):
        model.move_selected(dx, dy)

If the captured state is unchanged, nothing is pushed.
"""

from __future__ import annotations

import copy
from contextlib import contextmanager
from typing import Any, Callable

from PySide6.QtGui import QUndoCommand, QUndoStack

CaptureFn = Callable[[], Any]
RestoreFn = Callable[[Any], None]


class SnapshotCommand(QUndoCommand):
    """A ``QUndoCommand`` that restores captured before/after snapshots.

    ``restore`` is called with the *before* snapshot on undo and the
    *after* snapshot on redo. The mutation is assumed to have already
    happened when the command is constructed, so the initial ``redo()``
    that ``QUndoStack.push`` triggers is skipped (it would otherwise
    re-apply the already-live after-state).

    Snapshots are deep-copied defensively so later mutation of the live
    model can't alias what the command holds.
    """

    def __init__(self, text: str, restore: RestoreFn, before: Any, after: Any) -> None:
        super().__init__(text)
        self._restore = restore
        self._before = copy.deepcopy(before)
        self._after = copy.deepcopy(after)
        self._skip_initial_redo = True

    def undo(self) -> None:
        self._restore(copy.deepcopy(self._before))

    def redo(self) -> None:
        if self._skip_initial_redo:
            # The after-state is already live at push time.
            self._skip_initial_redo = False
            return
        self._restore(copy.deepcopy(self._after))


def push_snapshot(
    undo_stack: QUndoStack,
    text: str,
    before: Any,
    after: Any,
    restore: RestoreFn,
) -> SnapshotCommand | None:
    """Push a :class:`SnapshotCommand` for a completed mutation.

    Returns the command, or ``None`` if *before* equals *after* (no
    change, so nothing is pushed).
    """
    if before == after:
        return None
    cmd = SnapshotCommand(text, restore, before, after)
    undo_stack.push(cmd)
    return cmd


@contextmanager
def snapshot(undo_stack: QUndoStack, text: str, capture: CaptureFn, restore: RestoreFn):
    """Capture state around a mutation and push an undo command if it changed.

    ``capture()`` returns a snapshot of the document; ``restore(snapshot)``
    applies one back. The body performs the mutation::

        with snapshot(stack, "Edit", model.to_dict, model.load):
            model.do_edit()
    """
    before = capture()
    yield
    after = capture()
    push_snapshot(undo_stack, text, before, after, restore)
