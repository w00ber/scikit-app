"""A widget for viewing and rebinding keyboard shortcuts.

Consumes a :class:`~sciappkit.shortcuts.manager.ShortcutManager`: lists the
registered shortcuts grouped by category, lets the user record a new key
with a ``QKeySequenceEdit``, detects conflicts (offering to steal the key
from the conflicting action), and supports per-row and global reset. It is
a passive view over the manager — every change goes through
``manager.set_sequence`` / ``clear_sequence`` / ``reset`` — and it
repopulates whenever the manager emits ``shortcuts_changed``.

The apply logic lives in :meth:`apply_sequence` so it can be driven
directly (and tested) without simulating focus on the editors.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QHBoxLayout,
    QKeySequenceEdit,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .model import portable_text


class ShortcutEditorWidget(QWidget):
    """Editable list of shortcuts backed by a :class:`ShortcutManager`."""

    shortcuts_modified = Signal()

    def __init__(self, manager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._manager = manager
        self._edits: dict[str, QKeySequenceEdit] = {}
        self._populating = False

        self._tree = QTreeWidget()
        self._tree.setColumnCount(2)
        self._tree.setHeaderLabels(["Action", "Shortcut"])
        self._tree.setRootIsDecorated(True)

        self._reset_all_btn = QPushButton("Reset All to Defaults")
        self._reset_all_btn.clicked.connect(self._reset_all)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self._reset_all_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(self._tree)
        layout.addLayout(buttons)

        manager.shortcuts_changed.connect(self._on_manager_changed)
        self.populate()

    # -- population ---------------------------------------------------------

    def populate(self) -> None:
        self._populating = True
        self._tree.clear()
        self._edits.clear()
        for category, shortcuts in self._manager.registry.by_category().items():
            parent = QTreeWidgetItem([category or "General", ""])
            parent.setFirstColumnSpanned(True)
            self._tree.addTopLevelItem(parent)
            parent.setExpanded(True)
            for sc in shortcuts:
                self._add_row(parent, sc)
        self._tree.resizeColumnToContents(0)
        self._populating = False

    def _add_row(self, parent: QTreeWidgetItem, shortcut) -> None:
        item = QTreeWidgetItem([shortcut.display_name, ""])
        if shortcut.description:
            item.setToolTip(0, shortcut.description)
        parent.addChild(item)

        edit = QKeySequenceEdit(self._manager.sequence(shortcut.action_id))
        edit.editingFinished.connect(
            lambda action_id=shortcut.action_id: self._on_edit_finished(action_id)
        )
        self._edits[shortcut.action_id] = edit
        self._tree.setItemWidget(item, 1, edit)

    # -- editing ------------------------------------------------------------

    def _on_edit_finished(self, action_id: str) -> None:
        if self._populating:
            return
        edit = self._edits.get(action_id)
        if edit is None:
            return
        self.apply_sequence(action_id, edit.keySequence())

    def apply_sequence(self, action_id: str, seq: QKeySequence | str) -> bool:
        """Apply *seq* to *action_id*, resolving conflicts. Returns success.

        On a conflict the user is asked whether to reassign the key (which
        clears it from the conflicting action). Returns ``True`` if the new
        sequence ended up applied.
        """
        portable = portable_text(seq)
        if not portable:
            self._manager.clear_sequence(action_id)
            self.shortcuts_modified.emit()
            return True

        conflict = self._manager.conflict_for(portable, exclude=action_id)
        if conflict is not None:
            if not self._confirm_reassign(conflict, portable):
                self._reset_edit(action_id)
                return False
            self._manager.clear_sequence(conflict)

        if self._manager.set_sequence(action_id, portable):
            self.shortcuts_modified.emit()
            return True
        self._reset_edit(action_id)
        return False

    def _confirm_reassign(self, conflict_action: str, portable: str) -> bool:
        sc = self._manager.registry.get(conflict_action)
        name = sc.display_name if sc is not None else conflict_action
        reply = QMessageBox.question(
            self,
            "Shortcut in use",
            f"“{portable}” is already assigned to “{name}”.\n"
            f"Reassign it to this action (and clear it from “{name}”)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

    def _reset_edit(self, action_id: str) -> None:
        edit = self._edits.get(action_id)
        if edit is not None:
            self._populating = True
            edit.setKeySequence(self._manager.sequence(action_id))
            self._populating = False

    # -- reset --------------------------------------------------------------

    def _reset_all(self) -> None:
        self._manager.reset_all()
        self.shortcuts_modified.emit()

    def _on_manager_changed(self) -> None:
        # Re-sync the editors with the manager's current bindings.
        if self._populating:
            return
        for action_id, edit in self._edits.items():
            self._populating = True
            edit.setKeySequence(self._manager.sequence(action_id))
            self._populating = False
