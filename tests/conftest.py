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

import pytest


@pytest.fixture(scope="session")
def qapp():
    """Return a process-wide QApplication, creating it once if needed."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app
