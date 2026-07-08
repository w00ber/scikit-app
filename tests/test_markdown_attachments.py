"""Tests for markdown pasted-image attachments (no base64 blob in source)."""

from __future__ import annotations

import pytest

from sciappkit.widgets.markdown_editor import MarkdownEditor, MarkdownTextEdit

_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32  # not a real image, just bytes


def test_attachment_mode_keeps_source_clean(qapp):
    ed = MarkdownTextEdit(image_mode="attachment")
    ed._insert_image(_PNG, "image/png", alt="diagram", hint="diagram")
    text = ed.toPlainText()
    assert text == "![diagram](attachment:diagram)"
    # The bytes are stored out-of-band, not in the source.
    assert "base64" not in text
    assert ed.attachments["diagram"] == (_PNG, "image/png")


def test_datauri_mode_inlines(qapp):
    ed = MarkdownTextEdit(image_mode="datauri")
    ed._insert_image(_PNG, "image/png", alt="x", hint="x")
    assert ed.toPlainText().startswith("![x](data:image/png;base64,")
    assert ed.attachments == {}


def test_attachment_keys_are_unique(qapp):
    ed = MarkdownTextEdit(image_mode="attachment")
    ed._insert_image(_PNG, "image/png", alt="a", hint="img")
    ed._insert_image(_PNG, "image/png", alt="b", hint="img")
    assert len(ed.attachments) == 2


def test_web_preview_resolves_attachment(qapp):
    pytest.importorskip("PySide6.QtWebEngineWidgets")
    pytest.importorskip("markdown")
    from sciappkit.widgets.markdown_preview_web import WebMarkdownPreview

    preview = WebMarkdownPreview()
    preview.set_attachments({"diagram": (_PNG, "image/png")})
    html = preview.to_html("![d](attachment:diagram)")
    assert "attachment:diagram" not in html
    assert "data:image/png;base64," in html


def test_editor_document_roundtrip(qapp):
    pytest.importorskip("PySide6.QtWebEngineWidgets")
    md = MarkdownEditor(backend="web")
    md.setPlainText("# Note")
    md.editor._insert_image(_PNG, "image/png", alt="fig", hint="fig")
    doc = md.document()
    assert "attachments" in doc and "fig" in doc["attachments"]

    other = MarkdownEditor(backend="web")
    other.load_document(doc)
    assert "![fig](attachment:fig)" in other.toPlainText()
    assert other.attachments["fig"][0] == _PNG


def test_default_backend_uses_attachment_mode(qapp):
    md = MarkdownEditor()  # native backend, attachment image mode by default
    md.editor._insert_image(_PNG, "image/png", alt="p", hint="p")
    assert "attachment:p" in md.toPlainText()
    assert "base64" not in md.toPlainText()


def _real_png(qapp) -> bytes:
    from PySide6.QtCore import QBuffer, QIODevice
    from PySide6.QtGui import QColor, QImage

    img = QImage(8, 8, QImage.Format.Format_ARGB32)
    img.fill(QColor(10, 200, 90))
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    return bytes(buf.data())


def test_native_preview_resolves_attachment_image(qapp):
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QImage, QTextDocument

    from sciappkit.widgets.markdown_editor import AttachmentTextBrowser

    png = _real_png(qapp)
    browser = AttachmentTextBrowser()
    browser.set_attachments({"fig": (png, "image/png")})
    browser.setMarkdown("![fig](attachment:fig)")
    resource = browser.loadResource(
        int(QTextDocument.ResourceType.ImageResource), QUrl("attachment:fig")
    )
    assert isinstance(resource, QImage)
    assert not resource.isNull()
    # An unknown key falls through to the base implementation.
    assert not isinstance(
        browser.loadResource(int(QTextDocument.ResourceType.ImageResource),
                             QUrl("attachment:missing")),
        QImage,
    ) or browser.loadResource(
        int(QTextDocument.ResourceType.ImageResource), QUrl("attachment:missing")
    ).isNull()


def test_native_editor_passes_attachments_to_preview(qapp):
    from sciappkit.widgets.markdown_editor import AttachmentTextBrowser

    md = MarkdownEditor(backend="native")
    assert isinstance(md.preview, AttachmentTextBrowser)
    md.editor.attachments["fig"] = (_real_png(qapp), "image/png")
    md.setPlainText("![fig](attachment:fig)")  # triggers refresh
    assert "fig" in md.preview._attachment_images
