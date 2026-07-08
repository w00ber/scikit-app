"""Tests for sciappkit.widgets.markdown_editor."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent, QTextCursor

from sciappkit.widgets.markdown_editor import (
    MarkdownEditor,
    MarkdownTextEdit,
    bind_markdown_editor_shortcuts,
    markdown_editor_shortcut_defs,
)


def _key(w, key, mods=Qt.KeyboardModifier.NoModifier, text=""):
    w.keyPressEvent(QKeyEvent(QKeyEvent.Type.KeyPress, key, mods, text))


def _select_all(ed):
    cursor = ed.textCursor()
    cursor.select(QTextCursor.SelectionType.Document)
    ed.setTextCursor(cursor)


def test_bold_wraps_selection(qapp):
    ed = MarkdownTextEdit()
    ed.setPlainText("hello")
    _select_all(ed)
    ed.toggle_bold()
    assert ed.toPlainText() == "**hello**"


def test_italic_with_no_selection_inserts_placeholder(qapp):
    ed = MarkdownTextEdit()
    ed.toggle_italic()
    assert ed.toPlainText() == "*italic*"


def test_ctrl_b_keybinding(qapp):
    ed = MarkdownTextEdit()
    ed.setPlainText("x")
    _select_all(ed)
    _key(ed, Qt.Key.Key_B, Qt.KeyboardModifier.ControlModifier)
    assert ed.toPlainText() == "**x**"


def test_list_continuation_unordered(qapp):
    ed = MarkdownTextEdit()
    ed.setPlainText("- item")
    cursor = ed.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    ed.setTextCursor(cursor)
    _key(ed, Qt.Key.Key_Return)
    assert ed.toPlainText() == "- item\n- "


def test_list_continuation_ordered_increments(qapp):
    ed = MarkdownTextEdit()
    ed.setPlainText("1. first")
    cursor = ed.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    ed.setTextCursor(cursor)
    _key(ed, Qt.Key.Key_Return)
    assert ed.toPlainText() == "1. first\n2. "


def test_empty_list_item_clears_on_enter(qapp):
    ed = MarkdownTextEdit()
    ed.setPlainText("- ")
    cursor = ed.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    ed.setTextCursor(cursor)
    _key(ed, Qt.Key.Key_Return)
    assert ed.toPlainText() == ""


# -- MarkdownEditor (editor + preview) --------------------------------------

def test_editor_builds_with_preview(qapp):
    md = MarkdownEditor()
    assert md.preview_visible() is True
    md.setPlainText("# Title")
    # Native setMarkdown renders the heading text into the preview.
    assert "Title" in md.preview.toPlainText()


def test_toggle_preview(qapp):
    md = MarkdownEditor()
    md.toggle_preview()
    assert md.preview_visible() is False
    md.toggle_preview()
    assert md.preview_visible() is True


def test_command_passthroughs(qapp):
    md = MarkdownEditor()
    md.setPlainText("hi")
    _select_all(md.editor)
    md.toggle_bold()
    assert md.toPlainText() == "**hi**"


def test_shortcut_defs_ids():
    ids = {s.action_id for s in markdown_editor_shortcut_defs()}
    assert ids == {
        "markdown.bold", "markdown.italic", "markdown.link",
        "markdown.code_block", "markdown.toggle_preview",
    }


def test_bind_shortcuts_disables_builtin(qapp):
    from sciappkit.shortcuts.manager import ShortcutManager
    from sciappkit.shortcuts.model import ShortcutRegistry

    reg = ShortcutRegistry(platform="linux")
    reg.register_many(markdown_editor_shortcut_defs())
    mgr = ShortcutManager(reg, "metest")
    md = MarkdownEditor()
    bind_markdown_editor_shortcuts(mgr, md)
    assert md.editor._use_builtin_command_keys is False
    from PySide6.QtGui import QShortcut

    assert md.findChildren(QShortcut)
