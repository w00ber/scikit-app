"""The scaffold generator.

Writes a runnable, src-layout application that depends on ``sciappkit``.
The generated app reuses :class:`~sciappkit.app.main_window.SciAppMainWindow`
so the emitted code stays small: a settings schema, a shortcut registry,
a canvas builder (per the chosen style), a thin window subclass with
document hooks, and an entry point — plus docs, a test, and packaging.
"""

from __future__ import annotations

import re
from pathlib import Path

CANVAS_STYLES = ("scene", "mpl", "both")


# --------------------------------------------------------------------------
# Identifier helpers
# --------------------------------------------------------------------------

def _to_package(name: str) -> str:
    pkg = re.sub(r"[^0-9a-zA-Z]+", "_", name).strip("_").lower()
    if not pkg:
        pkg = "myapp"
    if pkg[0].isdigit():
        pkg = f"app_{pkg}"
    return pkg


def _to_class(package: str) -> str:
    return "".join(part.capitalize() for part in package.split("_")) + "Window"


def _render(text: str, mapping: dict[str, str]) -> str:
    for token, value in mapping.items():
        text = text.replace(token, value)
    return text


# --------------------------------------------------------------------------
# Per-style canvas module
# --------------------------------------------------------------------------

_CANVAS_SCENE = '''\
"""Canvas construction for __TITLE__."""

from __future__ import annotations

from PySide6.QtGui import QBrush, QColor, QPen

from sciappkit.canvas.protocol import SceneCanvasController
from sciappkit.canvas.scene_canvas import GraphicsSceneBase, GraphicsViewBase


def build_controllers():
    """Return the canvas controller(s) for this app."""
    scene = GraphicsSceneBase()
    scene.addRect(0, 0, 160, 100, QPen(QColor(40, 40, 40), 2), QBrush(QColor(120, 170, 255)))
    view = GraphicsViewBase(scene)
    return [SceneCanvasController(view)]
'''

_CANVAS_MPL = '''\
"""Canvas construction for __TITLE__."""

from __future__ import annotations

from sciappkit.canvas.mpl_canvas import MplCanvas
from sciappkit.canvas.protocol import MplCanvasController


def build_controllers():
    """Return the canvas controller(s) for this app."""
    canvas = MplCanvas(show_axes=True)
    canvas.ax.plot([0, 1, 2, 3], [0, 1, 4, 9], marker="o")
    canvas.ax.set_title("__TITLE__")
    return [MplCanvasController(canvas)]
'''

_CANVAS_BOTH = '''\
"""Canvas construction for __TITLE__."""

from __future__ import annotations

from PySide6.QtGui import QBrush, QColor, QPen

from sciappkit.canvas.mpl_canvas import MplCanvas
from sciappkit.canvas.protocol import MplCanvasController, SceneCanvasController
from sciappkit.canvas.scene_canvas import GraphicsSceneBase, GraphicsViewBase


def build_controllers():
    """Return the canvas controller(s) for this app (scene + matplotlib)."""
    scene = GraphicsSceneBase()
    scene.addRect(0, 0, 160, 100, QPen(QColor(40, 40, 40), 2), QBrush(QColor(120, 170, 255)))
    view = GraphicsViewBase(scene)

    canvas = MplCanvas(show_axes=True)
    canvas.ax.plot([0, 1, 2, 3], [0, 1, 4, 9], marker="o")
    canvas.ax.set_title("__TITLE__")

    return [SceneCanvasController(view), MplCanvasController(canvas)]
'''

_CANVAS_BY_STYLE = {"scene": _CANVAS_SCENE, "mpl": _CANVAS_MPL, "both": _CANVAS_BOTH}


# --------------------------------------------------------------------------
# Other module templates
# --------------------------------------------------------------------------

_INIT = '''\
"""__TITLE__ — built with sciappkit."""

__version__ = "0.1.0"
'''

_SETTINGS = '''\
"""Typed settings for __TITLE__."""

from __future__ import annotations

from pathlib import Path

from sciappkit.settings import defaults as _defaults
from sciappkit.settings.store import Setting, SettingsStore

# Factory defaults for this app live beside this module.
_defaults.set_defaults_path(Path(__file__).parent / "defaults.yaml")

SCHEMA = [
    Setting("theme", "system", section="theme", key="mode"),
    Setting("grid_spacing", 20.0, section="grid", key="spacing"),
    Setting("snap_to_grid", True),
    Setting("recent_files", [], mutable=True),
    Setting("last_directory", ""),
]


def build_settings() -> SettingsStore:
    return SettingsStore("__PKG__", SCHEMA)
'''

_SHORTCUTS = '''\
"""Keyboard shortcuts for __TITLE__."""

from __future__ import annotations

from sciappkit.shortcuts.manager import ShortcutManager
from sciappkit.shortcuts.model import Shortcut, ShortcutRegistry


def build_shortcuts() -> ShortcutManager:
    registry = ShortcutRegistry()
    registry.register_many([
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
        Shortcut("edit.preferences", default="Ctrl+,", category="Edit", display_name="Preferences"),
        Shortcut("view.fit", default="Ctrl+0", category="View", display_name="Fit to Content"),
        Shortcut("view.zoom_in", default="Ctrl++", category="View", display_name="Zoom In"),
        Shortcut("view.zoom_out", default="Ctrl+-", category="View", display_name="Zoom Out"),
    ])
    manager = ShortcutManager(registry, "__PKG__")
    manager.load()
    return manager
'''

_MAIN_WINDOW = '''\
"""Main window for __TITLE__."""

from __future__ import annotations

import json
from pathlib import Path

from sciappkit.app.main_window import SciAppMainWindow
from sciappkit.app.settings_dialog import SettingsDialog

from .canvas import build_controllers
from .settings import build_settings
from .shortcuts import build_shortcuts


class __CLASS__(SciAppMainWindow):
    """The application's main window."""

    def __init__(self):
        super().__init__(
            "__TITLE__",
            build_settings(),
            build_shortcuts(),
            build_controllers(),
        )
        self.resize(1000, 680)

    # -- menus --------------------------------------------------------------

    def populate_extra_menus(self, menubar) -> None:
        tools = menubar.addMenu("&Tools")
        self._add_action(tools, "&Preferences…", self.open_preferences, "edit.preferences")

    def open_preferences(self) -> None:
        dialog = SettingsDialog(self._settings, self._shortcuts, self)
        dialog.add_double("grid_spacing", "Grid spacing", minimum=2, maximum=200, step=1)
        dialog.add_bool("snap_to_grid", "Snap to grid")
        dialog.exec()

    # -- document model -----------------------------------------------------
    # Replace these stubs with your real document load/save.

    def do_new(self) -> None:
        pass

    def do_open(self, path: str) -> bool:
        try:
            json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return False
        return True

    def do_save(self, path: str) -> bool:
        try:
            Path(path).write_text(json.dumps({"app": "__PKG__"}), encoding="utf-8")
        except OSError:
            return False
        return True
'''

_APP = '''\
"""Application entry point for __TITLE__."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .main_window import __CLASS__


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("__TITLE__")
    window = __CLASS__()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
'''

_MAIN = '''\
from .app import main

if __name__ == "__main__":
    raise SystemExit(main())
'''

_DEFAULTS_YAML = '''\
# Factory defaults for __TITLE__.
grid:
  spacing: 20.0
theme:
  mode: "system"
'''

_PYPROJECT = '''\
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "__PKG__"
version = "0.1.0"
description = "__TITLE__ — a scientific app built with sciappkit."
readme = "README.md"
requires-python = ">=3.10"
authors = [
    {name = "__AUTHOR__"},
]
dependencies = [
    "sciappkit>=0.1",
]

[project.optional-dependencies]
dev = ["pytest>=7.0"]

[project.gui-scripts]
__PKG__ = "__PKG__.app:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
__PKG__ = ["defaults.yaml", "docs/*.md"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"
'''

_README = '''\
# __TITLE__

A scientific desktop app built with [sciappkit](https://github.com/w00ber/scikit-app).

## Run

```bash
pip install -e ".[dev]"
__PKG__                 # launch the GUI
python -m __PKG__       # same thing
```

The test suite runs Qt headless:

```bash
QT_QPA_PLATFORM=offscreen pytest
```

## Layout

```
src/__PKG__/
  app.py            # QApplication + main()
  main_window.py    # __CLASS__(SciAppMainWindow): menus, document hooks
  canvas.py         # build_controllers() — the canvas(es)
  settings.py       # typed SettingsStore schema
  shortcuts.py      # ShortcutRegistry + ShortcutManager
  defaults.yaml     # factory defaults
docs/               # help.md, tutorial.md
```

Edit the `do_new` / `do_open` / `do_save` hooks in `main_window.py` to wire
up your document format.
'''

_CLAUDE_MD = '''\
# __TITLE__ — notes for Claude Code

This app is built on **sciappkit** (`import sciappkit`). Prefer the
framework's building blocks over hand-rolled Qt:

- Window base: `sciappkit.app.main_window.SciAppMainWindow` (subclassed as
  `__CLASS__` in `src/__PKG__/main_window.py`). It owns the File/Edit/View
  menus, Export/Copy, theming, shortcuts, and recent files. Add menus via
  `populate_extra_menus`; implement `do_new` / `do_open` / `do_save`.
- Canvas: `build_controllers()` in `canvas.py` returns
  `CanvasController`(s) — `SceneCanvasController` (QGraphicsScene) and/or
  `MplCanvasController` (matplotlib).
- Settings: typed `SettingsStore` schema in `settings.py`; edit via
  `sciappkit.app.settings_dialog.SettingsDialog`.
- Shortcuts: `ShortcutRegistry` + `ShortcutManager` in `shortcuts.py`.
- Editors: `sciappkit.widgets.code_editor.CodeEditor` and
  `sciappkit.widgets.markdown_editor.MarkdownEditor` (use `backend="web"`
  for inline images; needs the sciappkit `[web]` extra).

Run tests headless: `QT_QPA_PLATFORM=offscreen pytest`.
'''

_HELP_MD = '''\
# __TITLE__ Help

Welcome to **__TITLE__**.

- **File → New / Open / Save** — manage documents.
- **File → Export** — SVG / PNG / PDF of the active canvas.
- **Edit → Copy to Clipboard** — copy the canvas as an image.
- **Tools → Preferences** — theme and app settings.

See **Tutorial** for a guided walkthrough.
'''

_TUTORIAL_MD = '''\
# __TITLE__ Tutorial

1. Launch the app.
2. Interact with the canvas.
3. Open **Tools → Preferences** to switch the theme.
4. **File → Export** your work to PNG/SVG/PDF.
'''

_GITIGNORE = '''\
__pycache__/
*.py[cod]
*.egg-info/
build/
dist/
.venv/
.pytest_cache/
.DS_Store
'''

_TEST_APP = '''\
"""Smoke test: the window builds headless."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from __PKG__.main_window import __CLASS__


def test_window_builds():
    app = QApplication.instance() or QApplication([])
    window = __CLASS__()
    assert window is not None
    assert window.windowTitle().endswith("__TITLE__")
'''


def create_app(
    target: str | Path,
    *,
    app_name: str,
    package: str | None = None,
    canvas_style: str = "both",
    author: str = "",
    force: bool = False,
) -> Path:
    """Generate a runnable sciappkit application at *target*.

    Parameters
    ----------
    target: parent directory the project folder is created in.
    app_name: human title (e.g. "Spectrum Tool").
    package: import/distribution name; derived from *app_name* if omitted.
    canvas_style: one of :data:`CANVAS_STYLES`.
    author: author name for ``pyproject.toml``.
    force: allow writing into an existing non-empty project directory.

    Returns the created project directory.
    """
    if canvas_style not in CANVAS_STYLES:
        raise ValueError(f"canvas_style must be one of {CANVAS_STYLES}, got {canvas_style!r}")

    pkg = _to_package(package or app_name)
    cls = _to_class(pkg)
    mapping = {
        "__PKG__": pkg,
        "__CLASS__": cls,
        "__TITLE__": app_name,
        "__AUTHOR__": author,
    }

    project = Path(target) / pkg
    if project.exists() and any(project.iterdir()) and not force:
        raise FileExistsError(f"{project} already exists and is not empty (use force=True)")

    src = project / "src" / pkg
    files: dict[Path, str] = {
        project / "pyproject.toml": _PYPROJECT,
        project / "README.md": _README,
        project / "CLAUDE.md": _CLAUDE_MD,
        project / ".gitignore": _GITIGNORE,
        src / "__init__.py": _INIT,
        src / "__main__.py": _MAIN,
        src / "app.py": _APP,
        src / "main_window.py": _MAIN_WINDOW,
        src / "canvas.py": _CANVAS_BY_STYLE[canvas_style],
        src / "settings.py": _SETTINGS,
        src / "shortcuts.py": _SHORTCUTS,
        src / "defaults.yaml": _DEFAULTS_YAML,
        project / "docs" / "help.md": _HELP_MD,
        project / "docs" / "tutorial.md": _TUTORIAL_MD,
        project / "tests" / "test_app.py": _TEST_APP,
    }

    for path, template in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_render(template, mapping), encoding="utf-8")

    return project
