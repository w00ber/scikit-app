"""Integration test: the editors demo composes and runs headless."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_DEMO = Path(__file__).resolve().parent.parent / "examples" / "editors_demo.py"


@pytest.fixture
def demo():
    spec = importlib.util.spec_from_file_location("sciappkit_editors_demo", _DEMO)
    module = importlib.util.module_from_spec(spec)
    sys.argv = ["demo"]
    spec.loader.exec_module(module)
    return module


def test_editors_demo_builds(qapp, demo):
    win = demo.build_window()
    assert win._tabs.count() == 2
    # Code editor highlighting produced format ranges.
    assert win._code.document().findBlockByNumber(0).layout().formats()
    # Markdown preview rendered the heading.
    assert "Notes" in win._notes.preview.toPlainText()


def test_editors_demo_shortcuts_bound(qapp, demo):
    from PySide6.QtGui import QShortcut

    win = demo.build_window()
    assert win._code.findChildren(QShortcut)
    assert win._notes.findChildren(QShortcut)
    assert win._code._use_builtin_command_keys is False
    assert win._notes.editor._use_builtin_command_keys is False
