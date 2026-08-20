"""Shared pytest fixtures and headless Qt configuration.

Importing any Qt-backed module requires a usable QPA platform. We default
to the ``offscreen`` platform so the suite runs with no display and no
extra system X libraries. Set ``QT_QPA_PLATFORM`` in the environment
(e.g. ``xcb`` under ``xvfb-run``) to override.
"""

from __future__ import annotations

import os

# Must be set before the first PySide6 import anywhere in the test process.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# QtWebEngine's Chromium needs the sandbox disabled in restricted/headless
# environments (the [web] markdown preview). Harmless when QtWebEngine is
# unused.
os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")
os.environ.setdefault(
    "QTWEBENGINE_CHROMIUM_FLAGS",
    "--no-sandbox --disable-gpu --disable-dev-shm-usage",
)

import pytest


@pytest.fixture(scope="session")
def qapp():
    """Return a process-wide QApplication, creating it once if needed."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture()
def qt_clipboard(monkeypatch):
    """Force the Qt clipboard path.

    On macOS `copy_to_clipboard` deliberately writes PDF/SVG straight to
    NSPasteboard via ctypes, which is the better path and the one users
    get — but it means Qt's own `QMimeData` never sees those flavours. A
    test that then inspects `qapp.clipboard().mimeData()` is asserting
    about the Qt fallback, so it has to ask for it rather than depend on
    the host not being a Mac.

    `export.clipboard` does `import sys` inside the function, so patching
    `sys.platform` itself is what reaches it.
    """
    import sys

    monkeypatch.setattr(sys, "platform", "linux")
    yield
