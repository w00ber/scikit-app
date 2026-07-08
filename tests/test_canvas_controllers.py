"""Tests for sciappkit.canvas scene_canvas + protocol/adapters."""

from __future__ import annotations

from sciappkit.canvas.protocol import (
    CanvasController,
    MplCanvasController,
    SceneCanvasController,
)
from sciappkit.canvas.scene_canvas import GraphicsSceneBase, GraphicsViewBase


# -- GraphicsSceneBase ------------------------------------------------------

def test_scene_undo_stack_and_mode_signal(qapp):
    scene = GraphicsSceneBase()
    assert scene.undo_stack is not None

    seen = []
    scene.mode_changed.connect(seen.append)
    scene.mode = "connect"
    scene.mode = "connect"  # no re-emit for same value
    scene.mode = "select"
    assert seen == ["connect", "select"]
    assert scene.mode == "select"


# -- GraphicsViewBase -------------------------------------------------------

def _view(qapp):
    scene = GraphicsSceneBase()
    scene.addRect(0, 0, 100, 80)
    view = GraphicsViewBase(scene)
    view.resize(400, 300)
    return view, scene


def test_view_retains_scene_reference(qapp):
    # Regression: QGraphicsView does not hold a Python ref to its scene, so
    # a scene not otherwise retained would be garbage-collected. The base
    # must keep it alive.
    import gc

    def make_view():
        scene = GraphicsSceneBase()
        scene.addRect(0, 0, 10, 10)
        return GraphicsViewBase(scene)  # scene local goes out of scope here

    view = make_view()
    gc.collect()
    assert view.scene() is not None
    assert view.scene().itemsBoundingRect().width() > 0


def test_view_zoom_in_out_clamped(qapp):
    view, _ = _view(qapp)
    start = view.current_scale()
    view.zoom_in()
    assert view.current_scale() > start
    view.zoom_reset()
    assert abs(view.current_scale() - 1.0) < 1e-9

    # Clamp at the maximum.
    for _ in range(100):
        view.zoom_in()
    assert view.current_scale() <= view.ZOOM_MAX + 1e-6

    # Clamp at the minimum.
    for _ in range(200):
        view.zoom_out()
    assert view.current_scale() >= view.ZOOM_MIN - 1e-6


def test_view_forwards_scene_mode(qapp):
    view, scene = _view(qapp)
    seen = []
    view.mode_changed.connect(seen.append)
    view.set_interaction_mode("draw")
    assert seen == ["draw"]
    assert view.interaction_mode() == "draw"


def test_view_grid_and_snap(qapp):
    view, _ = _view(qapp)
    from PySide6.QtCore import QPointF

    assert view.grid_visible is True
    view.grid_visible = False
    assert view.grid_visible is False

    view.grid_spacing = 20.0
    snapped = view.snap(QPointF(23, 17))
    assert (snapped.x(), snapped.y()) == (20.0, 20.0)
    view.snap_enabled = False
    assert view.snap(QPointF(23, 17)) == QPointF(23, 17)


def test_view_fit_to_content_runs(qapp):
    view, _ = _view(qapp)
    view.fit_to_content()  # should not raise with content present
    # Empty scene is a no-op (no raise). Hold a reference so the scene
    # isn't garbage-collected (the view does not own it).
    empty_scene = GraphicsSceneBase()
    GraphicsViewBase(empty_scene).fit_to_content()


# -- controllers / protocol -------------------------------------------------

def test_scene_controller_conforms_and_delegates(qapp):
    view, scene = _view(qapp)
    ctrl = SceneCanvasController(view)
    assert isinstance(ctrl, CanvasController)
    assert ctrl.widget() is view
    assert ctrl.export_target() is scene

    seen = []
    ctrl.mode_changed.connect(seen.append)
    ctrl.set_interaction_mode("connect")
    assert seen == ["connect"]
    assert ctrl.interaction_mode() == "connect"

    from sciappkit.export.scene_exporter import SceneExporter

    assert isinstance(ctrl.exporter, SceneExporter)


def test_mpl_controller_conforms_and_delegates(qapp):
    from sciappkit.canvas.mpl_canvas import MplCanvas
    from sciappkit.export.mpl_exporter import MplExporter

    canvas = MplCanvas(show_axes=True)
    ctrl = MplCanvasController(canvas)
    assert isinstance(ctrl, CanvasController)
    assert ctrl.widget() is canvas
    assert ctrl.export_target() is canvas.fig
    assert isinstance(ctrl.exporter, MplExporter)

    seen = []
    ctrl.mode_changed.connect(seen.append)
    ctrl.set_interaction_mode("pan")
    ctrl.set_interaction_mode("pan")  # no re-emit
    assert seen == ["pan"]
    ctrl.fit_to_content()  # should not raise


def test_controller_export_roundtrip_via_protocol(qapp, tmp_path):
    # The host pattern: getattr(ctrl.exporter, f"export_{fmt}")(ctrl.export_target(), path)
    view, _ = _view(qapp)
    ctrl = SceneCanvasController(view)
    path = tmp_path / "via_ctrl.png"
    ctrl.exporter.export_png(ctrl.export_target(), str(path))
    assert path.exists() and path.stat().st_size > 0
