"""Spinbox widgets.

``FineControlSpinBox`` is lifted from graphulator's ``para_ui/widgets.py``.
App-agnostic: a ``QDoubleSpinBox`` that adds modifier-aware stepping
(Shift = fine, Alt = coarse). Depends only on PySide6.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDoubleSpinBox


class FineControlSpinBox(QDoubleSpinBox):
    """Double spinbox with Shift+Up/Down for finer control.

    - Up/Down: Change by normal singleStep
    - Shift+Up/Down: Change by 1/10 of singleStep (finer control)
    - Alt+Up/Down: Change by 10x singleStep (coarser control)

    Note: The Shift+Up/Down behavior is primarily handled by the global
    shortcut handler (_nudge_label) which checks for spinbox focus.
    """

    # Default tooltip explaining modifier controls
    MODIFIER_TOOLTIP = "Up/Down: normal step\nShift+Up/Down: fine (1/10)\nAlt+Up/Down: coarse (10x)"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Disable keyboard tracking so valueChanged only fires when:
        # - User presses Enter
        # - Spinbox loses focus
        # - User uses up/down buttons/arrows
        # This prevents focus issues on Windows where valueChanged firing
        # on every keystroke can interfere with the focus restoration code
        self.setKeyboardTracking(False)
        # Set tooltip if none provided
        if not self.toolTip():
            self.setToolTip(self.MODIFIER_TOOLTIP)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Up, Qt.Key_Down):
            # Determine step multiplier based on modifiers
            modifiers = event.modifiers()

            if modifiers & Qt.ShiftModifier:
                # Shift: finer control (1/10 step)
                multiplier = 0.1
            elif modifiers & Qt.AltModifier:
                # Alt/Option: coarser control (10x step)
                multiplier = 10.0
            else:
                # No modifier: normal step
                super().keyPressEvent(event)
                return

            # Calculate the step and new value
            step = self.singleStep() * multiplier
            if event.key() == Qt.Key_Up:
                new_value = self.value() + step
            else:
                new_value = self.value() - step

            # Clamp to range and set
            new_value = max(self.minimum(), min(self.maximum(), new_value))
            self.setValue(new_value)
            event.accept()
        else:
            super().keyPressEvent(event)
