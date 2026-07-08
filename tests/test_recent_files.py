"""Tests for sciappkit.settings.recent_files and its main-window wiring."""

from __future__ import annotations

from sciappkit.settings.recent_files import RecentFiles
from sciappkit.settings.store import Setting, SettingsStore


# -- standalone (in-memory) -------------------------------------------------

def test_add_dedupes_and_orders():
    rf = RecentFiles()
    rf.add("/a")
    rf.add("/b")
    rf.add("/a")  # moves to front, no duplicate
    assert rf.items() == ["/a", "/b"]


def test_cap_enforced():
    rf = RecentFiles(max_items=3)
    for p in ["/1", "/2", "/3", "/4"]:
        rf.add(p)
    assert rf.items() == ["/4", "/3", "/2"]


def test_remove_and_clear_and_contains():
    rf = RecentFiles()
    rf.add("/a")
    rf.add("/b")
    assert "/a" in rf
    rf.remove("/a")
    assert "/a" not in rf
    assert len(rf) == 1
    rf.clear()
    assert rf.items() == []


def test_prune_missing(tmp_path):
    real = tmp_path / "real.txt"
    real.write_text("x")
    rf = RecentFiles()
    rf.add(str(real))
    rf.add(str(tmp_path / "ghost.txt"))
    rf.prune_missing()
    assert rf.items() == [str(real)]


# -- store-backed persistence -----------------------------------------------

def _store(tmp_path):
    schema = [Setting("recent_files", [], mutable=True)]
    return SettingsStore("rftest", schema, settings_dir=tmp_path)


def test_store_backed_persists(tmp_path):
    store = _store(tmp_path)
    rf = RecentFiles(store)
    rf.add("/x")
    rf.add("/y")
    # Reload a fresh store from disk: the list persisted.
    store2 = _store(tmp_path)
    assert list(RecentFiles(store2)) == ["/y", "/x"]


# -- SciAppMainWindow integration -------------------------------------------

def _window(tmp_path):
    from sciappkit.app.main_window import SciAppMainWindow
    from sciappkit.canvas.protocol import SceneCanvasController
    from sciappkit.canvas.scene_canvas import GraphicsSceneBase, GraphicsViewBase
    from sciappkit.shortcuts.manager import ShortcutManager
    from sciappkit.shortcuts.model import ShortcutRegistry

    schema = [
        Setting("recent_files", [], mutable=True),
        Setting("last_directory", ""),
    ]
    settings = SettingsStore("rfwin", schema, settings_dir=tmp_path)
    shortcuts = ShortcutManager(ShortcutRegistry(platform="linux"), "rfwin",
                                config_path=tmp_path / "sc.json")
    scene = GraphicsSceneBase()
    scene.addRect(0, 0, 10, 10)
    ctrl = SceneCanvasController(GraphicsViewBase(scene))

    opened = []

    class W(SciAppMainWindow):
        def do_open(self, path):
            opened.append(path)
            return True

    win = W("RF", settings, shortcuts, ctrl)
    win._opened = opened
    return win


def test_recent_menu_enabled_when_field_present(qapp, tmp_path):
    win = _window(tmp_path)
    assert win._recent is not None
    assert hasattr(win, "_recent_menu")


def test_open_recent_tracks_and_populates_menu(qapp, tmp_path):
    win = _window(tmp_path)
    win._open_recent("/some/file.dat")
    assert win._opened == ["/some/file.dat"]
    assert "/some/file.dat" in list(win._recent)
    # The menu now has the entry plus a "Clear Recent Files" action.
    labels = [a.text() for a in win._recent_menu.actions() if a.text()]
    assert "file.dat" in labels
    assert "Clear Recent Files" in labels


def test_clear_recent(qapp, tmp_path):
    win = _window(tmp_path)
    win._open_recent("/some/file.dat")
    win._clear_recent()
    assert list(win._recent) == []


def test_no_recent_menu_without_field(qapp, tmp_path):
    # A window whose settings schema lacks recent_files gets no recent menu.
    from sciappkit.app.main_window import SciAppMainWindow
    from sciappkit.canvas.protocol import SceneCanvasController
    from sciappkit.canvas.scene_canvas import GraphicsSceneBase, GraphicsViewBase
    from sciappkit.shortcuts.manager import ShortcutManager
    from sciappkit.shortcuts.model import ShortcutRegistry

    settings = SettingsStore("nornf", [Setting("theme", "system")], settings_dir=tmp_path)
    shortcuts = ShortcutManager(ShortcutRegistry(platform="linux"), "nornf",
                                config_path=tmp_path / "s.json")
    scene = GraphicsSceneBase()
    ctrl = SceneCanvasController(GraphicsViewBase(scene))
    win = SciAppMainWindow("NoRF", settings, shortcuts, ctrl)
    assert win._recent is None
    assert not hasattr(win, "_recent_menu")
