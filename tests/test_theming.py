"""Tests for sciappkit.app.theming."""

from __future__ import annotations

import pytest

from sciappkit.app import theming


def test_themes_constant():
    assert theming.THEMES == ("system", "light", "dark")


def test_palettes_differ():
    light = theming._build_light_palette()
    dark = theming._build_dark_palette()
    from PySide6.QtGui import QPalette

    light_win = light.color(QPalette.ColorRole.Window)
    dark_win = dark.color(QPalette.ColorRole.Window)
    # Light chrome should be brighter than dark chrome.
    assert light_win.lightness() > dark_win.lightness()


@pytest.mark.parametrize("mode", ["system", "light", "dark", "bogus"])
def test_apply_theme_runs(qapp, mode):
    # Should not raise for any value, including an unknown mode (which
    # falls back to "system").
    theming.apply_theme(qapp, mode)


def test_hint_text_color_follows_palette(qapp):
    theming.apply_theme(qapp, "light")
    assert theming.hint_text_color() == "#555555"
    theming.apply_theme(qapp, "dark")
    assert theming.hint_text_color() == "#a8a8a8"
    # Restore a neutral state for any later tests.
    theming.apply_theme(qapp, "system")
