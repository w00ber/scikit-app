"""Tests for the [web] QtWebEngine markdown preview.

These exercise the synchronous HTML conversion (which is where inline-image
support lives); the actual Chromium render is validated separately via the
example screenshots.
"""

from __future__ import annotations

import base64

import pytest

pytest.importorskip("PySide6.QtWebEngineWidgets")
pytest.importorskip("markdown")

from sciappkit.widgets.markdown_preview_web import WebMarkdownPreview  # noqa: E402


def _data_uri_png() -> str:
    # 1x1 transparent PNG.
    raw = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )
    return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")


def test_to_html_renders_heading_and_emphasis(qapp):
    p = WebMarkdownPreview()
    html = p.to_html("# Title\n\nSome **bold** text.")
    assert "<h1" in html and "Title" in html
    assert "<strong>bold</strong>" in html


def test_to_html_preserves_inline_image_data_uri(qapp):
    p = WebMarkdownPreview()
    uri = _data_uri_png()
    html = p.to_html(f"![pasted]({uri})")
    assert uri in html
    assert "<img" in html


def test_to_html_has_themed_css(qapp):
    p = WebMarkdownPreview()
    html = p.to_html("text")
    assert "<style>" in html
    assert "font-family" in html


def test_katex_assets_included_only_when_configured(qapp):
    no_math = WebMarkdownPreview().to_html("$x^2$")
    assert "katex" not in no_math.lower()

    with_math = WebMarkdownPreview(katex_base_url="https://cdn.example/katex").to_html("$x^2$")
    assert "katex.min.css" in with_math
    assert "auto-render.min.js" in with_math


def test_markdown_editor_web_backend(qapp):
    from sciappkit.widgets.markdown_editor import MarkdownEditor

    md = MarkdownEditor(backend="web")
    assert md.backend == "web"
    assert isinstance(md.preview, WebMarkdownPreview)
    # Uniform setMarkdown path works without raising.
    md.setPlainText("# Hi")


def test_unknown_backend_raises(qapp):
    from sciappkit.widgets.markdown_editor import MarkdownEditor

    with pytest.raises(ValueError):
        MarkdownEditor(backend="bogus")
