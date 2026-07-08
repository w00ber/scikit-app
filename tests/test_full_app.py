"""Integration test: the full-featured demo composes and runs headless."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

pytest.importorskip("PySide6.QtWebEngineWidgets")
pytest.importorskip("markdown")

_DEMO = Path(__file__).resolve().parent.parent / "examples" / "full_app.py"


@pytest.fixture
def demo():
    spec = importlib.util.spec_from_file_location("sciappkit_full_demo", _DEMO)
    module = importlib.util.module_from_spec(spec)
    sys.argv = ["demo"]
    spec.loader.exec_module(module)
    return module


def test_full_app_builds(qapp, demo):
    win = demo.build_window()
    # Two canvases + two editor docks.
    assert len(win._controllers) == 2
    assert win.notes.backend == "web"
    assert win.code.language == "python"
    # Tools menu (Preferences + dock toggles) was added via the hook.
    assert hasattr(win, "_tools_menu")
    tool_labels = [a.text() for a in win._tools_menu.actions() if a.text()]
    assert any("Preferences" in t for t in tool_labels)


def test_full_app_document_roundtrip(qapp, demo, tmp_path):
    win = demo.build_window()
    doc = tmp_path / "doc.json"
    assert win.do_save(str(doc)) is True
    win.do_new()
    assert win.notes.toPlainText() == ""
    assert win.do_open(str(doc)) is True
    assert "Project notes" in win.notes.toPlainText()
    assert "lorentzian" in win.code.toPlainText()


def test_full_app_settings_apply_updates_canvas(qapp, demo):
    win = demo.build_window()
    dlg = win.build_settings_dialog()
    # Simulate the user editing the dialog widgets (apply reads widgets).
    for field, _read, write in dlg._binders:
        if field == "grid_spacing":
            write(33.0)
        elif field == "snap_to_grid":
            write(False)
    dlg.apply()  # emits applied -> _apply_settings
    assert win._scene_view.grid_spacing == 33.0
    assert win._scene_view.snap_enabled is False


def test_full_app_export(qapp, demo, tmp_path):
    win = demo.build_window()
    ctrl = win.active_controller()
    out = tmp_path / "canvas.png"
    ctrl.exporter.export_png(ctrl.export_target(), str(out))
    assert out.exists() and out.stat().st_size > 0
