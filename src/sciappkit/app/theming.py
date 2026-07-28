"""Application theming: light / dark / system Fusion palettes.

Lifted from Diagrammer's ``app.py``. App-agnostic: depends only on
PySide6. Apps call :func:`apply_theme` at startup and from a menu toggle;
:func:`hint_text_color` returns a muted text color that stays legible
against whichever chrome theme is active.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QStyleFactory

# Valid theme values. "system" follows the platform's live color scheme;
# "light" and "dark" force that scheme app-locally. On Qt >= 6.8 all three
# ride QStyleHints.setColorScheme (the platform style re-skins natively);
# older Qt falls back to Fusion + the hand-built palettes below.
THEMES = ("system", "light", "dark")


def _build_light_palette() -> QPalette:
    """Return an explicit light QPalette (Fusion-style)."""
    palette = QPalette()
    white = QColor(255, 255, 255)
    near_white = QColor(245, 245, 245)
    light_gray = QColor(240, 240, 240)
    mid_gray = QColor(200, 200, 200)
    dark_gray = QColor(120, 120, 120)
    black = QColor(0, 0, 0)
    highlight = QColor(0, 120, 215)

    palette.setColor(QPalette.ColorRole.Window, light_gray)
    palette.setColor(QPalette.ColorRole.WindowText, black)
    palette.setColor(QPalette.ColorRole.Base, white)
    palette.setColor(QPalette.ColorRole.AlternateBase, near_white)
    palette.setColor(QPalette.ColorRole.ToolTipBase, white)
    palette.setColor(QPalette.ColorRole.ToolTipText, black)
    palette.setColor(QPalette.ColorRole.Text, black)
    palette.setColor(QPalette.ColorRole.PlaceholderText, dark_gray)
    palette.setColor(QPalette.ColorRole.Button, light_gray)
    palette.setColor(QPalette.ColorRole.ButtonText, black)
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.ColorRole.Highlight, highlight)
    palette.setColor(QPalette.ColorRole.HighlightedText, white)
    palette.setColor(QPalette.ColorRole.Link, highlight)

    for role, color in (
        (QPalette.ColorRole.WindowText, mid_gray),
        (QPalette.ColorRole.Text, mid_gray),
        (QPalette.ColorRole.ButtonText, mid_gray),
        (QPalette.ColorRole.Base, near_white),
        (QPalette.ColorRole.Highlight, mid_gray),
        (QPalette.ColorRole.HighlightedText, white),
    ):
        palette.setColor(QPalette.ColorGroup.Disabled, role, color)
    return palette


def _build_dark_palette() -> QPalette:
    """Return an explicit dark QPalette (Fusion-style).

    Loosely based on the commonly-used Qt Fusion dark recipe.
    """
    window_bg = QColor(53, 53, 53)
    # Construct FROM the button color so the derived shades (Light/Midlight/
    # Mid/Dark/Shadow — used by frames, separators, styled dock titles) come
    # out dark too; a default-constructed QPalette leaves them at their light
    # defaults, which reads as glaring light strips on the dark chrome.
    palette = QPalette(window_bg)
    base_bg = QColor(42, 42, 42)
    alt_base = QColor(66, 66, 66)
    button_bg = QColor(53, 53, 53)
    text = QColor(220, 220, 220)
    disabled_text = QColor(127, 127, 127)
    bright_text = QColor(255, 80, 80)
    highlight = QColor(42, 130, 218)
    white = QColor(255, 255, 255)
    black = QColor(0, 0, 0)

    palette.setColor(QPalette.ColorRole.Window, window_bg)
    palette.setColor(QPalette.ColorRole.WindowText, text)
    palette.setColor(QPalette.ColorRole.Base, base_bg)
    palette.setColor(QPalette.ColorRole.AlternateBase, alt_base)
    palette.setColor(QPalette.ColorRole.ToolTipBase, window_bg)
    palette.setColor(QPalette.ColorRole.ToolTipText, text)
    palette.setColor(QPalette.ColorRole.Text, text)
    palette.setColor(QPalette.ColorRole.PlaceholderText, disabled_text)
    palette.setColor(QPalette.ColorRole.Button, button_bg)
    palette.setColor(QPalette.ColorRole.ButtonText, text)
    palette.setColor(QPalette.ColorRole.BrightText, bright_text)
    palette.setColor(QPalette.ColorRole.Highlight, highlight)
    palette.setColor(QPalette.ColorRole.HighlightedText, black)
    palette.setColor(QPalette.ColorRole.Link, QColor(100, 170, 255))

    for role, color in (
        (QPalette.ColorRole.WindowText, disabled_text),
        (QPalette.ColorRole.Text, disabled_text),
        (QPalette.ColorRole.ButtonText, disabled_text),
        (QPalette.ColorRole.Base, window_bg),
        (QPalette.ColorRole.Highlight, QColor(80, 80, 80)),
        (QPalette.ColorRole.HighlightedText, white),
    ):
        palette.setColor(QPalette.ColorGroup.Disabled, role, color)
    return palette


def hint_text_color() -> str:
    """Return a hex color string for muted hint/caveat text.

    Returns a medium-gray that's legible against both light and dark
    chrome backgrounds, picked by inspecting the current application
    palette. Callers use this in inline stylesheets instead of hard-
    coding ``color: #555``, which disappears on a dark Window color.
    """
    app = QApplication.instance()
    if app is None:
        return "#555555"
    window = app.palette().color(QPalette.ColorRole.Window)
    # Window.lightness() is 0..255; <128 = dark-mode chrome.
    return "#a8a8a8" if window.lightness() < 128 else "#555555"


# Keep a handle on the style we saw at startup so "system" mode can
# restore the native look after switching away from Fusion.
_native_style_name: str | None = None


def apply_theme(app: QApplication, mode: str) -> None:
    """Apply a theme to the running QApplication.

    ``mode`` is one of :data:`THEMES`. Safe to call at startup and at
    runtime (e.g. from a menu toggle) — calling it again reapplies the
    requested style and palette so existing widgets repaint.
    """
    if mode not in THEMES:
        mode = "system"

    global _native_style_name
    if _native_style_name is None:
        current = app.style()
        if current is not None:
            _native_style_name = current.objectName()

    # Preferred path (Qt >= 6.8): flip the app-local color scheme and let
    # the PLATFORM restyle every widget natively (macOS NSAppearance,
    # Windows dark chrome, portal-aware Linux). Hand-built palettes fight
    # the native styles — macOS in particular ignores much of a custom
    # QPalette and ends up half-themed — so on this path no palette is set
    # at all, and Unknown hands scheme control back to the OS (live
    # night-mode flips included). The getter reflects what the platform
    # actually did, so a theme with no scheme support (e.g. bare Linux
    # without a desktop portal, offscreen) is detected and falls through
    # to the legacy Fusion-palette path below.
    hints = app.styleHints()
    schemes = {"light": Qt.ColorScheme.Light, "dark": Qt.ColorScheme.Dark}
    if hasattr(hints, "setColorScheme"):
        hints.setColorScheme(schemes.get(mode, Qt.ColorScheme.Unknown))
        if mode == "system" or hints.colorScheme() == schemes[mode]:
            style = QStyleFactory.create(_native_style_name or "Fusion")
            if style is not None and app.style().objectName() != style.objectName():
                app.setStyle(style)
            # A default-constructed palette (empty resolve mask) clears any
            # app-level override so the platform/theme palette shows through
            # — NOT style.standardPalette(), which is a static snapshot that
            # goes stale the moment the OS flips its appearance.
            app.setPalette(QPalette())
            return

    if mode == "system":
        # Hand control back to the platform style. We deliberately
        # re-instantiate it so any palette we previously set on the
        # app gets replaced by the style's standardPalette().
        style_name = _native_style_name or "Fusion"
        style = QStyleFactory.create(style_name)
        if style is not None:
            app.setStyle(style)
            app.setPalette(style.standardPalette())
        return

    fusion = QStyleFactory.create("Fusion")
    if fusion is not None:
        app.setStyle(fusion)
    if mode == "dark":
        app.setPalette(_build_dark_palette())
    else:
        app.setPalette(_build_light_palette())
