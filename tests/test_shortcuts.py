"""Tests for sciappkit.shortcuts (model + manager)."""

from __future__ import annotations

import json

import pytest

from sciappkit.shortcuts.model import (
    Shortcut,
    ShortcutRegistry,
    detect_platform,
    portable_text,
)


def _registry(platform="linux"):
    reg = ShortcutRegistry(platform=platform)
    reg.register_many([
        Shortcut("file.new", default="Ctrl+N", category="File", display_name="New"),
        Shortcut("file.save", default="Ctrl+S", category="File", display_name="Save"),
        Shortcut("edit.delete", default="Delete", mac="Backspace", category="Edit"),
        Shortcut("view.reset", category="View"),  # no binding
    ])
    return reg


def test_detect_platform_is_known():
    assert detect_platform() in {"mac", "win", "linux"}


def test_platform_specific_default():
    reg = _registry(platform="mac")
    assert portable_text(reg.sequence("edit.delete")) == "Backspace"
    reg2 = _registry(platform="linux")
    assert portable_text(reg2.sequence("edit.delete")) == "Del"


def test_all_sorted_by_category_then_id():
    reg = _registry()
    ids = [s.action_id for s in reg.all()]
    assert ids == ["edit.delete", "file.new", "file.save", "view.reset"]


def test_by_category():
    reg = _registry()
    cats = reg.by_category()
    assert set(cats) == {"File", "Edit", "View"}
    assert [s.action_id for s in cats["File"]] == ["file.new", "file.save"]


def test_override_and_reset():
    reg = _registry()
    reg.set_override("file.new", "Ctrl+Shift+N")
    assert reg.is_modified("file.new")
    assert portable_text(reg.sequence("file.new")) == "Ctrl+Shift+N"
    reg.reset("file.new")
    assert not reg.is_modified("file.new")
    assert portable_text(reg.sequence("file.new")) == "Ctrl+N"


def test_override_equal_to_default_collapses():
    reg = _registry()
    reg.set_override("file.new", "Ctrl+N")  # same as default
    assert not reg.is_modified("file.new")


def test_conflicts_detects_collision():
    reg = _registry()
    assert reg.conflicts() == {}
    reg.set_override("file.save", "Ctrl+N")  # collide with file.new
    conflicts = reg.conflicts()
    assert conflicts == {"Ctrl+N": ["file.new", "file.save"]}


def test_conflict_for_with_exclude():
    reg = _registry()
    assert reg.conflict_for("Ctrl+N") == "file.new"
    assert reg.conflict_for("Ctrl+N", exclude="file.new") is None
    assert reg.conflict_for("Ctrl+J") is None


def test_conflicts_with_proposed_overlay():
    reg = _registry()
    # Nothing applied yet, but a proposed edit would collide.
    conflicts = reg.conflicts(proposed={"file.save": "Ctrl+N"})
    assert "Ctrl+N" in conflicts
    assert conflicts["Ctrl+N"] == ["file.new", "file.save"]


def test_export_import_overrides_roundtrip():
    reg = _registry()
    reg.set_override("file.new", "Ctrl+Shift+N")
    exported = reg.export_overrides()
    assert exported == {"file.new": "Ctrl+Shift+N"}

    reg2 = _registry()
    reg2.import_overrides(exported)
    assert portable_text(reg2.sequence("file.new")) == "Ctrl+Shift+N"
    # Only non-default overrides are exported.
    assert "file.save" not in exported


# -- manager ----------------------------------------------------------------

def _manager(qapp, tmp_path, platform="linux"):
    from sciappkit.shortcuts.manager import ShortcutManager

    return ShortcutManager(_registry(platform), "stest", config_path=tmp_path / "shortcuts.json")


def test_manager_apply_to_action(qapp, tmp_path):
    from PySide6.QtGui import QAction

    mgr = _manager(qapp, tmp_path)
    action = QAction("New")
    mgr.apply_to("file.new", action)
    assert portable_text(action.shortcut()) == "Ctrl+N"

    # Rebinding live-updates the bound action.
    assert mgr.set_sequence("file.new", "Ctrl+Shift+N") is True
    assert portable_text(action.shortcut()) == "Ctrl+Shift+N"


def test_manager_set_sequence_blocks_conflict(qapp, tmp_path):
    mgr = _manager(qapp, tmp_path)
    signals = []
    mgr.shortcut_updated.connect(lambda *a: signals.append(a))
    assert mgr.set_sequence("file.save", "Ctrl+N") is False  # conflicts with file.new
    assert signals == []
    assert portable_text(mgr.sequence("file.save")) == "Ctrl+S"


def test_manager_signals_fire_on_rebind(qapp, tmp_path):
    mgr = _manager(qapp, tmp_path)
    changed = []
    updated = []
    mgr.shortcuts_changed.connect(lambda: changed.append(True))
    mgr.shortcut_updated.connect(lambda *a: updated.append(a))
    mgr.set_sequence("file.new", "Ctrl+Shift+N")
    assert changed == [True]
    assert updated == [("file.new", "Ctrl+N", "Ctrl+Shift+N")]


def test_manager_persistence_roundtrip(qapp, tmp_path):
    mgr = _manager(qapp, tmp_path)
    mgr.set_sequence("file.new", "Ctrl+Shift+N")
    mgr.save()

    data = json.loads((tmp_path / "shortcuts.json").read_text())
    assert data["version"] == 1
    assert data["overrides"] == {"file.new": "Ctrl+Shift+N"}

    mgr2 = _manager(qapp, tmp_path)
    mgr2.load()
    assert portable_text(mgr2.sequence("file.new")) == "Ctrl+Shift+N"


def test_manager_load_missing_file_is_noop(qapp, tmp_path):
    mgr = _manager(qapp, tmp_path)
    mgr.load()  # no file yet
    assert portable_text(mgr.sequence("file.new")) == "Ctrl+N"


def test_manager_bind_shortcut_and_input_wrapper(qapp, tmp_path):
    from PySide6.QtWidgets import QWidget

    reg = ShortcutRegistry(platform="linux")
    reg.register(Shortcut("tool.rotate", default="R", is_single_key=True))
    from sciappkit.shortcuts.manager import ShortcutManager

    mgr = ShortcutManager(reg, "stest", config_path=tmp_path / "s.json")

    wrapped = []
    mgr.set_input_focus_wrapper(lambda h: (wrapped.append(h) or h))
    parent = QWidget()
    qsc = mgr.bind_shortcut("tool.rotate", lambda: None, parent, wrap_for_input=True)
    assert qsc is not None
    assert portable_text(qsc.key()) == "R"
    assert len(wrapped) == 1
