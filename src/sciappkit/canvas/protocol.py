"""The canvas controller abstraction and its two adapters.

The core design decision from the plan: do **not** unify the matplotlib
canvas and the QGraphicsScene canvas under one base class. Instead, a thin
:class:`CanvasController` protocol lets a host (e.g.
:class:`sciappkit.app.main_window.SciAppMainWindow`) drive either kind —
embed it, export it, fit it, switch its interaction mode — without knowing
which it is. Two adapters implement the protocol:

* :class:`MplCanvasController` wraps a
  :class:`~sciappkit.canvas.mpl_canvas.MplCanvas` (export target = the
  ``Figure``, paired with :class:`~sciappkit.export.mpl_exporter.MplExporter`).
* :class:`SceneCanvasController` wraps a ``QGraphicsView`` (export target =
  the ``QGraphicsScene``, paired with
  :class:`~sciappkit.export.scene_exporter.SceneExporter`).

An app can dock a scene editor *and* a matplotlib plot panel and the same
Export/Copy menu drives whichever has focus.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QWidget

from ..export.mpl_exporter import MplExporter
from ..export.scene_exporter import SceneExporter


@runtime_checkable
class CanvasController(Protocol):
    """Uniform handle over one canvas (matplotlib or QGraphicsScene)."""

    #: The exporter paired with this canvas (an
    #: :class:`sciappkit.export.base.Exporter`).
    exporter: Any
    #: Emitted when the interaction mode changes.
    mode_changed: Signal

    def widget(self) -> QWidget:
        """Return the embeddable ``QWidget`` for this canvas."""
        ...

    def export_target(self) -> Any:
        """Return what the paired exporter consumes (Figure or scene)."""
        ...

    def fit_to_content(self) -> None:
        """Scale/pan so all content is visible."""
        ...

    def set_interaction_mode(self, mode: object) -> None:
        """Switch the active interaction mode (app-defined value)."""
        ...


class MplCanvasController(QObject):
    """:class:`CanvasController` for a matplotlib canvas."""

    mode_changed = Signal(object)

    def __init__(self, canvas, exporter: MplExporter | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._canvas = canvas
        self.exporter = exporter or MplExporter()
        self._mode: object = None

    def widget(self) -> QWidget:
        return self._canvas

    def export_target(self):
        # MplCanvas exposes the Figure as ``.fig``.
        return self._canvas.fig

    def fit_to_content(self) -> None:
        for ax in self._canvas.fig.get_axes():
            ax.relim()
            ax.autoscale()
        self._canvas.draw_idle()

    def set_interaction_mode(self, mode: object) -> None:
        if mode != self._mode:
            self._mode = mode
            self.mode_changed.emit(mode)

    def interaction_mode(self) -> object:
        return self._mode


class SceneCanvasController(QObject):
    """:class:`CanvasController` for a ``QGraphicsView`` + scene."""

    mode_changed = Signal(object)

    def __init__(self, view, exporter: SceneExporter | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._view = view
        self.exporter = exporter or SceneExporter()
        # Forward the view's (or scene's) mode_changed so a host can listen
        # on the controller uniformly.
        if hasattr(view, "mode_changed"):
            view.mode_changed.connect(self.mode_changed)
        elif hasattr(view.scene(), "mode_changed"):
            view.scene().mode_changed.connect(self.mode_changed)

    def widget(self) -> QWidget:
        return self._view

    def export_target(self):
        return self._view.scene()

    def fit_to_content(self) -> None:
        self._view.fit_to_content()

    def set_interaction_mode(self, mode: object) -> None:
        if hasattr(self._view, "set_interaction_mode"):
            self._view.set_interaction_mode(mode)
        else:
            scene = self._view.scene()
            if hasattr(scene, "mode"):
                scene.mode = mode

    def interaction_mode(self) -> object:
        if hasattr(self._view, "interaction_mode"):
            return self._view.interaction_mode()
        scene = self._view.scene()
        return scene.mode if hasattr(scene, "mode") else None
