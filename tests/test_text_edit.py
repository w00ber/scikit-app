"""Tests for sciappkit.widgets.text_edit.LineNumberTextEdit."""

from __future__ import annotations

from sciappkit.widgets.text_edit import (
    MAX_FONT_POINT_SIZE,
    MIN_FONT_POINT_SIZE,
    LineNumberTextEdit,
)


def test_constructs_with_gutter(qapp):
    ed = LineNumberTextEdit()
    assert ed.line_number_area is not None
    assert ed.line_number_area_width() > 0


def test_gutter_width_grows_with_line_count(qapp):
    ed = LineNumberTextEdit()
    narrow = ed.line_number_area_width()
    ed.setPlainText("\n".join(str(i) for i in range(1000)))
    assert ed.line_number_area_width() > narrow


def test_zoom_clamps(qapp):
    ed = LineNumberTextEdit()
    for _ in range(100):
        ed.zoom_in()
    assert ed.font().pointSize() == MAX_FONT_POINT_SIZE
    for _ in range(200):
        ed.zoom_out()
    assert ed.font().pointSize() == MIN_FONT_POINT_SIZE


def test_current_line_highlight_present_when_editable(qapp):
    ed = LineNumberTextEdit()
    ed.setPlainText("hello")
    ed.highlight_current_line()
    assert len(ed.extraSelections()) == 1
    ed.setReadOnly(True)
    ed.highlight_current_line()
    assert ed.extraSelections() == []


def test_set_highlighter(qapp):
    ed = LineNumberTextEdit()
    assert ed.highlighter is None
    sentinel = object()
    ed.set_highlighter(sentinel)
    assert ed.highlighter is sentinel
