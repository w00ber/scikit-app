"""Tests for sciappkit.canvas.grid."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QImage, QPainter

from sciappkit.canvas import grid


def test_snap_to_grid_rounds_to_nearest():
    snapped = grid.snap_to_grid(QPointF(23.0, 17.0), 20.0)
    assert (snapped.x(), snapped.y()) == (20.0, 20.0)

    snapped = grid.snap_to_grid(QPointF(31.0, 9.0), 20.0)
    assert (snapped.x(), snapped.y()) == (40.0, 0.0)


def test_snap_to_grid_exact_point_is_stable():
    snapped = grid.snap_to_grid(QPointF(40.0, -60.0), 20.0)
    assert (snapped.x(), snapped.y()) == (40.0, -60.0)


def test_draw_grid_runs_on_painter(qapp):
    image = QImage(100, 100, QImage.Format.Format_ARGB32)
    image.fill(0)
    painter = QPainter(image)
    try:
        grid.draw_grid(painter, QRectF(0, 0, 100, 100), spacing=20.0, scale=1.0)
    finally:
        painter.end()
    # The grid lines should have painted at least one non-transparent pixel.
    assert any(image.pixelColor(x, 0).alpha() > 0 for x in range(100))


def test_draw_grid_skipped_when_too_dense(qapp):
    image = QImage(100, 100, QImage.Format.Format_ARGB32)
    image.fill(0)
    painter = QPainter(image)
    try:
        # spacing * scale = 20 * 0.1 = 2 px < MIN_GRID_SPACING_PX -> nothing drawn
        grid.draw_grid(painter, QRectF(0, 0, 100, 100), spacing=20.0, scale=0.1)
    finally:
        painter.end()
    assert all(
        image.pixelColor(x, y).alpha() == 0
        for x in range(0, 100, 10)
        for y in range(0, 100, 10)
    )
