"""Tests for sciappkit.export.clipboard.

These run on the Linux/Qt fallback path (the macOS NSPasteboard strategies
are exercised only on darwin).
"""

from __future__ import annotations

from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QColor, QImage

from sciappkit.export import clipboard


def _png_bytes(color=QColor(255, 0, 0)) -> bytes:
    image = QImage(4, 4, QImage.Format.Format_ARGB32)
    image.fill(color)
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    assert image.save(buf, "PNG")
    return bytes(buf.data())


def test_set_clipboard_qt_path_png_and_pdf(qapp):
    pdf = b"%PDF-1.4 fake pdf bytes"
    png = _png_bytes()
    assert clipboard.copy_to_clipboard(pdf, png) is True
    # On Linux the cascade resolves to the Qt fallback.
    assert clipboard.last_clipboard_method == "qt"

    mime = qapp.clipboard().mimeData()
    assert mime.hasImage()
    assert bytes(mime.data("application/pdf")) == pdf
    # No SVG was supplied, so that flavour must be absent.
    assert not mime.hasFormat("image/svg+xml")


def test_set_clipboard_qt_path_includes_svg(qapp):
    pdf = b"%PDF-1.4 fake pdf bytes"
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"/>'
    png = _png_bytes()
    assert clipboard.copy_to_clipboard(pdf, png, svg) is True
    assert clipboard.last_clipboard_method == "qt"

    mime = qapp.clipboard().mimeData()
    assert mime.hasImage()
    assert bytes(mime.data("application/pdf")) == pdf
    assert mime.hasFormat("image/svg+xml")
    assert bytes(mime.data("image/svg+xml")) == svg


def test_set_clipboard_svg_only(qapp):
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>'
    # SVG alone (no PDF, no PNG) is still a successful vector write.
    assert clipboard.copy_to_clipboard(None, None, svg) is True
    assert clipboard.last_clipboard_method == "qt"
    mime = qapp.clipboard().mimeData()
    assert mime.hasFormat("image/svg+xml")
    assert bytes(mime.data("image/svg+xml")) == svg


def test_set_clipboard_png_only(qapp):
    png = _png_bytes(QColor(0, 0, 255))
    assert clipboard.copy_to_clipboard(None, png) is True
    assert clipboard.last_clipboard_method == "qt"
    assert qapp.clipboard().mimeData().hasImage()


def test_set_clipboard_handles_empty(qapp):
    # No data is still a successful (empty) write via the Qt path.
    assert clipboard.copy_to_clipboard(None, None) is True
    assert clipboard.last_clipboard_method == "qt"
