"""Line-numbered plain-text editor base.

Generalized from graphulator's ``LineNumberTextEdit``. This is the shared
base for the framework's code and markdown editors: a ``QPlainTextEdit``
with a line-number margin, current-line highlight, font zoom, a monospace
default, and an optional syntax-highlighter hook.

The original hard-coded its margin/highlight colors (light-theme only);
here they derive from the widget palette so the editor stays legible under
the light/dark/system themes from :mod:`sciappkit.app.theming`.
"""

from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPalette, QTextFormat
from PySide6.QtWidgets import QPlainTextEdit, QTextEdit, QWidget

MIN_FONT_POINT_SIZE = 6
MAX_FONT_POINT_SIZE = 48
DEFAULT_FONT_POINT_SIZE = 12
TAB_WIDTH_SPACES = 4
_MONOSPACE = "Menlo, Monaco, Consolas, Courier New, monospace"


class LineNumberArea(QWidget):
    """The gutter widget that paints line numbers for a text editor."""

    def __init__(self, editor: "LineNumberTextEdit") -> None:
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event) -> None:
        self._editor.paint_line_numbers(event)


class LineNumberTextEdit(QPlainTextEdit):
    """A plain-text editor with a line-number margin and font zoom.

    Subclass it for code (:class:`sciappkit.widgets.code_editor.CodeEditor`)
    or markdown editing. Attach a ``QSyntaxHighlighter`` with
    :meth:`set_highlighter`.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._line_number_area = LineNumberArea(self)
        self._highlighter = None

        self.blockCountChanged.connect(self._update_margin_width)
        self.updateRequest.connect(self._update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)

        font = QFont(_MONOSPACE)
        font.setPointSize(DEFAULT_FONT_POINT_SIZE)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        self._apply_tab_stop()

        self._update_margin_width()
        self.highlight_current_line()

    # -- syntax highlighter -------------------------------------------------

    def set_highlighter(self, highlighter) -> None:
        """Attach (or clear with ``None``) a ``QSyntaxHighlighter``."""
        self._highlighter = highlighter

    @property
    def highlighter(self):
        return self._highlighter

    # -- line number margin -------------------------------------------------

    @property
    def line_number_area(self) -> LineNumberArea:
        return self._line_number_area

    def line_number_area_width(self) -> int:
        digits = 1
        max_block = max(1, self.blockCount())
        while max_block >= 10:
            max_block //= 10
            digits += 1
        return 10 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_margin_width(self, _new_block_count: int = 0) -> None:
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_number_area(self, rect: QRect, dy: int) -> None:
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(
                0, rect.y(), self._line_number_area.width(), rect.height()
            )
        if rect.contains(self.viewport().rect()):
            self._update_margin_width()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
        )

    def paint_line_numbers(self, event) -> None:
        palette = self.palette()
        bg = palette.color(QPalette.ColorRole.AlternateBase)
        fg = palette.color(QPalette.ColorRole.PlaceholderText)

        painter = QPainter(self._line_number_area)
        painter.fillRect(event.rect(), bg)

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        painter.setPen(fg)
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.drawText(
                    0, top, self._line_number_area.width() - 5,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight, str(block_number + 1),
                )
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    # -- current-line highlight (theme-aware) -------------------------------

    def highlight_current_line(self) -> None:
        selections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(self._current_line_color())
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            selections.append(selection)
        self.setExtraSelections(selections)

    def _current_line_color(self) -> QColor:
        # A faint tint of the palette highlight reads well on light and dark.
        color = QColor(self.palette().color(QPalette.ColorRole.Highlight))
        color.setAlpha(36)
        return color

    # -- font zoom ----------------------------------------------------------

    def set_font_point_size(self, size: int) -> None:
        size = max(MIN_FONT_POINT_SIZE, min(MAX_FONT_POINT_SIZE, size))
        font = self.font()
        font.setPointSize(size)
        self.setFont(font)
        self._apply_tab_stop()

    def zoom_in(self) -> None:
        self.set_font_point_size(self.font().pointSize() + 1)

    def zoom_out(self) -> None:
        self.set_font_point_size(self.font().pointSize() - 1)

    def _apply_tab_stop(self) -> None:
        self.setTabStopDistance(TAB_WIDTH_SPACES * self.fontMetrics().horizontalAdvance(" "))
