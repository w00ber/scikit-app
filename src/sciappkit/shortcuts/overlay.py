"""Floating, context-sensitive keyboard-shortcut hint panel.

An optional on-canvas cheat sheet that lowers the learning curve for a
keyboard-driven workflow: it shows a curated (or registry-derived) set of
shortcut hints in a chosen corner of a host widget.

The panel (:class:`ShortcutOverlay`) is a plain Qt widget parented to a host
widget (typically a ``QGraphicsView`` viewport or a matplotlib canvas), so it
is layered *over* the drawing surface but is never part of the scene/figure --
it can't appear in PNG/SVG/PDF exports or "copy as image" clipboard copies,
which are rendered from the scene, not from the view's child widgets. It
repositions itself when the host resizes and never takes focus, so it never
interferes with typing or single-key shortcuts.

The widget is content-agnostic: the caller feeds it ``(keys, label)`` rows via
:meth:`ShortcutOverlay.set_rows`. Two convenience layers sit on top:

* :class:`ShortcutOverlayMixin` — the shared toggle / reposition / update
  wiring that both source apps (Diagrammer, graphulator) duplicated, factored
  into an app-agnostic mixin. A window subclasses it and supplies a host widget
  and the rows for the current context.
* :func:`overlay_rows_from_registry` — builds a zero-curation "all shortcuts"
  cheat sheet straight from a :class:`~sciappkit.shortcuts.model.ShortcutRegistry`,
  so bindings (and any user rebindings) are reflected automatically.

Lifted from Diagrammer's ``panels/shortcut_overlay.py`` (the newer copy, with
the ``_relayout`` first-show cropping fix) and generalized.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Iterable

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .model import ShortcutRegistry

logger = logging.getLogger(__name__)

__all__ = ["ShortcutOverlay", "ShortcutOverlayMixin", "overlay_rows_from_registry"]

# Corner keyword -> (anchor to the right?, anchor to the bottom?)
_CORNERS = {
    "top-left": (False, False),
    "top-right": (True, False),
    "bottom-left": (False, True),
    "bottom-right": (True, True),
}

_MARGIN = 12  # px inset from the host edge


class ShortcutOverlay(QWidget):
    """A small translucent panel of context-relevant shortcut hints."""

    def __init__(self, host: QWidget):
        super().__init__(host)
        self._host = host
        self._corner = "top-right"
        self.setObjectName("shortcutOverlay")
        # Never steal focus (matches the canvas), so single-key shortcuts and
        # text fields keep working while it is visible.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(0)
        self._label = QLabel(self)
        self._label.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._label.setTextFormat(Qt.TextFormat.RichText)
        # Pin the text dark: the panel background is always light, so without
        # this the text follows the system palette and turns white (unreadable)
        # under macOS dark/night mode.
        self._label.setStyleSheet("color: #111111;")
        layout.addWidget(self._label)

        # objectName-scoped stylesheet so it doesn't bleed onto child labels of
        # other widgets; translucent so the canvas shows through faintly.
        self.setStyleSheet(
            "#shortcutOverlay {"
            "  background-color: rgba(250, 250, 250, 235);"
            "  border: 1px solid rgba(0, 0, 0, 40);"
            "  border-radius: 8px;"
            "}"
        )
        # Reposition whenever the host resizes.
        host.installEventFilter(self)
        self.hide()

    # ---- public API ---------------------------------------------------

    def set_corner(self, corner: str) -> None:
        """Set the anchor corner ('top-left'|'top-right'|'bottom-left'|'bottom-right')."""
        if corner in _CORNERS:
            self._corner = corner
            self._reposition()

    def set_rows(self, title: str, rows) -> None:
        """Populate with a context title and ``[(keys, label), ...]`` rows.

        Hides the panel when there are no rows.
        """
        if not rows:
            self.hide()
            return
        body = "".join(
            "<tr>"
            f"<td style='padding:1px 10px 1px 0; white-space:nowrap;'>"
            f"<span style='font-family:monospace; font-weight:bold;'>{keys}</span></td>"
            f"<td style='padding:1px 0;'>{label}</td>"
            "</tr>"
            for keys, label in rows
        )
        html = (
            f"<div style='font-weight:bold; padding-bottom:4px;'>{title}</div>"
            f"<table style='border-collapse:collapse;'>{body}</table>"
        )
        self._label.setText(html)
        self.adjustSize()
        self._clamp_to_parent()
        self._reposition()

    def _clamp_to_parent(self) -> None:
        """Keep the panel within the host so a long list can't spill off-screen;
        content taller than the host is clipped at the bottom."""
        parent = self.parentWidget()
        if parent is None:
            return
        max_h = max(60, parent.height() - 2 * _MARGIN)
        max_w = max(60, parent.width() - 2 * _MARGIN)
        if self.height() > max_h or self.width() > max_w:
            self.resize(min(self.width(), max_w), min(self.height(), max_h))

    # ---- internals ----------------------------------------------------

    def _reposition(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        right, bottom = _CORNERS.get(self._corner, (True, False))
        pw, ph = parent.width(), parent.height()
        w, h = self.width(), self.height()
        x = pw - w - _MARGIN if right else _MARGIN
        y = ph - h - _MARGIN if bottom else _MARGIN
        self.move(max(_MARGIN, x), max(_MARGIN, y))

    def _relayout(self) -> None:
        """Re-expand to the content's natural size for the current parent
        bounds, then clamp and reposition.

        The adjustSize() is essential: if the panel was clamped to a smaller
        size while the parent was still tiny (e.g. during window construction,
        before the host has its real size), a bare reposition would leave it
        cropped. Re-running adjustSize() recomputes the full size from the
        label content so it grows back once the parent is large enough."""
        self.adjustSize()
        self._clamp_to_parent()
        self._reposition()

    def eventFilter(self, obj, event):
        # Guard with getattr: during teardown the host can deliver a final
        # Resize after this widget's Python attributes are already cleared.
        if obj is getattr(self, "_host", None) and event.type() == QEvent.Type.Resize:
            self._relayout()
        return super().eventFilter(obj, event)

    def showEvent(self, event):
        super().showEvent(event)
        self._relayout()
        self.raise_()


class ShortcutOverlayMixin:
    """Shared toggle / reposition / update wiring for a :class:`ShortcutOverlay`.

    Factors out the ``_init/_toggle/_update/_apply`` boilerplate that
    Diagrammer's ``MainWindow`` and graphulator's ``GraphWindowCommonMixin``
    each duplicated. A window mixes this in and provides two hooks:

    * :meth:`shortcut_overlay_host` — the widget to parent the overlay to
      (e.g. a ``QGraphicsView`` viewport or a matplotlib canvas). **Required.**
    * :meth:`shortcut_overlay_rows` — the ``(title, rows)`` to show for the
      current context, where each row is ``(keys_text, label)``. Override to
      supply curated per-selection hints; the default shows nothing.

    Enabled state is kept in memory. Persistence (which settings key stores the
    on/off flag and the corner) is left to the app, since those keys differ per
    app — call :meth:`init_shortcut_overlay` with the restored values and
    :meth:`toggle_shortcut_overlay` / :meth:`set_shortcut_overlay_corner` from
    the app's settings-applied handler.
    """

    def init_shortcut_overlay(self, *, corner: str = "top-right", enabled: bool = False) -> ShortcutOverlay:
        """Create the overlay over :meth:`shortcut_overlay_host` and return it."""
        overlay = ShortcutOverlay(self.shortcut_overlay_host())
        overlay.set_corner(corner)
        self._shortcut_overlay = overlay
        self._shortcut_overlay_enabled = bool(enabled)
        if self._shortcut_overlay_enabled:
            self.update_shortcut_overlay()
        return overlay

    # -- hooks the subclass provides ---------------------------------------

    def shortcut_overlay_host(self) -> QWidget:
        """Return the widget the overlay should be parented to (required)."""
        raise NotImplementedError

    def shortcut_overlay_rows(self) -> tuple[str, list[tuple[str, str]]]:
        """Return ``(title, rows)`` for the current context (override me)."""
        return ("", [])

    # -- state / accessors -------------------------------------------------

    @property
    def shortcut_overlay(self) -> ShortcutOverlay | None:
        return getattr(self, "_shortcut_overlay", None)

    @property
    def shortcut_overlay_enabled(self) -> bool:
        return getattr(self, "_shortcut_overlay_enabled", False)

    # -- commands ----------------------------------------------------------

    def set_shortcut_overlay_corner(self, corner: str) -> None:
        overlay = self.shortcut_overlay
        if overlay is not None:
            overlay.set_corner(corner)

    def toggle_shortcut_overlay(self, enabled: bool | None = None) -> None:
        """Turn the overlay on/off. With no argument, flips the current state."""
        overlay = self.shortcut_overlay
        if overlay is None:
            return
        self._shortcut_overlay_enabled = (
            not self.shortcut_overlay_enabled if enabled is None else bool(enabled)
        )
        if self._shortcut_overlay_enabled:
            self.update_shortcut_overlay()
        else:
            overlay.hide()

    def update_shortcut_overlay(self) -> None:
        """Refresh the displayed rows from :meth:`shortcut_overlay_rows`.

        A no-op while the overlay is disabled. ``set_rows`` hides the panel
        when there are no rows for the current context.
        """
        overlay = self.shortcut_overlay
        if overlay is None or not self.shortcut_overlay_enabled:
            return
        title, rows = self.shortcut_overlay_rows()
        overlay.set_rows(title, rows)
        if rows:
            overlay.show()


def overlay_rows_from_registry(
    registry: "ShortcutRegistry",
    categories: Iterable[str] | None = None,
    platform: str | None = None,
) -> list[tuple[str, str]]:
    """Build ``[(display_text, display_name), ...]`` rows from a registry.

    A zero-curation "all shortcuts" cheat sheet: every shortcut that resolves
    to a non-empty key on *platform* (defaults to the registry's platform),
    grouped by category in registry order. Pass *categories* to restrict to a
    subset. Rebindings are reflected because ``display_text`` reads the active
    (override-aware) sequence.
    """
    plat = platform or registry.platform
    wanted = set(categories) if categories is not None else None
    rows: list[tuple[str, str]] = []
    for category, shortcuts in registry.by_category().items():
        if wanted is not None and category not in wanted:
            continue
        for sc in shortcuts:
            keys = sc.display_text(plat)
            if keys:
                rows.append((keys, sc.display_name))
    return rows
