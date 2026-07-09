"""Tests for sciappkit.app.icons (multi-resolution app icon loading)."""

from __future__ import annotations

from PySide6.QtGui import QImage

from sciappkit.app.icons import load_app_icon, set_app_icon


def _write_png(path, size):
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(0xFF3366AA)
    assert img.save(str(path), "PNG")


def _iconset(tmp_path):
    icons = tmp_path / "icons"
    icons.mkdir()
    _write_png(icons / "icon_16x16.png", 16)
    _write_png(icons / "icon_32x32.png", 32)
    _write_png(icons / "icon_16x16@2x.png", 32)
    return icons


def test_load_app_icon_builds_multires_icon(qapp, tmp_path):
    icon = load_app_icon(_iconset(tmp_path))
    assert not icon.isNull()
    sizes = {(s.width(), s.height()) for s in icon.availableSizes()}
    assert (16, 16) in sizes and (32, 32) in sizes


def test_load_app_icon_missing_dir_is_null(qapp, tmp_path):
    icon = load_app_icon(tmp_path / "nope")
    assert icon.isNull()


def test_load_app_icon_empty_dir_is_null(qapp, tmp_path):
    empty = tmp_path / "icons"
    empty.mkdir()
    assert load_app_icon(empty).isNull()


def test_set_app_icon_applies_and_returns(qapp, tmp_path):
    icon = set_app_icon(qapp, _iconset(tmp_path))
    assert not icon.isNull()
    assert not qapp.windowIcon().isNull()
    qapp.setWindowIcon(type(icon)())  # reset for other tests


def test_set_app_icon_null_leaves_default(qapp, tmp_path):
    from PySide6.QtGui import QIcon

    qapp.setWindowIcon(QIcon())
    icon = set_app_icon(qapp, tmp_path / "nope")
    assert icon.isNull()
    assert qapp.windowIcon().isNull()  # untouched
