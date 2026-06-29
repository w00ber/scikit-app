"""Code editor: line numbers + syntax highlighting + code conveniences.

Builds on :class:`sciappkit.widgets.text_edit.LineNumberTextEdit`, adding a
pluggable ``QSyntaxHighlighter`` (a Python highlighter ships built in),
auto-indent, tab-to-spaces, and comment toggling. The editing-structure
keys (Tab / Shift+Tab / Enter) are always handled; the *command* keys
(comment toggle, zoom) have built-in defaults but can instead be driven by
a rebindable :class:`~sciappkit.shortcuts.manager.ShortcutManager` via
:func:`bind_code_editor_shortcuts`.

Apps that generate code (e.g. graphulator's SymPy/Python export) get a
ready editor; other languages plug in by passing ``language=`` or calling
``set_highlighter`` with a custom highlighter.
"""

from __future__ import annotations

from PySide6.QtCore import QRegularExpression, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextCursor,
)
from PySide6.QtWidgets import QWidget

from .text_edit import LineNumberTextEdit


def _fmt(color: str, *, bold: bool = False, italic: bool = False) -> QTextCharFormat:
    fmt = QTextCharFormat()
    fmt.setForeground(QColor(color))
    if bold:
        fmt.setFontWeight(QFont.Weight.Bold)
    if italic:
        fmt.setFontItalic(True)
    return fmt


class PythonHighlighter(QSyntaxHighlighter):
    """A modest Python syntax highlighter.

    Colors are chosen to stay readable on both light and dark backgrounds.
    """

    KEYWORDS = (
        "and as assert async await break class continue def del elif else "
        "except finally for from global if import in is lambda nonlocal not "
        "or pass raise return try while with yield match case"
    ).split()
    BUILTINS = (
        "abs all any bool dict enumerate float int len list max min print "
        "range set str sum tuple type zip super object property staticmethod "
        "classmethod isinstance issubclass getattr setattr hasattr"
    ).split()

    def __init__(self, document) -> None:
        super().__init__(document)
        kw = _fmt("#0033b3" if not _is_dark(document) else "#7aa2f7", bold=True)
        builtin = _fmt("#7a3e9d" if not _is_dark(document) else "#bb9af7")
        string = _fmt("#067d17" if not _is_dark(document) else "#9ece6a")
        comment = _fmt("#8c8c8c", italic=True)
        number = _fmt("#1750eb" if not _is_dark(document) else "#ff9e64")
        decorator = _fmt("#9e880d" if not _is_dark(document) else "#e0af68")
        defname = _fmt("#00627a" if not _is_dark(document) else "#7dcfff", bold=True)

        self._rules: list[tuple[QRegularExpression, QTextCharFormat]] = []
        for word in self.KEYWORDS:
            self._rules.append((QRegularExpression(rf"\b{word}\b"), kw))
        for word in self.BUILTINS:
            self._rules.append((QRegularExpression(rf"\b{word}\b"), builtin))
        self._rules.append((QRegularExpression(r"\b\d+(\.\d+)?\b"), number))
        self._rules.append((QRegularExpression(r"@[A-Za-z_][A-Za-z0-9_]*"), decorator))
        self._rules.append((QRegularExpression(r"(?<=\bdef\s)[A-Za-z_][A-Za-z0-9_]*"), defname))
        self._rules.append((QRegularExpression(r"(?<=\bclass\s)[A-Za-z_][A-Za-z0-9_]*"), defname))
        # Single-line strings (after the keyword/number rules so they win).
        self._rules.append((QRegularExpression(r"'[^'\\]*(\\.[^'\\]*)*'"), string))
        self._rules.append((QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"'), string))
        self._rules.append((QRegularExpression(r"#[^\n]*"), comment))

        self._string_format = string
        self._triple = QRegularExpression(r"('''|\"\"\")")

    def highlightBlock(self, text: str) -> None:
        for pattern, fmt in self._rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), fmt)
        self._highlight_triple_strings(text)

    def _highlight_triple_strings(self, text: str) -> None:
        # Continue an open triple-quoted string, or find new ones.
        self.setCurrentBlockState(0)
        start = 0
        if self.previousBlockState() != 1:
            m = self._triple.match(text)
            start = m.capturedStart() if m.hasMatch() else -1
        while start >= 0:
            m = self._triple.match(text, start + 3 if self.previousBlockState() != 1 or start > 0 else 0)
            end_match = self._triple.match(text, start + 3)
            if end_match.hasMatch():
                length = end_match.capturedEnd() - start
                self.setFormat(start, length, self._string_format)
                nxt = self._triple.match(text, end_match.capturedEnd())
                start = nxt.capturedStart() if nxt.hasMatch() else -1
                self.setCurrentBlockState(0)
            else:
                self.setCurrentBlockState(1)
                self.setFormat(start, len(text) - start, self._string_format)
                break


def _is_dark(document) -> bool:
    parent = document.parent() if document is not None else None
    try:
        from PySide6.QtGui import QPalette

        if parent is not None and hasattr(parent, "palette"):
            return parent.palette().color(QPalette.ColorRole.Base).lightness() < 128
    except Exception:
        pass
    return False


#: language name -> highlighter factory (``factory(document) -> highlighter``)
LANGUAGES = {"python": PythonHighlighter}

#: language name -> line-comment token
COMMENT_TOKENS = {"python": "#"}


class CodeEditor(LineNumberTextEdit):
    """A line-numbered editor with syntax highlighting and code conveniences."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        language: str | None = "python",
        indent_width: int = 4,
    ) -> None:
        super().__init__(parent)
        self._indent_width = indent_width
        self._language = language
        self._comment_token = COMMENT_TOKENS.get(language or "", "#")
        self._use_builtin_command_keys = True
        if language in LANGUAGES:
            self.set_highlighter(LANGUAGES[language](self.document()))

    @property
    def language(self) -> str | None:
        return self._language

    # -- key handling -------------------------------------------------------

    def keyPressEvent(self, event) -> None:
        key = event.key()
        mods = event.modifiers()
        ctrl = bool(mods & Qt.KeyboardModifier.ControlModifier)

        if key == Qt.Key.Key_Tab and not ctrl:
            if self._selection_spans_lines():
                self._indent_selection()
            else:
                self.insertPlainText(" " * self._indent_width)
            event.accept()
            return
        if key == Qt.Key.Key_Backtab:
            self._dedent_selection()
            event.accept()
            return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not (mods & Qt.KeyboardModifier.ShiftModifier):
            self._insert_newline_with_indent()
            event.accept()
            return

        if self._use_builtin_command_keys and ctrl:
            if key == Qt.Key.Key_Slash:
                self.toggle_comment()
                event.accept()
                return
            if key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
                self.zoom_in()
                event.accept()
                return
            if key == Qt.Key.Key_Minus:
                self.zoom_out()
                event.accept()
                return

        super().keyPressEvent(event)

    # -- indent helpers -----------------------------------------------------

    def _selection_spans_lines(self) -> bool:
        cursor = self.textCursor()
        if not cursor.hasSelection():
            return False
        return self.document().findBlock(cursor.selectionStart()) != self.document().findBlock(
            cursor.selectionEnd()
        )

    def _each_selected_block(self):
        cursor = self.textCursor()
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        block = self.document().findBlock(start)
        blocks = []
        while block.isValid() and block.position() <= end:
            blocks.append(block)
            if block.position() == end and block.position() != start:
                break
            block = block.next()
        return blocks or [self.document().findBlock(cursor.position())]

    def _indent_selection(self) -> None:
        cursor = self.textCursor()
        cursor.beginEditBlock()
        for block in self._each_selected_block():
            c = QTextCursor(block)
            c.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            c.insertText(" " * self._indent_width)
        cursor.endEditBlock()

    def _dedent_selection(self) -> None:
        cursor = self.textCursor()
        cursor.beginEditBlock()
        for block in self._each_selected_block():
            text = block.text()
            removable = 0
            while removable < self._indent_width and removable < len(text) and text[removable] == " ":
                removable += 1
            if removable == 0 and text.startswith("\t"):
                removable = 1
            if removable:
                c = QTextCursor(block)
                c.movePosition(QTextCursor.MoveOperation.StartOfBlock)
                for _ in range(removable):
                    c.deleteChar()
        cursor.endEditBlock()

    def _insert_newline_with_indent(self) -> None:
        cursor = self.textCursor()
        line = cursor.block().text()
        indent = line[: len(line) - len(line.lstrip(" \t"))]
        if line.rstrip().endswith(":"):
            indent += " " * self._indent_width
        cursor.insertText("\n" + indent)

    # -- commands (also exposed for the ShortcutManager) --------------------

    def toggle_comment(self) -> None:
        """Comment or uncomment the selected lines (or the current line)."""
        token = self._comment_token
        blocks = self._each_selected_block()
        all_commented = all(b.text().lstrip().startswith(token) for b in blocks if b.text().strip())
        cursor = self.textCursor()
        cursor.beginEditBlock()
        for block in blocks:
            text = block.text()
            if not text.strip():
                continue
            c = QTextCursor(block)
            if all_commented:
                idx = text.find(token)
                c.setPosition(block.position() + idx)
                for _ in range(len(token)):
                    c.deleteChar()
                # Drop one following space if present (matches our insert).
                if block.text()[idx: idx + 1] == " ":
                    c.deleteChar()
            else:
                indent_len = len(text) - len(text.lstrip(" \t"))
                c.setPosition(block.position() + indent_len)
                c.insertText(f"{token} ")
        cursor.endEditBlock()


# -- shortcut integration ---------------------------------------------------

def code_editor_shortcut_defs(prefix: str = "code") -> list:
    """Return rebindable :class:`Shortcut` defs for the code editor."""
    from ..shortcuts.model import Shortcut

    return [
        Shortcut(f"{prefix}.comment_toggle", default="Ctrl+/", category="Code",
                 display_name="Toggle Comment", description="Comment/uncomment selected lines"),
        Shortcut(f"{prefix}.zoom_in", default="Ctrl++", category="Code",
                 display_name="Zoom In"),
        Shortcut(f"{prefix}.zoom_out", default="Ctrl+-", category="Code",
                 display_name="Zoom Out"),
    ]


def bind_code_editor_shortcuts(manager, editor: CodeEditor, parent=None, prefix: str = "code") -> None:
    """Drive *editor* commands through *manager* (disables built-in keys).

    The editor's structural keys (Tab/Enter) keep working; the command keys
    become rebindable through the manager. The defs from
    :func:`code_editor_shortcut_defs` must already be registered in the
    manager's registry.
    """
    editor._use_builtin_command_keys = False
    parent = parent or editor
    manager.bind_shortcut(f"{prefix}.comment_toggle", editor.toggle_comment, parent)
    manager.bind_shortcut(f"{prefix}.zoom_in", editor.zoom_in, parent)
    manager.bind_shortcut(f"{prefix}.zoom_out", editor.zoom_out, parent)
