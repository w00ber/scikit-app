"""Import smoke tests.

Confirms the top-level package and every M0 submodule import cleanly on
the pinned Qt 6.8 line. The submodules pull in PySide6 / matplotlib, so a
QApplication is ensured via the ``qapp`` fixture first.
"""

from __future__ import annotations

import importlib

import pytest

SUBMODULES = [
    "sciappkit",
    # M0 lift-and-shift
    "sciappkit.app.theming",
    "sciappkit.canvas.grid",
    "sciappkit.canvas.mpl_canvas",
    "sciappkit.export.clipboard",
    "sciappkit.settings.defaults",
    "sciappkit.widgets.spinbox",
    # M1 normalized APIs
    "sciappkit.settings.store",
    "sciappkit.settings.recent_files",
    "sciappkit.shortcuts.model",
    "sciappkit.shortcuts.manager",
    "sciappkit.export.base",
    "sciappkit.export.mpl_exporter",
    "sciappkit.export.scene_exporter",
    "sciappkit.canvas.scene_canvas",
    "sciappkit.canvas.protocol",
    "sciappkit.app.main_window",
    # M1 editor widgets
    "sciappkit.widgets.text_edit",
    "sciappkit.widgets.code_editor",
    "sciappkit.widgets.markdown_editor",
]


def test_top_level_import_is_lightweight():
    # Importing the package alone must not require Qt/matplotlib.
    mod = importlib.import_module("sciappkit")
    assert hasattr(mod, "__version__")


@pytest.mark.parametrize("name", SUBMODULES)
def test_submodule_imports(qapp, name):
    importlib.import_module(name)


def test_pyside_on_68_line():
    import PySide6

    major, minor = (int(p) for p in PySide6.__version__.split(".")[:2])
    assert (major, minor) >= (6, 8)
    assert (major, minor) < (6, 9), f"expected the 6.8 line, got {PySide6.__version__}"
