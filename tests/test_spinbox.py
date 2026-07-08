"""Tests for sciappkit.widgets.spinbox."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent

from sciappkit.widgets.spinbox import FineControlSpinBox


def _press(widget, key, modifier=Qt.KeyboardModifier.NoModifier):
    event = QKeyEvent(QKeyEvent.Type.KeyPress, key, modifier)
    widget.keyPressEvent(event)


def _make(qapp):
    box = FineControlSpinBox()
    box.setRange(-100.0, 100.0)
    box.setSingleStep(1.0)
    box.setValue(0.0)
    return box


def test_default_tooltip_and_no_keyboard_tracking(qapp):
    box = _make(qapp)
    assert box.keyboardTracking() is False
    assert "fine" in box.toolTip()


def test_plain_step(qapp):
    box = _make(qapp)
    _press(box, Qt.Key.Key_Up)
    assert box.value() == 1.0


def test_shift_is_fine_step(qapp):
    box = _make(qapp)
    _press(box, Qt.Key.Key_Up, Qt.KeyboardModifier.ShiftModifier)
    assert round(box.value(), 6) == 0.1


def test_alt_is_coarse_step(qapp):
    box = _make(qapp)
    _press(box, Qt.Key.Key_Up, Qt.KeyboardModifier.AltModifier)
    assert box.value() == 10.0


def test_fine_step_clamps_to_range(qapp):
    box = _make(qapp)
    box.setValue(-100.0)
    _press(box, Qt.Key.Key_Down, Qt.KeyboardModifier.AltModifier)
    assert box.value() == -100.0
