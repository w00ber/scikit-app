"""Integration test: the hand-written example app composes and runs.

Guards that the M1 public API keeps composing into a working application
(the example under ``examples/``). Runs headless via the ``qapp`` fixture.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_DEMO = Path(__file__).resolve().parent.parent / "examples" / "demo_app.py"


@pytest.fixture
def demo_module():
    spec = importlib.util.spec_from_file_location("sciappkit_demo_app", _DEMO)
    module = importlib.util.module_from_spec(spec)
    sys.argv = ["demo"]  # avoid --selftest hard-exit path
    spec.loader.exec_module(module)
    return module


def test_example_builds_two_canvas_window(qapp, demo_module):
    win = demo_module.build_window()
    assert win.windowTitle().endswith("sciappkit demo")
    assert len(win._controllers) == 2


@pytest.mark.parametrize(
    "style,expected", [("scene", 1), ("mpl", 1), ("both", 2)]
)
def test_example_builds_each_canvas_style(qapp, demo_module, style, expected):
    # Mirrors the M2 scaffold's canvas_style question: each style builds a
    # working window with the right number of canvases.
    win = demo_module.build_window(style)
    assert len(win._controllers) == expected


@pytest.mark.parametrize("style", ["scene", "mpl", "both"])
def test_example_exports_each_style(qapp, demo_module, tmp_path, style):
    win = demo_module.build_window(style)
    for i, ctrl in enumerate(win._controllers):
        for fmt in ("svg", "png", "pdf"):
            path = tmp_path / f"{style}_c{i}.{fmt}"
            getattr(ctrl.exporter, f"export_{fmt}")(ctrl.export_target(), str(path))
            assert path.exists() and path.stat().st_size > 0


def test_example_copy_and_tab_switch(qapp, demo_module):
    win = demo_module.build_window()
    win._copy_to_clipboard()
    assert qapp.clipboard().mimeData().hasImage()
    win._tabs.setCurrentIndex(1)
    assert win.active_controller() is win._controllers[1]
