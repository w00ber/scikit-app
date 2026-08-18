"""Tests for sciappkit.app.about and the base window's About wiring."""

from __future__ import annotations

from sciappkit.app.about import (
    AboutInfo,
    about_info,
    base_components,
    diagnostics_text,
)
from sciappkit.app.main_window import SciAppMainWindow
from sciappkit.canvas.protocol import SceneCanvasController
from sciappkit.canvas.scene_canvas import GraphicsSceneBase, GraphicsViewBase
from sciappkit.settings.store import Setting, SettingsStore
from sciappkit.shortcuts.manager import ShortcutManager
from sciappkit.shortcuts.model import ShortcutRegistry


def _window(tmp_path, name="wintest", extra_help=False):
    scene = GraphicsSceneBase()
    scene.addRect(0, 0, 10, 10)
    ctrl = SceneCanvasController(GraphicsViewBase(scene))
    settings = SettingsStore(
        name, [Setting("theme", "system", section="theme", key="mode")],
        settings_dir=tmp_path,
    )
    shortcuts = ShortcutManager(
        ShortcutRegistry(platform="linux"), name, config_path=tmp_path / "sc.json"
    )

    class Win(SciAppMainWindow):
        def populate_extra_menus(self, menubar):
            if extra_help:
                self.help_menu().addAction("&Manual…", lambda: None)

        def about_components(self):
            return {"widget-engine": "1.2.3", "absent": ""}

    return Win(name, settings, shortcuts, ctrl)


# -- the pure half ----------------------------------------------------------

def test_missing_metadata_is_never_fatal():
    """A distribution that is not installed still yields a usable box."""
    info = about_info("Nope", "definitely-not-installed-xyz")
    assert info.app_name == "Nope"
    assert info.version == ""
    assert info.urls == {}
    # the shared rows are still there, so the dialog is never empty
    assert "Python" in info.components


def test_app_components_override_and_blanks_are_dropped():
    info = about_info("Kit", "sciappkit",
                      components={"VTK": "9.6.2", "missing": ""})
    assert info.components["VTK"] == "9.6.2"
    assert "missing" not in info.components


def test_the_installed_distribution_is_reported():
    info = about_info("Kit", "sciappkit")
    assert info.version  # sciappkit is installed in the test env
    assert info.components["Kit"] == info.version


def test_base_components_name_python_and_qt():
    comps = base_components()
    assert comps["Python"]
    assert comps["Qt"]


def test_diagnostics_is_one_name_value_per_line():
    info = AboutInfo(app_name="X", version="1.0",
                     components={"a": "1", "b": "2"})
    lines = diagnostics_text(info).splitlines()
    assert lines[0] == "a: 1"
    assert lines[1] == "b: 2"
    assert lines[-1].startswith("Executable: ")


def test_a_full_licence_text_becomes_a_body_not_a_label():
    """`license = {file=...}` puts the WHOLE licence in the metadata; it
    must not end up as the one-line label beside the version."""
    info = about_info("Kit", "fabulator")
    if not info.license_text:      # standalone sciappkit checkout
        return
    assert "\n" in info.license_text
    assert len(info.license_label) <= 60


# -- the window wiring ------------------------------------------------------

def test_about_lands_in_one_help_menu(qapp, tmp_path):
    win = _window(tmp_path)
    titles = [a.text() for a in win.menuBar().actions()]
    assert sum("Help" in t for t in titles) == 1
    assert any("About" in a.text() for a in win.help_menu().actions())


def test_an_apps_own_help_entries_keep_their_menu(qapp, tmp_path):
    """The app adds to Help in populate_extra_menus; About appends after."""
    win = _window(tmp_path, extra_help=True)
    texts = [a.text() for a in win.help_menu().actions() if a.text()]
    assert texts[0] == "&Manual…"
    assert "About" in texts[-1]
    assert sum("Help" in a.text() for a in win.menuBar().actions()) == 1


def test_the_about_action_carries_the_mac_role(qapp, tmp_path):
    from PySide6.QtGui import QAction

    win = _window(tmp_path)
    act = next(a for a in win.help_menu().actions() if "About" in a.text())
    assert act.menuRole() == QAction.MenuRole.AboutRole


def test_help_menu_is_created_once(qapp, tmp_path):
    win = _window(tmp_path)
    assert win.help_menu() is win.help_menu()


def test_the_apps_components_reach_the_dialog(qapp, tmp_path):
    win = _window(tmp_path)
    info = about_info(win.about_display_name(), win.about_distribution(),
                      components=win.about_components())
    assert info.components["widget-engine"] == "1.2.3"
    assert "absent" not in info.components


def test_copy_diagnostics_puts_the_block_on_the_clipboard(qapp, tmp_path):
    from PySide6.QtGui import QGuiApplication

    from sciappkit.app.about import AboutDialog

    win = _window(tmp_path)
    info = about_info(win.about_display_name(), win.about_distribution(),
                      components=win.about_components())
    dlg = AboutDialog(info, parent=win)
    dlg.copy_button.click()
    assert QGuiApplication.clipboard().text() == diagnostics_text(info)
