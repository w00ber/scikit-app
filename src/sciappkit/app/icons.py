"""Application icon loading (multi-resolution, macOS-friendly).

Lifted from Diagrammer's ``app.py``. The pattern that makes icons "just
work" on macOS — including the Dock icon for a plain ``python app.py``
run, no ``.app`` bundle required — is a single :class:`QIcon` fed every
size of a macOS-style iconset ladder::

    icons/
        icon_16x16.png      icon_16x16@2x.png
        icon_32x32.png      icon_32x32@2x.png
        icon_128x128.png    icon_128x128@2x.png
        icon_256x256.png    icon_256x256@2x.png
        icon_512x512.png    icon_512x512@2x.png

Qt then picks the right resolution per context (title bar, Dock, Cmd-Tab,
taskbar), and ``QApplication.setWindowIcon`` applies it everywhere at
runtime. A real ``.icns`` file is only needed when freezing a macOS
``.app`` bundle (e.g. PyInstaller's ``BUNDLE(icon=...)``) so Finder shows
the icon before the process starts; this loader covers everything else.

Generate the ladder from a single 1024×1024 master on macOS with ``sips``::

    for s in 16 32 128 256 512; do
        sips -z $s $s master.png --out icons/icon_${s}x${s}.png
        sips -z $((s*2)) $((s*2)) master.png --out icons/icon_${s}x${s}@2x.png
    done
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtGui import QIcon

logger = logging.getLogger(__name__)

__all__ = ["load_app_icon", "set_app_icon"]


def load_app_icon(icons_dir: str | Path, pattern: str = "icon_*.png") -> QIcon:
    """Build a multi-resolution :class:`QIcon` from PNGs in *icons_dir*.

    Every file matching *pattern* is added to one ``QIcon`` so Qt can pick
    the best size per context. Returns a null ``QIcon`` (``icon.isNull()``)
    if the directory is missing or matches nothing — safe to pass to
    ``setWindowIcon`` either way, so callers need no guard.
    """
    icon = QIcon()
    icons_dir = Path(icons_dir)
    if icons_dir.is_dir():
        for png in sorted(icons_dir.glob(pattern)):
            icon.addFile(str(png))
    if icon.isNull():
        logger.debug("No app icons found in %s (pattern %r)", icons_dir, pattern)
    return icon


def set_app_icon(app, icons_dir: str | Path, pattern: str = "icon_*.png") -> QIcon:
    """Load the iconset and apply it as *app*'s window icon.

    On macOS this also sets the Dock icon at runtime. A null icon (nothing
    found) is not applied, preserving any platform default. Returns the
    loaded icon so callers can reuse it (e.g. for an About dialog).
    """
    icon = load_app_icon(icons_dir, pattern)
    if not icon.isNull():
        app.setWindowIcon(icon)
    return icon
