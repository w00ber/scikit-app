"""Minimal sciappkit scene app — the smallest useful SciAppMainWindow.

    QT_QPA_PLATFORM=offscreen python minimal_scene.py   # headless smoke
    python minimal_scene.py                              # GUI
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from sciappkit.app.main_window import SciAppMainWindow
from sciappkit.canvas.protocol import SceneCanvasController
from sciappkit.canvas.scene_canvas import GraphicsSceneBase, GraphicsViewBase
from sciappkit.settings.store import Setting, SettingsStore
from sciappkit.shortcuts.manager import ShortcutManager
from sciappkit.shortcuts.model import Shortcut, ShortcutRegistry


def build_window() -> SciAppMainWindow:
    settings = SettingsStore("minimal_scene", [Setting("theme", "system", section="theme", key="mode")])

    registry = ShortcutRegistry()
    registry.register_many([
        Shortcut("file.new", default="Ctrl+N", category="File", display_name="New"),
        Shortcut("file.save", default="Ctrl+S", category="File", display_name="Save"),
        Shortcut("view.fit", default="Ctrl+0", category="View", display_name="Fit"),
    ])
    shortcuts = ShortcutManager(registry, "minimal_scene")

    scene = GraphicsSceneBase()
    scene.addRect(0, 0, 160, 100)
    controller = SceneCanvasController(GraphicsViewBase(scene))

    return SciAppMainWindow("Minimal Scene", settings, shortcuts, controller)


def main() -> int:
    app = QApplication(sys.argv)
    win = build_window()
    win.show()
    if "--selftest" in sys.argv:
        app.processEvents()
        return 0
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
