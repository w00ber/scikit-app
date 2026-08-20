"""Tests for sciappkit.shortcuts.overlay (widget + mixin + registry helper)."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from sciappkit.shortcuts import (
    Shortcut,
    ShortcutOverlay,
    ShortcutOverlayMixin,
    ShortcutRegistry,
    overlay_rows_from_registry,
)


def _host(qapp) -> QWidget:
    host = QWidget()
    host.resize(400, 300)
    # Show the top-level so a child overlay's isVisible() reflects show/hide
    # (a child is only "visible" once its whole ancestor chain is shown).
    host.show()
    return host


# -- ShortcutOverlay widget -------------------------------------------------

def test_overlay_set_rows_renders_title_and_rows(qapp):
    overlay = ShortcutOverlay(_host(qapp))
    overlay.set_rows("Editing", [("⌘S", "Save"), ("⌘Z", "Undo")])
    html = overlay._label.text()
    assert "Editing" in html
    assert "Save" in html and "Undo" in html
    assert "⌘S" in html


def test_overlay_empty_rows_hides(qapp):
    overlay = ShortcutOverlay(_host(qapp))
    overlay.set_rows("Nothing", [])
    assert not overlay.isVisible()


def test_overlay_set_corner_repositions(qapp):
    host = _host(qapp)
    overlay = ShortcutOverlay(host)
    overlay.set_rows("T", [("A", "act")])
    overlay.show()

    overlay.set_corner("top-left")
    left_x = overlay.x()
    overlay.set_corner("top-right")
    right_x = overlay.x()
    assert right_x > left_x


def test_overlay_unknown_corner_ignored(qapp):
    overlay = ShortcutOverlay(_host(qapp))
    overlay.set_corner("bogus")  # must not raise; keeps default
    assert overlay._corner == "top-right"


# -- ShortcutOverlayMixin ---------------------------------------------------

class _Win(ShortcutOverlayMixin):
    """Minimal host object exercising the mixin without a full window."""

    def __init__(self, host: QWidget, rows):
        self._host = host
        self._rows = rows

    def shortcut_overlay_host(self):
        return self._host

    def shortcut_overlay_rows(self):
        return ("Shortcuts", self._rows)


def test_mixin_toggle_shows_and_hides(qapp):
    win = _Win(_host(qapp), [("A", "act")])
    win.init_shortcut_overlay(enabled=False)
    assert not win.shortcut_overlay_enabled
    assert not win.shortcut_overlay.isVisible()

    win.toggle_shortcut_overlay()
    assert win.shortcut_overlay_enabled
    assert win.shortcut_overlay.isVisible()

    win.toggle_shortcut_overlay()
    assert not win.shortcut_overlay_enabled
    assert not win.shortcut_overlay.isVisible()


def test_mixin_explicit_enabled_argument(qapp):
    win = _Win(_host(qapp), [("A", "act")])
    win.init_shortcut_overlay(enabled=False)
    win.toggle_shortcut_overlay(True)
    assert win.shortcut_overlay_enabled
    win.toggle_shortcut_overlay(True)  # idempotent when already on
    assert win.shortcut_overlay_enabled


def test_mixin_update_is_noop_while_disabled(qapp):
    win = _Win(_host(qapp), [("A", "act")])
    win.init_shortcut_overlay(enabled=False)
    win.update_shortcut_overlay()
    assert not win.shortcut_overlay.isVisible()


def test_mixin_init_enabled_shows_immediately(qapp):
    win = _Win(_host(qapp), [("A", "act")])
    win.init_shortcut_overlay(enabled=True)
    assert win.shortcut_overlay_enabled
    assert win.shortcut_overlay.isVisible()


# -- overlay_rows_from_registry ---------------------------------------------

def _registry() -> ShortcutRegistry:
    reg = ShortcutRegistry(platform="mac")
    reg.register_many([
        Shortcut("file.save", default="Ctrl+S", category="File", display_name="Save"),
        Shortcut("file.open", default="Ctrl+O", category="File", display_name="Open"),
        Shortcut("edit.undo", default="Ctrl+Z", category="Edit", display_name="Undo"),
        # Unbound: no key -> must be skipped in the cheat sheet.
        Shortcut("misc.nothing", category="Edit", display_name="Nothing"),
    ])
    return reg


def test_rows_from_registry_pairs_and_skips_unbound(qapp):
    rows = overlay_rows_from_registry(_registry())
    names = [name for _keys, name in rows]
    assert "Save" in names and "Open" in names and "Undo" in names
    assert "Nothing" not in names  # unbound shortcut dropped
    # Every returned row has a non-empty key string.
    assert all(keys for keys, _name in rows)


def test_rows_from_registry_category_filter(qapp):
    rows = overlay_rows_from_registry(_registry(), categories=["File"])
    names = {name for _keys, name in rows}
    assert names == {"Save", "Open"}


def test_rows_from_registry_reflects_override(qapp):
    reg = _registry()
    before = dict((name, keys) for keys, name in overlay_rows_from_registry(reg))
    reg.set_override("file.save", "Ctrl+Shift+S")
    after = dict((name, keys) for keys, name in overlay_rows_from_registry(reg))
    # display_text uses the active (override-aware) sequence, rendered as
    # the PLATFORM draws it — "Ctrl+Shift+S" on Linux/Windows, "⇧⌘S" on a
    # Mac. So the assertion asks Qt for that rendering instead of matching
    # one platform's spelling ("Shift" is absent from the glyph form).
    from PySide6.QtGui import QKeySequence

    expected = QKeySequence("Ctrl+Shift+S").toString(
        QKeySequence.SequenceFormat.NativeText)
    assert after["Save"] != before["Save"]
    assert after["Save"] == expected
