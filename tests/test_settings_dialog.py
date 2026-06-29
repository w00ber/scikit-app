"""Tests for sciappkit.app.settings_dialog.SettingsDialog."""

from __future__ import annotations

from sciappkit.app.settings_dialog import SettingsDialog
from sciappkit.settings.store import Setting, SettingsStore
from sciappkit.shortcuts.manager import ShortcutManager
from sciappkit.shortcuts.model import Shortcut, ShortcutRegistry


def _settings(tmp_path):
    schema = [
        Setting("theme", "system", section="theme", key="mode"),
        Setting("snap", True),
        Setting("grid_spacing", 20.0, section="grid", key="spacing"),
        Setting("title", "Untitled"),
        Setting("mode", "ortho"),
    ]
    return SettingsStore("sdtest", schema, settings_dir=tmp_path)


def _populate(dlg):
    dlg.add_bool("snap", "Snap to grid")
    dlg.add_double("grid_spacing", "Grid spacing", minimum=1, maximum=100, step=1)
    dlg.add_text("title", "Title")
    dlg.add_choice("mode", "Routing", ["ortho", "direct", "curved"])


def test_apply_writes_widget_values(qapp, tmp_path):
    settings = _settings(tmp_path)
    dlg = SettingsDialog(settings)
    snap = dlg.add_bool("snap", "Snap to grid")
    spacing = dlg.add_double("grid_spacing", "Grid spacing", minimum=1, maximum=100)
    snap.setChecked(False)
    spacing.setValue(12.0)
    dlg.apply()
    assert settings.snap is False
    assert settings.grid_spacing == 12.0
    # Persisted to disk.
    import json

    data = json.loads(settings.path.read_text())
    assert data["grid_spacing"] == 12.0


def test_cancel_reverts(qapp, tmp_path):
    settings = _settings(tmp_path)
    dlg = SettingsDialog(settings)
    spacing = dlg.add_double("grid_spacing", "Grid spacing", minimum=1, maximum=100)
    spacing.setValue(99.0)
    dlg._on_cancel()
    # Store rolled back to the value captured at open.
    assert settings.grid_spacing == 20.0


def test_choice_binding(qapp, tmp_path):
    settings = _settings(tmp_path)
    dlg = SettingsDialog(settings)
    combo = dlg.add_choice("mode", "Routing", ["ortho", "direct", "curved"])
    combo.setCurrentIndex(combo.findData("curved"))
    dlg.apply()
    assert settings.mode == "curved"


def test_restore_defaults_reseeds(qapp, tmp_path):
    loader_settings = _settings(tmp_path)
    dlg = SettingsDialog(loader_settings)
    spacing = dlg.add_double("grid_spacing", "Grid spacing", minimum=1, maximum=100)
    spacing.setValue(77.0)
    dlg.apply()
    dlg.restore_defaults()
    # Field default (no loader value) -> literal 20.0, and the widget refreshed.
    assert loader_settings.grid_spacing == 20.0
    assert spacing.value() == 20.0


def test_appearance_tab_present_with_theme_field(qapp, tmp_path):
    dlg = SettingsDialog(_settings(tmp_path))
    titles = [dlg._tabs.tabText(i) for i in range(dlg._tabs.count())]
    assert "Appearance" in titles
    assert dlg._theme_combo is not None


def test_theme_preview_applies_live(qapp, tmp_path):
    settings = _settings(tmp_path)
    dlg = SettingsDialog(settings)
    dlg._theme_combo.setCurrentIndex(dlg._theme_combo.findData("dark"))
    # Live preview applied a dark palette to the app.
    from PySide6.QtGui import QPalette

    win = qapp.palette().color(QPalette.ColorRole.Window)
    assert win.lightness() < 128
    # Committing persists the choice.
    dlg.apply()
    assert settings.theme == "dark"
    # Restore neutral theme for other tests.
    from sciappkit.app.theming import apply_theme

    apply_theme(qapp, "system")


def test_shortcuts_tab_present(qapp, tmp_path):
    reg = ShortcutRegistry(platform="linux")
    reg.register(Shortcut("file.new", default="Ctrl+N", category="File", display_name="New"))
    mgr = ShortcutManager(reg, "sdtest", config_path=tmp_path / "sc.json")
    dlg = SettingsDialog(_settings(tmp_path), shortcuts=mgr)
    titles = [dlg._tabs.tabText(i) for i in range(dlg._tabs.count())]
    assert "Shortcuts" in titles


def test_no_appearance_tab_without_theme_field(qapp, tmp_path):
    settings = SettingsStore("noth", [Setting("snap", True)], settings_dir=tmp_path)
    dlg = SettingsDialog(settings)
    titles = [dlg._tabs.tabText(i) for i in range(dlg._tabs.count())]
    assert "Appearance" not in titles
