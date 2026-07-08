"""Tests for sciappkit.canvas.mpl_canvas."""

from __future__ import annotations

from sciappkit.canvas.mpl_canvas import MplCanvas


def test_canvas_constructs_graph_mode(qapp):
    canvas = MplCanvas(width=4, height=3, dpi=80, show_axes=False)
    assert canvas.fig is not None
    assert canvas.ax is not None
    # Graph mode fills the figure: axes positioned at [0, 0, 1, 1].
    pos = canvas.ax.get_position()
    assert pos.x0 == 0 and pos.y0 == 0
    assert pos.width == 1 and pos.height == 1


def test_canvas_constructs_plot_mode(qapp):
    canvas = MplCanvas(width=4, height=3, dpi=80, show_axes=True)
    assert canvas.ax is not None


def test_signals_emit_on_mpl_event(qapp):
    canvas = MplCanvas(show_axes=True)
    received = []
    canvas.click_signal.connect(received.append)

    sentinel = object()
    canvas._on_click(sentinel)
    assert received == [sentinel]
