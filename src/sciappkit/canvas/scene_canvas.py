"""Generic QGraphicsScene / QGraphicsView base classes.

The reusable ~300 lines extracted from Diagrammer's canvas, with all the
app-specific logic (connections, ports, junctions, waypoints, groups,
component placement) left behind. What stays is the genuinely generic
machinery: an undo stack + interaction-mode signal on the scene, and
zoom / pan / fit-to-content / grid drawing / interaction-mode plumbing on
the view.

The deliberate non-goal (per the design plan) is to *not* unify the two
canvases under one base — apps subclass :class:`GraphicsViewBase` and add
their own interaction, while a matplotlib app uses
:class:`~sciappkit.canvas.mpl_canvas.MplCanvas` instead. Grid drawing is
wired to :mod:`sciappkit.canvas.grid`; colors are passed in rather than
read from any app's settings.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView, QWidget

from .grid import DEFAULT_GRID_SPACING, draw_grid, snap_to_grid

# Default scene rect — large enough that panning feels unbounded.
_DEFAULT_SCENE_RECT = (-5000.0, -5000.0, 10000.0, 10000.0)


class GraphicsSceneBase(QGraphicsScene):
    """A ``QGraphicsScene`` with an undo stack and an interaction-mode signal.

    ``mode`` is generic over any value (apps typically use an ``Enum``);
    assigning a new value emits :attr:`mode_changed`.
    """

    mode_changed = Signal(object)

    def __init__(self, parent=None, *, scene_rect: tuple[float, float, float, float] | None = None) -> None:
        super().__init__(parent)
        from PySide6.QtGui import QUndoStack

        self._undo_stack = QUndoStack(self)
        self.setSceneRect(*(scene_rect or _DEFAULT_SCENE_RECT))
        self._mode: object = None

    @property
    def undo_stack(self):
        return self._undo_stack

    @property
    def mode(self) -> object:
        return self._mode

    @mode.setter
    def mode(self, value: object) -> None:
        if value != self._mode:
            self._mode = value
            self.mode_changed.emit(value)


class GraphicsViewBase(QGraphicsView):
    """A ``QGraphicsView`` with zoom, pan, fit-to-content, and grid drawing.

    Subclasses add their own interaction (item dragging, selection
    semantics, etc.). Zoom keeps the point under the cursor fixed; the
    middle mouse button pans; the grid is drawn in :meth:`drawBackground`.
    """

    #: Forwarded from the scene's ``mode_changed`` when the scene provides one.
    mode_changed = Signal(object)

    ZOOM_MIN = 0.05
    ZOOM_MAX = 20.0
    ZOOM_FACTOR = 1.15

    def __init__(
        self,
        scene: QGraphicsScene,
        parent: QWidget | None = None,
        *,
        grid_spacing: float = DEFAULT_GRID_SPACING,
        grid_visible: bool = True,
        snap_enabled: bool = True,
    ) -> None:
        super().__init__(scene, parent)
        # QGraphicsView does not take a Python reference to its scene, so a
        # scene not otherwise retained by the caller would be garbage
        # collected and ``self.scene()`` would become None. Hold a strong
        # reference to prevent that footgun.
        self._scene_ref = scene
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)

        self._grid_spacing = grid_spacing
        self._grid_visible = grid_visible
        self._snap_enabled = snap_enabled
        self._minor_grid_color: QColor | None = None
        self._major_grid_color: QColor | None = None
        self._panning = False
        self._pan_start = QPointF()

        if hasattr(scene, "mode_changed"):
            scene.mode_changed.connect(self.mode_changed)

    # -- zoom ---------------------------------------------------------------

    def current_scale(self) -> float:
        return self.transform().m11()

    def zoom_at(self, factor: float, scene_pos: QPointF) -> None:
        """Zoom by *factor*, keeping *scene_pos* fixed under the cursor."""
        current = self.current_scale()
        clamped = max(self.ZOOM_MIN, min(self.ZOOM_MAX, current * factor))
        factor = clamped / current
        if abs(factor - 1.0) < 1e-9:
            return
        before = self.mapFromScene(scene_pos)
        self.scale(factor, factor)
        after = self.mapFromScene(scene_pos)
        delta = after - before
        # Scrollbars are hidden but still drive the scroll offset.
        self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() + delta.x())
        self.verticalScrollBar().setValue(self.verticalScrollBar().value() + delta.y())

    def zoom_centered(self, factor: float) -> None:
        center = self.mapToScene(self.viewport().rect().center())
        self.zoom_at(factor, center)

    def zoom_in(self) -> None:
        self.zoom_centered(self.ZOOM_FACTOR)

    def zoom_out(self) -> None:
        self.zoom_centered(1.0 / self.ZOOM_FACTOR)

    def zoom_reset(self) -> None:
        self.resetTransform()

    def wheelEvent(self, event) -> None:
        # Discrete mouse wheel zooms toward the cursor; trackpad two-finger
        # scroll (pixelDelta) pans.
        if not event.pixelDelta().isNull():
            d = event.pixelDelta()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - d.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - d.y())
            event.accept()
            return
        delta = event.angleDelta().y()
        if delta == 0:
            return
        factor = self.ZOOM_FACTOR if delta > 0 else 1.0 / self.ZOOM_FACTOR
        self.zoom_at(factor, self.mapToScene(event.position().toPoint()))
        event.accept()

    # -- fit ----------------------------------------------------------------

    def fit_to_content(self, *, margin_fraction: float = 0.1) -> None:
        """Scale/pan so all scene items are visible with a small margin."""
        scene = self.scene()
        if scene is None:
            return
        rect = scene.itemsBoundingRect()
        if rect.isNull() or rect.isEmpty():
            return
        margin = max(rect.width(), rect.height()) * margin_fraction
        self.fitInView(
            rect.adjusted(-margin, -margin, margin, margin),
            Qt.AspectRatioMode.KeepAspectRatio,
        )

    # -- pan (middle mouse) -------------------------------------------------

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self._begin_pan(event.position())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._panning:
            self._update_pan(event.position())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.MiddleButton and self._panning:
            self._end_pan()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _begin_pan(self, pos: QPointF) -> None:
        self._panning = True
        self._pan_start = pos
        self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def _update_pan(self, pos: QPointF) -> None:
        delta = pos - self._pan_start
        self._pan_start = pos
        self.horizontalScrollBar().setValue(int(self.horizontalScrollBar().value() - delta.x()))
        self.verticalScrollBar().setValue(int(self.verticalScrollBar().value() - delta.y()))

    def _end_pan(self) -> None:
        self._panning = False
        self.unsetCursor()

    # -- interaction mode ---------------------------------------------------

    def set_interaction_mode(self, mode: object) -> None:
        scene = self.scene()
        if hasattr(scene, "mode"):
            scene.mode = mode  # emits scene.mode_changed -> forwarded
        else:
            self.mode_changed.emit(mode)

    def interaction_mode(self) -> object:
        scene = self.scene()
        return scene.mode if hasattr(scene, "mode") else None

    # -- grid + snap --------------------------------------------------------

    @property
    def grid_spacing(self) -> float:
        return self._grid_spacing

    @grid_spacing.setter
    def grid_spacing(self, value: float) -> None:
        self._grid_spacing = value
        self.viewport().update()

    @property
    def grid_visible(self) -> bool:
        return self._grid_visible

    @grid_visible.setter
    def grid_visible(self, value: bool) -> None:
        self._grid_visible = value
        self.viewport().update()

    @property
    def snap_enabled(self) -> bool:
        return self._snap_enabled

    @snap_enabled.setter
    def snap_enabled(self, value: bool) -> None:
        self._snap_enabled = value

    def set_grid_colors(self, minor: QColor | None, major: QColor | None) -> None:
        """Override grid colors (e.g. to follow the active theme)."""
        self._minor_grid_color = minor
        self._major_grid_color = major
        self.viewport().update()

    def snap(self, pos: QPointF) -> QPointF:
        """Snap *pos* to the grid if snapping is enabled."""
        if self._snap_enabled:
            return snap_to_grid(pos, self._grid_spacing)
        return pos

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        super().drawBackground(painter, rect)
        if self._grid_visible:
            draw_grid(
                painter, rect, self._grid_spacing, self.current_scale(),
                minor_color=self._minor_grid_color,
                major_color=self._major_grid_color,
            )
