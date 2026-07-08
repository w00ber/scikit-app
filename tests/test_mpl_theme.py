"""Tests for matplotlib light/dark theming."""

from __future__ import annotations

from sciappkit.canvas.mpl_theme import (
    DARK_CHROME,
    LIGHT_CHROME,
    apply_mpl_theme,
    chrome_for,
)


def _figure():
    from matplotlib.figure import Figure

    fig = Figure()
    ax = fig.add_subplot(111)
    (line,) = ax.plot([0, 1, 2], [0, 1, 4], label="a")
    ax.set_xlabel("x")
    ax.set_title("t")
    ax.legend()
    return fig, ax, line


def test_chrome_for():
    assert chrome_for("dark") is DARK_CHROME
    assert chrome_for("light") is LIGHT_CHROME
    assert chrome_for("system") is LIGHT_CHROME  # unknown -> light


def test_dark_theme_sets_surface_and_text(qapp):
    fig, ax, _ = _figure()
    apply_mpl_theme(fig, "dark")
    assert _hex(fig.get_facecolor()) == DARK_CHROME.surface
    assert _hex(ax.get_facecolor()) == DARK_CHROME.surface
    assert _hex(ax.title.get_color()) == DARK_CHROME.primary
    assert _hex(ax.xaxis.label.get_color()) == DARK_CHROME.secondary
    for spine in ax.spines.values():
        assert _hex(spine.get_edgecolor()) == DARK_CHROME.baseline


def test_light_theme_sets_surface(qapp):
    fig, ax, _ = _figure()
    apply_mpl_theme(fig, "light")
    assert _hex(fig.get_facecolor()) == LIGHT_CHROME.surface


def test_existing_line_preserved_by_default(qapp):
    fig, ax, line = _figure()
    before = line.get_color()
    apply_mpl_theme(fig, "dark")
    assert line.get_color() == before  # correspondence preserved


def test_recolor_existing_opt_in(qapp):
    fig, ax, line = _figure()
    apply_mpl_theme(fig, "dark", recolor_existing=True)
    assert _hex(line.get_color()) == DARK_CHROME.cycle[0]


def test_new_plot_uses_theme_cycle(qapp):
    fig, ax, _ = _figure()
    apply_mpl_theme(fig, "dark")
    (new_line,) = ax.plot([0, 1], [1, 0])  # next in the cycle after the first
    assert _hex(new_line.get_color()) in DARK_CHROME.cycle


def test_controller_apply_theme(qapp):
    from sciappkit.canvas.mpl_canvas import MplCanvas
    from sciappkit.canvas.protocol import MplCanvasController

    canvas = MplCanvas(show_axes=True)
    canvas.ax.plot([0, 1], [0, 1])
    ctrl = MplCanvasController(canvas)
    ctrl.apply_theme("dark")
    assert _hex(canvas.fig.get_facecolor()) == DARK_CHROME.surface


def _hex(color) -> str:
    from matplotlib.colors import to_hex

    return to_hex(color)
