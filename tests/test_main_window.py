"""Tests for sciappkit.app.main_window.SciAppMainWindow."""

from __future__ import annotations

import pytest

from sciappkit.app.main_window import SciAppMainWindow
from sciappkit.canvas.mpl_canvas import MplCanvas
from sciappkit.canvas.protocol import MplCanvasController, SceneCanvasController
from sciappkit.canvas.scene_canvas import GraphicsSceneBase, GraphicsViewBase
from sciappkit.settings.store import Setting, SettingsStore
from sciappkit.shortcuts.manager import ShortcutManager
from sciappkit.shortcuts.model import Shortcut, ShortcutRegistry


def _settings(tmp_path):
    schema = [
        Setting("theme", "system", section="theme", key="mode"),
        Setting("last_directory", ""),
    ]
    return SettingsStore("wintest", schema, settings_dir=tmp_path)


def _shortcuts(tmp_path):
    reg = ShortcutRegistry(platform="linux")
    reg.register_many([
        Shortcut("file.new", default="Ctrl+N", category="File"),
        Shortcut("file.save", default="Ctrl+S", category="File"),
        Shortcut("edit.copy_as_image", default="Ctrl+Shift+C", category="Edit"),
    ])
    return ShortcutManager(reg, "wintest", config_path=tmp_path / "sc.json")


class DemoWindow(SciAppMainWindow):
    def __init__(self, *a, **k):
        self.opened: list[str] = []
        self.saved: list[str] = []
        self.new_count = 0
        super().__init__(*a, **k)

    def do_new(self):
        self.new_count += 1

    def do_open(self, path):
        self.opened.append(path)
        return True

    def do_save(self, path):
        self.saved.append(path)
        return True


def _scene_controller():
    scene = GraphicsSceneBase()
    scene.addRect(0, 0, 60, 40)
    view = GraphicsViewBase(scene)
    return SceneCanvasController(view), scene


def _mpl_controller():
    canvas = MplCanvas(show_axes=True)
    canvas.ax.plot([0, 1], [0, 1])
    return MplCanvasController(canvas)


def _window(tmp_path, controllers):
    return DemoWindow("WinTest", _settings(tmp_path), _shortcuts(tmp_path), controllers)


# -- construction -----------------------------------------------------------

def test_single_controller_window_builds(qapp, tmp_path):
    ctrl, _ = _scene_controller()
    win = _window(tmp_path, ctrl)
    assert win.windowTitle() == "Untitled — WinTest"
    assert win.centralWidget() is ctrl.widget()


def test_shortcut_bound_to_action(qapp, tmp_path):
    ctrl, _ = _scene_controller()
    win = _window(tmp_path, ctrl)
    # The New action's shortcut should come from the manager's registry.
    from PySide6.QtGui import QAction

    from sciappkit.shortcuts.model import portable_text

    new_acts = [a for a in win.findChildren(QAction) if a.text() == "&New"]
    assert new_acts, "New action was not created"
    assert portable_text(new_acts[0].shortcut()) == "Ctrl+N"


# -- export delegation ------------------------------------------------------

def test_export_delegates_to_active_controller(qapp, tmp_path, monkeypatch):
    ctrl, _ = _scene_controller()
    win = _window(tmp_path, ctrl)
    out = tmp_path / "exported.png"
    monkeypatch.setattr(
        "sciappkit.app.main_window.QFileDialog.getSaveFileName",
        lambda *a, **k: (str(out), "PNG (*.png)"),
    )
    win._export("png")
    assert out.exists() and out.stat().st_size > 0
    # last_directory persisted because the schema defines it.
    assert win._settings.last_directory == str(tmp_path)


def test_export_cancelled_is_noop(qapp, tmp_path, monkeypatch):
    ctrl, _ = _scene_controller()
    win = _window(tmp_path, ctrl)
    monkeypatch.setattr(
        "sciappkit.app.main_window.QFileDialog.getSaveFileName",
        lambda *a, **k: ("", ""),
    )
    win._export("png")  # should not raise


def test_copy_to_clipboard(qapp, tmp_path):
    ctrl, _ = _scene_controller()
    win = _window(tmp_path, ctrl)
    win._copy_to_clipboard()
    assert qapp.clipboard().mimeData().hasImage()


# -- multi-canvas + active tracking -----------------------------------------

def test_two_controllers_use_tabs_and_track_active(qapp, tmp_path):
    scene_ctrl, _ = _scene_controller()
    mpl_ctrl = _mpl_controller()
    win = _window(tmp_path, [scene_ctrl, mpl_ctrl])
    from PySide6.QtWidgets import QTabWidget

    assert isinstance(win.centralWidget(), QTabWidget)
    # Untitled controllers get distinct default labels.
    assert win._tabs.tabText(0) == "Canvas 1"
    assert win._tabs.tabText(1) == "Canvas 2"
    assert win.active_controller() is scene_ctrl

    win._tabs.setCurrentIndex(1)
    assert win.active_controller() is mpl_ctrl
    assert win.active_controller().export_target() is mpl_ctrl.widget().fig


# -- undo / redo delegation -------------------------------------------------

def test_undo_redo_delegates_to_scene_stack(qapp, tmp_path):
    ctrl, scene = _scene_controller()
    win = _window(tmp_path, ctrl)

    from PySide6.QtGui import QUndoCommand

    flag = {"done": False}

    class Cmd(QUndoCommand):
        def redo(self):
            flag["done"] = True

        def undo(self):
            flag["done"] = False

    scene.undo_stack.push(Cmd())
    assert flag["done"] is True
    win._undo()
    assert flag["done"] is False
    win._redo()
    assert flag["done"] is True


def test_is_dirty_tracks_undo_stack(qapp, tmp_path):
    ctrl, scene = _scene_controller()
    win = _window(tmp_path, ctrl)
    assert win.is_dirty() is False
    from PySide6.QtGui import QUndoCommand

    scene.undo_stack.push(QUndoCommand())
    assert win.is_dirty() is True


# -- document hooks ---------------------------------------------------------

def test_file_new_resets_and_titles(qapp, tmp_path):
    ctrl, _ = _scene_controller()
    win = _window(tmp_path, ctrl)
    win._current_file = "/x/y.doc"
    win._file_new()
    assert win.new_count == 1
    assert win.current_file is None
    assert win.windowTitle() == "Untitled — WinTest"


def test_file_open_calls_hook_and_titles(qapp, tmp_path, monkeypatch):
    ctrl, _ = _scene_controller()
    win = _window(tmp_path, ctrl)
    doc = tmp_path / "doc.dat"
    doc.write_text("x")
    monkeypatch.setattr(
        "sciappkit.app.main_window.QFileDialog.getOpenFileName",
        lambda *a, **k: (str(doc), ""),
    )
    win._file_open()
    assert win.opened == [str(doc)]
    assert win.current_file == str(doc)
    assert win.windowTitle() == f"{doc.name} — WinTest"


def test_file_save_as_calls_hook(qapp, tmp_path, monkeypatch):
    ctrl, _ = _scene_controller()
    win = _window(tmp_path, ctrl)
    out = tmp_path / "saved.dat"
    monkeypatch.setattr(
        "sciappkit.app.main_window.QFileDialog.getSaveFileName",
        lambda *a, **k: (str(out), ""),
    )
    win._file_save()  # no current file -> save as
    assert win.saved == [str(out)]
    assert win.current_file == str(out)


# -- theme ------------------------------------------------------------------

def test_apply_theme_persists(qapp, tmp_path):
    ctrl, _ = _scene_controller()
    win = _window(tmp_path, ctrl)
    seen = []
    win.theme_changed.connect(seen.append)
    win.apply_theme("dark")
    assert win._settings.theme == "dark"
    assert seen == ["dark"]
    # Persisted to disk.
    import json

    assert json.loads(win._settings.path.read_text())["theme"] == "dark"
    win.apply_theme("system")  # restore


def test_requires_a_controller(qapp, tmp_path):
    with pytest.raises(ValueError):
        DemoWindow("WinTest", _settings(tmp_path), _shortcuts(tmp_path), [])
