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
