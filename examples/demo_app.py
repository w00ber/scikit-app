"""A minimal end-to-end sciappkit app (canvas_style = "both").

Hand-written against the M1 public API to validate that the building
blocks compose into a runnable application *before* the M2 scaffold/skill
exists. It docks a QGraphicsScene editor and a matplotlib plot in tabs;
the shared File→Export / Edit→Copy menu drives whichever tab is active.

Run it::

    python examples/demo_app.py                      # both canvases (default)
    python examples/demo_app.py --style=scene        # scene editor only
    python examples/demo_app.py --style=mpl          # matplotlib plot only
    QT_QPA_PLATFORM=offscreen python examples/demo_app.py --selftest
        # headless: build, export the canvas(es), exit 0

This is a throwaway demo, not part of the installed package.
"""

from __future__ import annotations

import sys

from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import QApplication

from sciappkit.app.main_window import SciAppMainWindow
from sciappkit.canvas.mpl_canvas import MplCanvas
from sciappkit.canvas.protocol import MplCanvasController, SceneCanvasController
from sciappkit.canvas.scene_canvas import GraphicsSceneBase, GraphicsViewBase
from sciappkit.settings.store import Setting, SettingsStore
from sciappkit.shortcuts.manager import ShortcutManager
from sciappkit.shortcuts.model import Shortcut, ShortcutRegistry

APP_NAME = "sciappkit-demo"


def _build_settings() -> SettingsStore:
    schema = [
        Setting("theme", "system", section="theme", key="mode"),
        Setting("grid_spacing", 20.0, section="grid", key="spacing"),
        Setting("last_directory", ""),
    ]
    return SettingsStore(APP_NAME, schema)


def _build_shortcuts() -> ShortcutManager:
    reg = ShortcutRegistry()
    reg.register_many([
        Shortcut("file.new", default="Ctrl+N", category="File", display_name="New"),
        Shortcut("file.open", default="Ctrl+O", category="File", display_name="Open"),
        Shortcut("file.save", default="Ctrl+S", category="File", display_name="Save"),
        Shortcut("file.save_as", default="Ctrl+Shift+S", category="File", display_name="Save As"),
        Shortcut("file.export_png", default="Ctrl+E", category="File", display_name="Export PNG"),
        Shortcut("file.quit", default="Ctrl+Q", category="File", display_name="Quit"),
        Shortcut("edit.undo", default="Ctrl+Z", category="Edit", display_name="Undo"),
        Shortcut("edit.redo", default="Ctrl+Shift+Z", category="Edit", display_name="Redo"),
        Shortcut("edit.copy_as_image", default="Ctrl+Shift+C", category="Edit",
                 display_name="Copy as Image"),
        Shortcut("view.fit", default="Ctrl+0", category="View", display_name="Fit to Content"),
        Shortcut("view.zoom_in", default="Ctrl++", category="View", display_name="Zoom In"),
        Shortcut("view.zoom_out", default="Ctrl+-", category="View", display_name="Zoom Out"),
    ])
    mgr = ShortcutManager(reg, APP_NAME)
    mgr.load()
    return mgr


def _build_scene_controller() -> SceneCanvasController:
    scene = GraphicsSceneBase()
    # A little sample drawing.
    scene.addRect(0, 0, 160, 100, QPen(QColor(40, 40, 40), 2), QBrush(QColor(120, 170, 255)))
    scene.addEllipse(40, 130, 120, 80, QPen(QColor(40, 40, 40), 2), QBrush(QColor(255, 200, 120)))
    text = scene.addText("sciappkit scene")
    text.setPos(0, 230)
    view = GraphicsViewBase(scene)
    return SceneCanvasController(view)


def _build_mpl_controller() -> MplCanvasController:
    canvas = MplCanvas(show_axes=True)
    canvas.ax.plot([0, 1, 2, 3, 4], [0, 1, 4, 9, 16], marker="o")
    canvas.ax.set_title("sciappkit plot")
    canvas.ax.set_xlabel("x")
    canvas.ax.set_ylabel("x²")
    return MplCanvasController(canvas)


class DemoWindow(SciAppMainWindow):
    """Trivial document model so the File menu has something to do."""

    def do_new(self) -> None:
        print("[demo] New document")

    def do_open(self, path: str) -> bool:
        print(f"[demo] Open {path}")
        return True

    def do_save(self, path: str) -> bool:
        print(f"[demo] Save {path}")
        return True


def build_controllers(style: str = "both") -> list:
    """Return controllers for the requested canvas style.

    *style* mirrors the M2 scaffold's ``canvas_style`` question:
    ``"scene"``, ``"mpl"``, or ``"both"``.
    """
    if style == "scene":
        return [_build_scene_controller()]
    if style == "mpl":
        return [_build_mpl_controller()]
    if style == "both":
        return [_build_scene_controller(), _build_mpl_controller()]
    raise ValueError(f"unknown canvas style: {style!r}")


def build_window(style: str = "both") -> DemoWindow:
    win = DemoWindow(
        "sciappkit demo",
        _build_settings(),
        _build_shortcuts(),
        build_controllers(style),
    )
    win.resize(900, 600)
    return win


def _selftest(win: DemoWindow) -> int:
    """Exercise the stack without a display; return an exit code."""
    import tempfile
    from pathlib import Path

    out = Path(tempfile.mkdtemp(prefix="sciappkit-demo-"))
    # Export each controller through the same uniform exporter surface.
    for i, ctrl in enumerate(win._controllers):
        target = ctrl.export_target()
        for fmt in ("svg", "png", "pdf"):
            path = out / f"canvas{i}.{fmt}"
            getattr(ctrl.exporter, f"export_{fmt}")(target, str(path))
            assert path.exists() and path.stat().st_size > 0, path
    # Copy the active canvas to the clipboard.
    win._copy_to_clipboard()
    # With more than one canvas, switching tabs moves the active controller.
    if len(win._controllers) > 1:
        win._tabs.setCurrentIndex(1)
        assert win.active_controller() is win._controllers[1]
    print(f"[demo] selftest OK ({len(win._controllers)} canvas) — exports written to {out}")
    sys.stdout.flush()
    # NOTE: the headless "offscreen" QPA plugin segfaults during interpreter
    # teardown *after* clipboard data has been set (a quirk of that plugin —
    # under a real display / xvfb+xcb it exits cleanly). The work is already
    # done and verified above, so hard-exit to avoid the misleading crash.
    import os
    os._exit(0)


def _style_from_argv() -> str:
    for arg in sys.argv:
        if arg.startswith("--style="):
            return arg.split("=", 1)[1]
    return "both"


def main() -> int:
    app = QApplication(sys.argv)
    win = build_window(_style_from_argv())
    if "--selftest" in sys.argv:
        win.show()
        app.processEvents()
        return _selftest(win)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
