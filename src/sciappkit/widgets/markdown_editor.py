"""Markdown editor with a live preview pane.

``MarkdownTextEdit`` lifts graphulator's markdown editing behaviors onto
the shared :class:`~sciappkit.widgets.text_edit.LineNumberTextEdit`:
bold/italic/link/code-block formatting, smart list continuation, and
image paste/drop as base64 data URIs. ``MarkdownEditor`` pairs it with a
``QTextBrowser`` preview (Qt-native ``setMarkdown`` — no web dependency)
in a splitter, updating live.

Formatting command keys (Ctrl+B / Ctrl+I / Ctrl+K / Ctrl+Shift+C) work out
of the box, and can instead be driven by a rebindable
:class:`~sciappkit.shortcuts.manager.ShortcutManager` via
:func:`bind_markdown_editor_shortcuts`.
"""

from __future__ import annotations

import base64
import os
import re

from PySide6.QtCore import QBuffer, QEvent, QIODevice, Qt
from PySide6.QtGui import QImage, QTextCursor
from PySide6.QtWidgets import (
    QInputDialog,
    QMessageBox,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from .text_edit import LineNumberTextEdit

# Warn when a single pasted/dropped image would bloat the document.
IMAGE_SIZE_WARN_BYTES = 1_000_000
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"}
EXT_TO_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".bmp": "image/bmp",
}


class MarkdownTextEdit(LineNumberTextEdit):
    """A line-numbered editor with markdown editing conveniences."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._use_builtin_command_keys = True
        self.setAcceptDrops(True)

    # -- shortcut-override guard --------------------------------------------

    def event(self, e):
        # Keep our Ctrl+B/I/K/Shift+C from being eaten by global menu
        # shortcuts while typing in the editor.
        # event() can fire during base __init__ before our flag is set.
        if getattr(self, "_use_builtin_command_keys", True) and e.type() == QEvent.Type.ShortcutOverride:
            mods = e.modifiers()
            key = e.key()
            ctrl = mods & Qt.KeyboardModifier.ControlModifier
            shift = mods & Qt.KeyboardModifier.ShiftModifier
            if ctrl and not (mods & Qt.KeyboardModifier.AltModifier):
                if key in (Qt.Key.Key_B, Qt.Key.Key_I, Qt.Key.Key_K) and not shift:
                    e.accept()
                    return True
                if key == Qt.Key.Key_C and shift:
                    e.accept()
                    return True
        return super().event(e)

    def keyPressEvent(self, event) -> None:
        mods = event.modifiers()
        key = event.key()
        ctrl = bool(mods & Qt.KeyboardModifier.ControlModifier)
        shift = bool(mods & Qt.KeyboardModifier.ShiftModifier)
        alt = bool(mods & Qt.KeyboardModifier.AltModifier)

        if self._use_builtin_command_keys and ctrl and not alt:
            if key == Qt.Key.Key_B and not shift:
                self.toggle_bold()
                return
            if key == Qt.Key.Key_I and not shift:
                self.toggle_italic()
                return
            if key == Qt.Key.Key_K and not shift:
                self.insert_link()
                return
            if key == Qt.Key.Key_C and shift:
                self.insert_code_block()
                return

        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not (shift or ctrl or alt):
            if self._handle_list_continuation():
                return

        super().keyPressEvent(event)

    # -- commands (also exposed for the ShortcutManager) --------------------

    def toggle_bold(self) -> None:
        self._wrap_selection("**", "**", placeholder="bold")

    def toggle_italic(self) -> None:
        self._wrap_selection("*", "*", placeholder="italic")

    def insert_code_block(self) -> None:
        self._wrap_code_block()

    def insert_link(self) -> None:
        cursor = self.textCursor()
        selected = cursor.selectedText() if cursor.hasSelection() else ""
        url, ok = QInputDialog.getText(self, "Insert Link", "URL:")
        if not ok or not url:
            return
        cursor.insertText(f"[{selected or 'link'}]({url})")

    # -- formatting helpers -------------------------------------------------

    def _wrap_selection(self, prefix: str, suffix: str, placeholder: str = "text") -> None:
        cursor = self.textCursor()
        if cursor.hasSelection():
            cursor.insertText(f"{prefix}{cursor.selectedText()}{suffix}")
        else:
            cursor.insertText(f"{prefix}{placeholder}{suffix}")
            end = cursor.position() - len(suffix)
            cursor.setPosition(end - len(placeholder), QTextCursor.MoveMode.MoveAnchor)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            self.setTextCursor(cursor)

    def _wrap_code_block(self) -> None:
        cursor = self.textCursor()
        if cursor.hasSelection():
            selected = cursor.selectedText().replace(" ", "\n")
            cursor.insertText(f"```\n{selected}\n```")
        else:
            cursor.insertText("```\n\n```")
            cursor.setPosition(cursor.position() - len("\n```"))
            self.setTextCursor(cursor)

    def _handle_list_continuation(self) -> bool:
        cursor = self.textCursor()
        if cursor.hasSelection():
            return False
        block_text = cursor.block().text()

        ul = re.match(r"^(\s*)([-*+])(\s+)(.*)$", block_text)
        if ul:
            indent, marker, sep, content = ul.groups()
            if not content.strip():
                self._clear_current_block(cursor)
                return True
            cursor.insertText(f"\n{indent}{marker}{sep}")
            return True

        ol = re.match(r"^(\s*)(\d+)([.)])(\s+)(.*)$", block_text)
        if ol:
            indent, num, dot, sep, content = ol.groups()
            if not content.strip():
                self._clear_current_block(cursor)
                return True
            cursor.insertText(f"\n{indent}{int(num) + 1}{dot}{sep}")
            return True
        return False

    @staticmethod
    def _clear_current_block(cursor: QTextCursor) -> None:
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()

    # -- image insertion ----------------------------------------------------

    def insertFromMimeData(self, source) -> None:
        if source.hasImage():
            image = source.imageData()
            if isinstance(image, QImage) and not image.isNull():
                self._insert_qimage(image)
                return
        if source.hasUrls():
            image_urls = [
                u for u in source.urls()
                if u.isLocalFile()
                and os.path.splitext(u.toLocalFile())[1].lower() in IMAGE_EXTENSIONS
            ]
            if image_urls:
                for url in image_urls:
                    self._insert_image_file(url.toLocalFile())
                return
        super().insertFromMimeData(source)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls() and self._has_image_url(event.mimeData()):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:
        if event.mimeData().hasUrls() and self._has_image_url(event.mimeData()):
            self.setTextCursor(self.cursorForPosition(event.position().toPoint()))
            for url in event.mimeData().urls():
                if url.isLocalFile() and os.path.splitext(url.toLocalFile())[1].lower() in IMAGE_EXTENSIONS:
                    self._insert_image_file(url.toLocalFile())
            event.acceptProposedAction()
            return
        super().dropEvent(event)

    @staticmethod
    def _has_image_url(mime) -> bool:
        return any(
            u.isLocalFile() and os.path.splitext(u.toLocalFile())[1].lower() in IMAGE_EXTENSIONS
            for u in mime.urls()
        )

    def _insert_qimage(self, image: QImage, mime: str = "image/png") -> None:
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        fmt = "PNG" if mime == "image/png" else mime.split("/", 1)[1].upper()
        if not image.save(buffer, fmt):
            return
        raw = bytes(buffer.data())
        if not self._confirm_image_size(len(raw)):
            return
        b64 = base64.b64encode(raw).decode("ascii")
        self._insert_image_markdown(f"data:{mime};base64,{b64}", alt="pasted-image")

    def _insert_image_file(self, path: str) -> None:
        ext = os.path.splitext(path)[1].lower()
        mime = EXT_TO_MIME.get(ext, "image/png")
        try:
            with open(path, "rb") as f:
                raw = f.read()
        except OSError as exc:
            QMessageBox.warning(self, "Image Insert Failed", f"Could not read {path}:\n{exc}")
            return
        if not self._confirm_image_size(len(raw)):
            return
        b64 = base64.b64encode(raw).decode("ascii")
        alt = os.path.splitext(os.path.basename(path))[0] or "image"
        self._insert_image_markdown(f"data:{mime};base64,{b64}", alt=alt)

    def _insert_image_markdown(self, src: str, alt: str = "image") -> None:
        self.textCursor().insertText(f"![{alt}]({src})")

    def _confirm_image_size(self, raw_bytes: int) -> bool:
        if raw_bytes <= IMAGE_SIZE_WARN_BYTES:
            return True
        kb = raw_bytes / 1024
        encoded_kb = (raw_bytes * 4 / 3) / 1024
        reply = QMessageBox.question(
            self, "Large image",
            f"This image is {kb:.0f} KB (~{encoded_kb:.0f} KB once base64-encoded "
            f"into the document). Insert it anyway?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes


class MarkdownEditor(QWidget):
    """A markdown editor paired with a live preview.

    Exposes :attr:`editor` (a :class:`MarkdownTextEdit`) and :attr:`preview`
    (a ``QTextBrowser``). The preview re-renders on every edit via Qt's
    native ``setMarkdown`` (no extra dependency).
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        orientation: Qt.Orientation = Qt.Orientation.Horizontal,
        preview_visible: bool = True,
    ) -> None:
        super().__init__(parent)
        self.editor = MarkdownTextEdit()
        self.preview = QTextBrowser()
        self.preview.setOpenExternalLinks(True)

        self._splitter = QSplitter(orientation)
        self._splitter.addWidget(self.editor)
        self._splitter.addWidget(self.preview)
        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._splitter)

        self.editor.textChanged.connect(self._refresh_preview)
        self.set_preview_visible(preview_visible)
        self._refresh_preview()

    # -- preview ------------------------------------------------------------

    def _refresh_preview(self) -> None:
        self.preview.setMarkdown(self.editor.toPlainText())

    def set_preview_visible(self, visible: bool) -> None:
        self.preview.setVisible(visible)
        if visible:
            self._refresh_preview()

    def toggle_preview(self) -> None:
        self.set_preview_visible(self.preview.isHidden())

    def preview_visible(self) -> bool:
        # isHidden() is independent of whether an ancestor is shown, so this
        # is correct even before the widget is displayed.
        return not self.preview.isHidden()

    # -- text passthroughs --------------------------------------------------

    def toPlainText(self) -> str:
        return self.editor.toPlainText()

    def setPlainText(self, text: str) -> None:
        self.editor.setPlainText(text)

    # -- command passthroughs (for menus / shortcuts) -----------------------

    def toggle_bold(self) -> None:
        self.editor.toggle_bold()

    def toggle_italic(self) -> None:
        self.editor.toggle_italic()

    def insert_link(self) -> None:
        self.editor.insert_link()

    def insert_code_block(self) -> None:
        self.editor.insert_code_block()

    def zoom_in(self) -> None:
        self.editor.zoom_in()

    def zoom_out(self) -> None:
        self.editor.zoom_out()


# -- shortcut integration ---------------------------------------------------

def markdown_editor_shortcut_defs(prefix: str = "markdown") -> list:
    """Return rebindable :class:`Shortcut` defs for the markdown editor."""
    from ..shortcuts.model import Shortcut

    return [
        Shortcut(f"{prefix}.bold", default="Ctrl+B", category="Markdown", display_name="Bold"),
        Shortcut(f"{prefix}.italic", default="Ctrl+I", category="Markdown", display_name="Italic"),
        Shortcut(f"{prefix}.link", default="Ctrl+K", category="Markdown", display_name="Insert Link"),
        Shortcut(f"{prefix}.code_block", default="Ctrl+Shift+C", category="Markdown",
                 display_name="Code Block"),
        Shortcut(f"{prefix}.toggle_preview", default="Ctrl+Shift+P", category="Markdown",
                 display_name="Toggle Preview"),
    ]


def bind_markdown_editor_shortcuts(manager, editor, parent=None, prefix: str = "markdown") -> None:
    """Drive *editor* commands through *manager* (disables built-in keys).

    *editor* may be a :class:`MarkdownEditor` or a bare
    :class:`MarkdownTextEdit`. The defs from
    :func:`markdown_editor_shortcut_defs` must already be registered in the
    manager's registry.
    """
    text_edit = editor.editor if isinstance(editor, MarkdownEditor) else editor
    text_edit._use_builtin_command_keys = False
    parent = parent or editor
    manager.bind_shortcut(f"{prefix}.bold", editor.toggle_bold, parent)
    manager.bind_shortcut(f"{prefix}.italic", editor.toggle_italic, parent)
    manager.bind_shortcut(f"{prefix}.link", editor.insert_link, parent)
    manager.bind_shortcut(f"{prefix}.code_block", editor.insert_code_block, parent)
    if isinstance(editor, MarkdownEditor):
        manager.bind_shortcut(f"{prefix}.toggle_preview", editor.toggle_preview, parent)
