"""Keyboard shortcut system (per-app registry + manager).

Submodules stay importable directly; this package re-exports the public
surface for convenience:

* :mod:`~sciappkit.shortcuts.model` — :class:`Shortcut`, :class:`ShortcutRegistry`
* :mod:`~sciappkit.shortcuts.manager` — :class:`ShortcutManager`
* :mod:`~sciappkit.shortcuts.editor` — :class:`ShortcutEditorWidget` (rebinding UI)
* :mod:`~sciappkit.shortcuts.overlay` — :class:`ShortcutOverlay` (on-canvas cheat
  sheet), :class:`ShortcutOverlayMixin`, :func:`overlay_rows_from_registry`
"""

from .editor import ShortcutEditorWidget
from .manager import ShortcutManager
from .model import Shortcut, ShortcutRegistry, native_text, portable_text
from .overlay import ShortcutOverlay, ShortcutOverlayMixin, overlay_rows_from_registry

__all__ = [
    "Shortcut",
    "ShortcutRegistry",
    "ShortcutManager",
    "ShortcutEditorWidget",
    "ShortcutOverlay",
    "ShortcutOverlayMixin",
    "overlay_rows_from_registry",
    "native_text",
    "portable_text",
]
