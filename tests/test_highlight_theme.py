"""Tests for code-editor color schemes."""

from __future__ import annotations

import pytest

from sciappkit.widgets.highlight_theme import (
    DEFAULT_DARK,
    DEFAULT_LIGHT,
    THEMES,
    HighlightTheme,
    get_theme,
    list_themes,
)


def test_builtin_schemes_present():
    names = set(list_themes())
    assert {"dracula", "monokai", "solarized-dark", "solarized-light",
            "zenburn", "github-light"} <= names


def test_get_theme_by_name_and_instance():
    assert get_theme("dracula") is THEMES["dracula"]
    custom = THEMES["monokai"]
    assert get_theme(custom) is custom


def test_get_theme_auto_follows_dark_flag():
    assert get_theme("auto", dark=True) is DEFAULT_DARK
    assert get_theme("auto", dark=False) is DEFAULT_LIGHT


def test_unknown_theme_raises():
    with pytest.raises(ValueError):
        get_theme("nonesuch")


def test_dark_schemes_have_light_text_on_dark_bg():
    from PySide6.QtGui import QColor

    for theme in THEMES.values():
        bg = QColor(theme.background).lightness()
        fg = QColor(theme.foreground).lightness()
        # Reasonable contrast: background and foreground on opposite sides.
        assert abs(bg - fg) > 60, f"{theme.name} bg/fg contrast too low"
        if theme.dark:
            assert bg < 128 and fg > 128
        else:
            assert bg > 128 and fg < 160


def test_code_editor_applies_theme(qapp):
    from PySide6.QtGui import QColor, QPalette

    from sciappkit.widgets.code_editor import CodeEditor

    ed = CodeEditor(theme="dracula")
    assert ed.theme.name == "dracula"
    base = ed.palette().color(QPalette.ColorRole.Base)
    assert base == QColor("#282a36")


def test_code_editor_set_theme_switches(qapp):
    from PySide6.QtGui import QColor, QPalette

    from sciappkit.widgets.code_editor import CodeEditor

    ed = CodeEditor(theme="dracula")
    ed.set_theme("solarized-light")
    assert ed.theme.name == "solarized-light"
    assert ed.palette().color(QPalette.ColorRole.Base) == QColor("#fdf6e3")


def test_highlighter_uses_theme_colors(qapp):
    from PySide6.QtGui import QColor

    from sciappkit.widgets.code_editor import CodeEditor

    ed = CodeEditor(theme="dracula")
    ed.setPlainText("def foo():\n    return 1\n")
    ed.highlighter.rehighlight()
    formats = ed.document().findBlockByNumber(0).layout().formats()
    colors = {fr.format.foreground().color().name() for fr in formats}
    # "def" keyword uses the Dracula keyword color (#ff79c6).
    assert "#ff79c6" in colors
