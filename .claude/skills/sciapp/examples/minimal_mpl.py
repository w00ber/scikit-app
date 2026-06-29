"""Minimal sciappkit matplotlib app.

    QT_QPA_PLATFORM=offscreen python minimal_mpl.py   # headless smoke
    python minimal_mpl.py                              # GUI
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from sciappkit.app.main_window import SciAppMainWindow
from sciappkit.canvas.mpl_canvas import MplCanvas
from sciappkit.canvas.protocol import MplCanvasController
from sciappkit.settings.store import Setting, SettingsStore
from sciappkit.shortcuts.manager import ShortcutManager
from sciappkit.shortcuts.model import Shortcut, ShortcutRegistry


def build_window() -> SciAppMainWindow:
    settings = SettingsStore("minimal_mpl", [Setting("theme", "system", section="theme", key="mode")])

    registry = ShortcutRegistry()
    registry.register(Shortcut("file.export_png", default="Ctrl+E", category="File", display_name="Export PNG"))
    shortcuts = ShortcutManager(registry, "minimal_mpl")

    canvas = MplCanvas(show_axes=True)
    canvas.ax.plot([0, 1, 2, 3], [0, 1, 4, 9], marker="o")
    canvas.ax.set_title("response")
    controller = MplCanvasController(canvas)

    return SciAppMainWindow("Minimal Plot", settings, shortcuts, controller)


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
