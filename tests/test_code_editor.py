"""Tests for sciappkit.widgets.code_editor."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent, QTextCursor

from sciappkit.widgets.code_editor import (
    CodeEditor,
    PythonHighlighter,
    bind_code_editor_shortcuts,
    code_editor_shortcut_defs,
)


def _key(editor, key, mods=Qt.KeyboardModifier.NoModifier, text=""):
    editor.keyPressEvent(QKeyEvent(QKeyEvent.Type.KeyPress, key, mods, text))


def test_python_highlighter_attached(qapp):
    ed = CodeEditor(language="python")
    assert isinstance(ed.highlighter, PythonHighlighter)


def test_no_highlighter_for_unknown_language(qapp):
    ed = CodeEditor(language=None)
    assert ed.highlighter is None


def test_highlighter_formats_keyword(qapp):
    ed = CodeEditor(language="python")
    ed.setPlainText("def foo():\n    return 1\n")
    ed.highlighter.rehighlight()
    formats = ed.document().findBlockByNumber(0).layout().formats()
    assert formats, "expected syntax highlighting format ranges on the first line"


def test_tab_inserts_spaces(qapp):
    ed = CodeEditor()
    _key(ed, Qt.Key.Key_Tab)
    assert ed.toPlainText() == "    "


def test_auto_indent_after_colon(qapp):
    ed = CodeEditor()
    ed.setPlainText("def f():")
    cursor = ed.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    ed.setTextCursor(cursor)
    _key(ed, Qt.Key.Key_Return)
    assert ed.toPlainText() == "def f():\n    "


def test_auto_indent_carries_existing_indent(qapp):
    ed = CodeEditor()
    ed.setPlainText("    x = 1")
    cursor = ed.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    ed.setTextCursor(cursor)
    _key(ed, Qt.Key.Key_Return)
    assert ed.toPlainText() == "    x = 1\n    "


def test_toggle_comment_roundtrip(qapp):
    ed = CodeEditor(language="python")
    ed.setPlainText("x = 1\ny = 2")
    ed.selectAll()
    ed.toggle_comment()
    assert ed.toPlainText() == "# x = 1\n# y = 2"
    ed.selectAll()
    ed.toggle_comment()
    assert ed.toPlainText() == "x = 1\ny = 2"


def test_indent_and_dedent_selection(qapp):
    ed = CodeEditor()
    ed.setPlainText("a\nb")
    ed.selectAll()
    _key(ed, Qt.Key.Key_Tab)
    assert ed.toPlainText() == "    a\n    b"
    ed.selectAll()
    _key(ed, Qt.Key.Key_Backtab)
    assert ed.toPlainText() == "a\nb"


def test_shortcut_defs_ids():
    defs = code_editor_shortcut_defs()
    ids = {s.action_id for s in defs}
    assert ids == {"code.comment_toggle", "code.zoom_in", "code.zoom_out"}


def test_bind_shortcuts_disables_builtin_and_binds(qapp):
    from sciappkit.shortcuts.manager import ShortcutManager
    from sciappkit.shortcuts.model import ShortcutRegistry

    reg = ShortcutRegistry(platform="linux")
    reg.register_many(code_editor_shortcut_defs())
    mgr = ShortcutManager(reg, "cetest")
    ed = CodeEditor(language="python")
    bind_code_editor_shortcuts(mgr, ed)
    assert ed._use_builtin_command_keys is False
    # The comment-toggle shortcut is now a real QShortcut on the editor.
    from PySide6.QtGui import QShortcut

    assert ed.findChildren(QShortcut)
