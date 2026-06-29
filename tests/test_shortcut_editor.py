"""Tests for sciappkit.shortcuts.editor.ShortcutEditorWidget."""

from __future__ import annotations

from sciappkit.shortcuts.editor import ShortcutEditorWidget
from sciappkit.shortcuts.manager import ShortcutManager
from sciappkit.shortcuts.model import Shortcut, ShortcutRegistry, portable_text


def _manager(tmp_path):
    reg = ShortcutRegistry(platform="linux")
    reg.register_many([
        Shortcut("file.new", default="Ctrl+N", category="File", display_name="New"),
        Shortcut("file.save", default="Ctrl+S", category="File", display_name="Save"),
        Shortcut("edit.copy", default="Ctrl+C", category="Edit", display_name="Copy"),
    ])
    return ShortcutManager(reg, "setest", config_path=tmp_path / "sc.json")


def test_populates_rows_per_shortcut(qapp, tmp_path):
    w = ShortcutEditorWidget(_manager(tmp_path))
    # One editor per registered action.
    assert set(w._edits) == {"file.new", "file.save", "edit.copy"}
    # Two category groups (File, Edit).
    assert w._tree.topLevelItemCount() == 2


def test_apply_sequence_rebinds(qapp, tmp_path):
    mgr = _manager(tmp_path)
    w = ShortcutEditorWidget(mgr)
    modified = []
    w.shortcuts_modified.connect(lambda: modified.append(True))
    assert w.apply_sequence("file.new", "Ctrl+Shift+N") is True
    assert portable_text(mgr.sequence("file.new")) == "Ctrl+Shift+N"
    assert modified == [True]


def test_apply_empty_clears(qapp, tmp_path):
    mgr = _manager(tmp_path)
    w = ShortcutEditorWidget(mgr)
    assert w.apply_sequence("file.new", "") is True
    assert portable_text(mgr.sequence("file.new")) == ""


def test_conflict_declined_reverts(qapp, tmp_path, monkeypatch):
    mgr = _manager(tmp_path)
    w = ShortcutEditorWidget(mgr)
    # User declines the reassign prompt.
    monkeypatch.setattr(w, "_confirm_reassign", lambda *a: False)
    assert w.apply_sequence("file.save", "Ctrl+N") is False
    # Unchanged: file.save keeps Ctrl+S, file.new keeps Ctrl+N.
    assert portable_text(mgr.sequence("file.save")) == "Ctrl+S"
    assert portable_text(mgr.sequence("file.new")) == "Ctrl+N"


def test_conflict_accepted_steals_key(qapp, tmp_path, monkeypatch):
    mgr = _manager(tmp_path)
    w = ShortcutEditorWidget(mgr)
    monkeypatch.setattr(w, "_confirm_reassign", lambda *a: True)
    assert w.apply_sequence("file.save", "Ctrl+N") is True
    # file.save now owns Ctrl+N; file.new was cleared.
    assert portable_text(mgr.sequence("file.save")) == "Ctrl+N"
    assert portable_text(mgr.sequence("file.new")) == ""


def test_reset_all_restores_defaults(qapp, tmp_path):
    mgr = _manager(tmp_path)
    w = ShortcutEditorWidget(mgr)
    w.apply_sequence("file.new", "Ctrl+Shift+N")
    w._reset_all()
    assert portable_text(mgr.sequence("file.new")) == "Ctrl+N"
    # The editor field re-syncs to the restored default.
    assert portable_text(w._edits["file.new"].keySequence()) == "Ctrl+N"


def test_editor_resyncs_on_external_change(qapp, tmp_path):
    mgr = _manager(tmp_path)
    w = ShortcutEditorWidget(mgr)
    # A change made directly on the manager updates the widget's editor.
    mgr.set_sequence("edit.copy", "Ctrl+Shift+C")
    assert portable_text(w._edits["edit.copy"].keySequence()) == "Ctrl+Shift+C"
