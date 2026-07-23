"""The scaffold generator.

Writes a runnable, src-layout application that depends on ``sciappkit``.
The generated app reuses :class:`~sciappkit.app.main_window.SciAppMainWindow`
so the emitted code stays small: a settings schema, a shortcut registry,
a canvas builder (per the chosen style), a thin window subclass with
document hooks, and an entry point — plus docs, a test, and packaging.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

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
from pathlib import Path

from PySide6.QtWidgets import QApplication

from sciappkit.app.icons import set_app_icon

from .main_window import __CLASS__


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("__TITLE__")
    # Multi-resolution app icon (drop PNGs into icons/ — see icons/README.md).
    # On macOS this also sets the Dock icon, even for unbundled runs.
    set_app_icon(app, Path(__file__).parent / "icons")
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
__PKG__ = ["defaults.yaml", "docs/*.md", "icons/*.png"]

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

## Standalone builds & releases

```bash
pip install pyinstaller
pyinstaller __PKG__.spec        # one-folder build in dist/ (+ .app on macOS)
```

CI (`.github/workflows/build.yml`) runs the tests, builds macOS + Windows
apps, and attaches them to a GitHub release whenever you push a version
tag (`git tag v0.1.0 && git push --tags`).

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

The **sciapp skill** is preinstalled at `.claude/skills/sciapp/` — Claude
Code loads it automatically. It carries the framework API reference,
conventions, a new-app recipe, and runnable minimal examples; prefer it
over guessing at sciappkit APIs.

Run tests headless: `QT_QPA_PLATFORM=offscreen pytest`.
'''

_ICONS_README = '''\
# App icons

Drop a macOS-style iconset ladder of PNGs here and __TITLE__ picks them up
automatically at launch (`app.py` calls `sciappkit.app.icons.set_app_icon`).
One `QIcon` gets every size, so Qt shows a crisp icon in the title bar,
Dock / taskbar, and app switcher — on macOS this works even for plain
`python -m __PKG__` runs, no .app bundle needed.

Expected names (any subset works; more sizes = crisper):

    icon_16x16.png      icon_16x16@2x.png
    icon_32x32.png      icon_32x32@2x.png
    icon_128x128.png    icon_128x128@2x.png
    icon_256x256.png    icon_256x256@2x.png
    icon_512x512.png    icon_512x512@2x.png

Generate the ladder from a single 1024x1024 `master.png` (macOS):

```bash
for s in 16 32 128 256 512; do
  sips -z $s $s master.png --out icon_${s}x${s}.png
  sips -z $((s*2)) $((s*2)) master.png --out icon_${s}x${s}@2x.png
done
```

Only when you later freeze a macOS .app bundle (e.g. PyInstaller) do you
also need a real `.icns` — build one from the same PNGs with `iconutil`:

```bash
mkdir __PKG__.iconset && cp icon_*.png __PKG__.iconset/
iconutil -c icns __PKG__.iconset
```

This README is safe to delete once your icons are in place.
'''

_LAUNCHER = '''\
#!/usr/bin/env python
"""PyInstaller entry point for __TITLE__.

PyInstaller analyzes a *script*, not a package, so this shim imports the
app with an absolute import (``src/__PKG__/__main__.py`` uses a relative
one, which fails when frozen as the top-level script). Referenced by
``__PKG__.spec``; not used for normal `pip install` runs.
"""

from __PKG__.app import main

if __name__ == "__main__":
    raise SystemExit(main())
'''

_SPEC = '''\
# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for __TITLE__.

Build locally:
    pip install pyinstaller
    pyinstaller __PKG__.spec

Produces a one-folder distribution in dist/__PKG__/ and, on macOS, a
dist/__TITLE__.app bundle. CI (.github/workflows/build.yml) runs this on
tag pushes and attaches zips to a GitHub release.
"""

import sys
from pathlib import Path

HERE = Path(SPECPATH)
SRC = HERE / "src"
PKG = SRC / "__PKG__"

# Single source of truth for the version: src/__PKG__/__init__.py, parsed
# textually (not imported) so PyInstaller's spec evaluation doesn't pull
# PySide6/matplotlib into its own process.
APP_VERSION = "0.0.0"
for _line in (PKG / "__init__.py").read_text(encoding="utf-8").splitlines():
    if _line.startswith("__version__"):
        APP_VERSION = _line.split("=", 1)[1].strip().strip('"').strip("'")
        break

IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform == "win32"

# macOS wants a real .icns for the bundle icon (build one from the PNG
# ladder with iconutil — see src/__PKG__/icons/README.md). Windows wants a
# .ico; CI generates it from the same PNGs with Pillow. Both are optional:
# missing files just mean the frozen app uses the runtime QIcon only.
_ICNS = PKG / "icons" / "app.icns"
MAC_ICON = str(_ICNS) if IS_MAC and _ICNS.exists() else None
_ICO = HERE / "__PKG__.ico"
WIN_ICON = str(_ICO) if IS_WIN and _ICO.exists() else None

# Qt modules sciappkit apps don't use by default. Trim this list if you
# adopt one (e.g. remove the QtWebEngine lines if you use
# MarkdownEditor(backend="web")). NOTE: never exclude stdlib modules that
# dependencies import at load time — matplotlib needs ``unittest.mock``
# via its dependency chain, so ``unittest`` must stay bundled.
EXCLUDES = [
    "PySide6.QtWebEngine",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuick3D",
    "PySide6.QtQuickControls2",
    "PySide6.QtQuickWidgets",
    "PySide6.Qt3DAnimation",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DExtras",
    "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic",
    "PySide6.Qt3DRender",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtNetworkAuth",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.QtSql",
    "PySide6.QtTest",
    "tkinter",
]

# Package data setuptools would install but PyInstaller won't find on its
# own. Keep in sync with [tool.setuptools.package-data] in pyproject.toml.
datas = [
    (str(PKG / "defaults.yaml"), "__PKG__"),
    (str(PKG / "icons"), "__PKG__/icons"),
]

a = Analysis(
    ["__PKG___launcher.py"],
    pathex=[str(SRC)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # Since PyInstaller 5.0 the matplotlib hook only bundles backends
        # referenced by a literal ``matplotlib.use(...)`` or explicit
        # import. sciappkit's exporters call ``fig.savefig(..., format=
        # "svg"/"pdf")``, which imports these lazily via importlib —
        # without listing them the frozen app's exports fail at runtime.
        # See pyinstaller/pyinstaller#6760.
        "matplotlib.backends.backend_agg",
        "matplotlib.backends.backend_svg",
        "matplotlib.backends.backend_pdf",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="__PKG__",
    debug=False,
    strip=False,
    upx=True,
    console=False,  # GUI app: no terminal window
    icon=WIN_ICON if IS_WIN else MAC_ICON,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name="__PKG__",
)

if IS_MAC:
    app = BUNDLE(
        coll,
        name="__TITLE__.app",
        icon=MAC_ICON,
        bundle_identifier="com.__PKG__.app",
        info_plist={
            "CFBundleDisplayName": "__TITLE__",
            "CFBundleShortVersionString": APP_VERSION,
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "12.0",
        },
    )
'''

_BUILD_YML = '''\
name: Build Standalone Apps

# Two ways in:
#   * push a version tag (git tag v0.1.0 && git push --tags) — builds and
#     attaches zips to a GitHub release for that tag;
#   * manual dispatch — builds artifacts; optionally names an existing
#     release tag to (re)attach them to (repairs a release whose assets
#     went missing without rewriting its notes).
on:
  push:
    tags:
      - "v*"
  workflow_dispatch:
    inputs:
      release_tag:
        description: >-
          Existing release tag to attach the built zips to (e.g. v0.1.2).
          Leave blank to just build artifacts.
        required: false
        default: ""

permissions:
  contents: write  # release creation/upload

jobs:
  # Gate the (slow) platform builds on the headless test suite.
  test:
    name: Test (headless)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - name: Install Qt system libraries
        run: |
          sudo apt-get update -qq
          sudo apt-get install -y -qq \\
            libegl1 libgl1 libglx-mesa0 libxkbcommon0 libxkbcommon-x11-0 \\
            libdbus-1-3 libfontconfig1 libxrender1 libxcb-cursor0
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          # sciappkit is not on PyPI yet — install from git first so the
          # app's `sciappkit>=0.1` requirement resolves. Drop this line
          # once sciappkit is published.
          pip install "sciappkit @ git+https://github.com/w00ber/scikit-app"
          pip install -e ".[dev]"
      - name: Run tests
        run: QT_QPA_PLATFORM=offscreen pytest

  build:
    name: Build (${{ matrix.name }})
    needs: test
    strategy:
      fail-fast: false
      matrix:
        include:
          - os: macos-latest
            name: macOS
            artifact: __PKG__-macOS
          - os: windows-latest
            name: Windows
            artifact: __PKG__-Windows
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pyinstaller
          pip install "sciappkit @ git+https://github.com/w00ber/scikit-app"
          pip install -e .

      # Windows executable icon: build a .ico from the PNG ladder.
      - name: Generate Windows icon
        if: runner.os == 'Windows'
        shell: python
        run: |
          import os, subprocess, sys
          subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
          from PIL import Image
          icon_dir = os.path.join("src", "__PKG__", "icons")
          images = [
              Image.open(os.path.join(icon_dir, f"icon_{s}x{s}.png"))
              for s in (16, 32, 128, 256)
              if os.path.exists(os.path.join(icon_dir, f"icon_{s}x{s}.png"))
          ]
          if images:
              images[0].save(
                  "__PKG__.ico", format="ICO",
                  sizes=[(i.width, i.height) for i in images],
                  append_images=images[1:],
              )
              print("Created __PKG__.ico")
          else:
              print("No iconset PNGs found; building without a Windows icon")

      - name: Build with PyInstaller
        run: pyinstaller __PKG__.spec

      - name: Package macOS app
        if: runner.os == 'macOS'
        run: |
          cd dist
          zip -r -y "../__PKG__-macOS.zip" *.app
      - name: Package Windows app
        if: runner.os == 'Windows'
        shell: pwsh
        run: Compress-Archive -Path "dist\\__PKG__" -DestinationPath "__PKG__-Windows.zip"

      - name: Upload build artifact
        uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.artifact }}
          path: |
            __PKG__-macOS.zip
            __PKG__-Windows.zip
          if-no-files-found: ignore

  # Single release writer. The matrix jobs above only upload workflow
  # artifacts; this one job attaches every zip in a single call. Two known
  # traps this avoids (both hit by this framework's ancestor apps):
  #   * per-platform release steps racing to mutate the same release — an
  #     upload can 404 during finalize and get silently dropped;
  #   * parallel `gh release create --draft` calls each spawning a fresh
  #     draft (drafts have no realized tag ref to deduplicate on).
  # `needs: build` also means one failed platform blocks the release
  # instead of shipping it partially.
  release:
    name: Attach builds to release
    needs: build
    if: startsWith(github.ref, 'refs/tags/') || github.event.inputs.release_tag != ''
    runs-on: ubuntu-latest
    steps:
      - name: Download all build artifacts
        uses: actions/download-artifact@v4
        with:
          path: artifacts
          pattern: __PKG__-*
          merge-multiple: true
      - name: Attach to release
        uses: softprops/action-gh-release@v2
        with:
          tag_name: ${{ github.event.inputs.release_tag || github.ref_name }}
          files: artifacts/*.zip
          fail_on_unmatched_files: true
          # Generate notes only for genuine tag pushes; a manual re-attach
          # must never overwrite a hand-written release body.
          generate_release_notes: ${{ startsWith(github.ref, 'refs/tags/') }}
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
    include_skill: bool = True,
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
    include_skill: copy the bundled ``sciapp`` Claude Code skill into the
        project's ``.claude/skills/sciapp/`` so Claude Code can assist with
        framework work out of the box.

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
        src / "icons" / "README.md": _ICONS_README,
        project / f"{pkg}_launcher.py": _LAUNCHER,
        project / f"{pkg}.spec": _SPEC,
        project / ".github" / "workflows" / "build.yml": _BUILD_YML,
        project / "docs" / "help.md": _HELP_MD,
        project / "docs" / "tutorial.md": _TUTORIAL_MD,
        project / "tests" / "test_app.py": _TEST_APP,
    }

    for path, template in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_render(template, mapping), encoding="utf-8")

    if include_skill:
        _copy_skill(project)

    return project


def _copy_skill(project: Path) -> None:
    """Copy the bundled ``sciapp`` Claude Code skill into *project*.

    The skill ships as package data (``sciappkit/scaffold/skill/``) and is
    copied verbatim — no token rendering, it documents the framework, not
    the generated app. Best effort: a missing/partial resource logs a
    warning instead of failing the scaffold.
    """
    from importlib import resources

    try:
        skill_root = resources.files("sciappkit.scaffold") / "skill"
        if not skill_root.is_dir():
            raise FileNotFoundError("bundled skill directory not found")
        dest_root = project / ".claude" / "skills" / "sciapp"

        def _copy_tree(src, dest: Path) -> None:
            for entry in src.iterdir():
                if entry.name == "__pycache__":
                    continue
                target = dest / entry.name
                if entry.is_dir():
                    _copy_tree(entry, target)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(entry.read_bytes())

        _copy_tree(skill_root, dest_root)
    except Exception:
        logger.warning(
            "Could not copy the bundled sciapp skill into %s — the app is "
            "complete, but Claude Code won't have the skill preinstalled.",
            project, exc_info=True,
        )
