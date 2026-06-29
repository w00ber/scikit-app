"""``SciAppMainWindow`` — the base window that wires the framework together.

New glue (not lifted): a ``QMainWindow`` base that owns the menus, the
active-canvas resolver, Export/Copy delegation, theming, shortcut
registration (via the injected :class:`ShortcutManager`), and
title/dirty plumbing. Apps subclass it, supply one or more
:class:`~sciappkit.canvas.protocol.CanvasController` instances, and
override the document hooks (:meth:`do_new` / :meth:`do_open` /
:meth:`do_save`).

It stays canvas-agnostic by driving every export through the controller's
uniform ``exporter`` + ``export_target()`` (the plan's thin protocol), and
settings-schema-agnostic by touching settings fields defensively (theme,
last directory) only when the app's schema actually defines them.

Help / Tutorial / Examples menus are a later milestone; a
:meth:`populate_extra_menus` hook is provided so apps can add menus now.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Sequence

from PySide6.QtCore import QEvent, QObject, Signal
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QTabWidget,
    QWidget,
)

from ..canvas.protocol import CanvasController
from .theming import THEMES, apply_theme

logger = logging.getLogger(__name__)

_EXPORT_FORMATS = ("svg", "png", "pdf")


class SciAppMainWindow(QMainWindow):
    """Base main window for a sciappkit application."""

    #: Emitted after the chrome theme changes (so canvases can re-pin surfaces).
    theme_changed = Signal(str)

    def __init__(
        self,
        app_name: str,
        settings,
        shortcuts,
        controllers: CanvasController | Sequence[CanvasController],
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._app_name = app_name
        self._settings = settings
        self._shortcuts = shortcuts
        if isinstance(controllers, CanvasController):
            controllers = [controllers]
        self._controllers: list[CanvasController] = list(controllers)
        if not self._controllers:
            raise ValueError("SciAppMainWindow requires at least one CanvasController")
        self._active_controller = self._controllers[0]
        self._current_file: str | None = None

        self._build_central()
        self._build_menus()
        self.apply_theme()
        self._shortcuts.apply_all()
        self._update_title()

    # -- central widget / active-controller tracking ------------------------

    def _build_central(self) -> None:
        if len(self._controllers) == 1:
            self.setCentralWidget(self._controllers[0].widget())
        else:
            self._tabs = QTabWidget()
            for index, ctrl in enumerate(self._controllers):
                title_fn = getattr(ctrl, "title", None)
                label = title_fn() if callable(title_fn) else f"Canvas {index + 1}"
                self._tabs.addTab(ctrl.widget(), label)
            self._tabs.currentChanged.connect(self._on_tab_changed)
            self.setCentralWidget(self._tabs)
        # Track focus to resolve the active controller in split layouts.
        for ctrl in self._controllers:
            ctrl.widget().installEventFilter(self)

    def _on_tab_changed(self, index: int) -> None:
        if 0 <= index < len(self._controllers):
            self._active_controller = self._controllers[index]
            self._sync_export_actions()

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.FocusIn:
            for ctrl in self._controllers:
                w = ctrl.widget()
                if w is obj or w.isAncestorOf(obj):
                    self._active_controller = ctrl
                    self._sync_export_actions()
                    break
        return super().eventFilter(obj, event)

    def active_controller(self) -> CanvasController:
        """Return the controller that currently has focus (or last active)."""
        fw = QApplication.focusWidget()
        if fw is not None:
            for ctrl in self._controllers:
                w = ctrl.widget()
                if w is fw or w.isAncestorOf(fw):
                    self._active_controller = ctrl
                    break
        return self._active_controller

    # -- menu construction --------------------------------------------------

    def _add_action(
        self,
        menu,
        text: str,
        slot,
        shortcut_id: str | None = None,
        *,
        checkable: bool = False,
    ) -> QAction:
        """Create an action, bind its shortcut via the manager, and add it."""
        act = QAction(text, self)
        if checkable:
            act.setCheckable(True)
        if shortcut_id and self._shortcuts.registry.get(shortcut_id) is not None:
            self._shortcuts.apply_to(shortcut_id, act)
        act.triggered.connect(slot)
        menu.addAction(act)
        return act

    def _build_menus(self) -> None:
        bar = self.menuBar()
        self._build_file_menu(bar.addMenu("&File"))
        self._build_edit_menu(bar.addMenu("&Edit"))
        self._build_view_menu(bar.addMenu("&View"))
        self.populate_extra_menus(bar)

    def _build_file_menu(self, menu) -> None:
        self._add_action(menu, "&New", self._file_new, "file.new")
        self._add_action(menu, "&Open…", self._file_open, "file.open")
        menu.addSeparator()
        self._add_action(menu, "&Save", self._file_save, "file.save")
        self._add_action(menu, "Save &As…", self._file_save_as, "file.save_as")
        menu.addSeparator()
        export_menu = menu.addMenu("&Export")
        self._export_actions: dict[str, QAction] = {}
        for fmt in _EXPORT_FORMATS:
            self._export_actions[fmt] = self._add_action(
                export_menu, f"Export as {fmt.upper()}…",
                lambda checked=False, f=fmt: self._export(f),
                f"file.export_{fmt}",
            )
        menu.addSeparator()
        self._add_action(menu, "&Quit", self.close, "file.quit")
        self._sync_export_actions()

    def _build_edit_menu(self, menu) -> None:
        self._add_action(menu, "&Undo", self._undo, "edit.undo")
        self._add_action(menu, "&Redo", self._redo, "edit.redo")
        menu.addSeparator()
        self._add_action(
            menu, "&Copy to Clipboard", self._copy_to_clipboard, "edit.copy_as_image"
        )

    def _build_view_menu(self, menu) -> None:
        self._add_action(menu, "Fit to Content", self._fit_to_content, "view.fit")
        self._add_action(menu, "Zoom In", self._zoom_in, "view.zoom_in")
        self._add_action(menu, "Zoom Out", self._zoom_out, "view.zoom_out")
        menu.addSeparator()
        appearance = menu.addMenu("&Appearance")
        group = QActionGroup(self)
        group.setExclusive(True)
        current = self._theme_mode()
        for mode in THEMES:
            act = QAction(mode.capitalize(), self, checkable=True)
            act.setChecked(mode == current)
            act.triggered.connect(lambda checked=False, m=mode: self.apply_theme(m))
            group.addAction(act)
            appearance.addAction(act)

    def populate_extra_menus(self, menubar) -> None:
        """Hook for subclasses to add menus (default: no-op)."""

    # -- export / copy ------------------------------------------------------

    def _sync_export_actions(self) -> None:
        """Enable only the export formats the active exporter supports."""
        actions = getattr(self, "_export_actions", None)
        if not actions:
            return
        exporter = self.active_controller().exporter
        for fmt, act in actions.items():
            act.setEnabled(hasattr(exporter, f"export_{fmt}"))

    def _export(self, fmt: str) -> None:
        ctrl = self.active_controller()
        exporter = ctrl.exporter
        method = getattr(exporter, f"export_{fmt}", None)
        if method is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, f"Export {fmt.upper()}", self._last_dir(), f"{fmt.upper()} (*.{fmt})"
        )
        if not path:
            return
        try:
            method(ctrl.export_target(), path)
        except Exception:
            logger.exception("Export to %s failed", path)
            return
        self._remember_dir(path)

    def _copy_to_clipboard(self) -> None:
        ctrl = self.active_controller()
        if ctrl.exporter.copy_to_clipboard(ctrl.export_target()):
            self.statusBar().showMessage("Copied to clipboard", 4000)

    # -- view ops -----------------------------------------------------------

    def _fit_to_content(self) -> None:
        self.active_controller().fit_to_content()

    def _zoom_in(self) -> None:
        self._zoom(1)

    def _zoom_out(self) -> None:
        self._zoom(-1)

    def _zoom(self, direction: int) -> None:
        widget = self.active_controller().widget()
        name = "zoom_in" if direction > 0 else "zoom_out"
        fn = getattr(widget, name, None)
        if callable(fn):
            fn()

    # -- undo / redo (delegated to the active scene's undo stack) ------------

    def _active_undo_stack(self):
        target = self.active_controller().export_target()
        return getattr(target, "undo_stack", None)

    def _undo(self) -> None:
        stack = self._active_undo_stack()
        if stack is not None:
            stack.undo()

    def _redo(self) -> None:
        stack = self._active_undo_stack()
        if stack is not None:
            stack.redo()

    # -- theme --------------------------------------------------------------

    def _theme_mode(self) -> str:
        mode = getattr(self._settings, "theme", "system")
        return mode if mode in THEMES else "system"

    def apply_theme(self, mode: str | None = None) -> None:
        """Apply *mode* (or the saved theme) and persist it if possible."""
        mode = mode or self._theme_mode()
        app = QApplication.instance()
        if app is not None:
            apply_theme(app, mode)
        if "theme" in getattr(self._settings, "field_names", lambda: [])():
            self._settings.theme = mode
            self._settings.save()
        self.theme_changed.emit(mode)

    # -- document state -----------------------------------------------------

    @property
    def current_file(self) -> str | None:
        return self._current_file

    def _update_title(self) -> None:
        name = Path(self._current_file).name if self._current_file else "Untitled"
        self.setWindowTitle(f"{name} — {self._app_name}")

    def is_dirty(self) -> bool:
        """True if any canvas with an undo stack has unsaved changes."""
        for ctrl in self._controllers:
            stack = getattr(ctrl.export_target(), "undo_stack", None)
            if stack is not None and not stack.isClean():
                return True
        return False

    # -- File-menu slots (delegate document I/O to overridable hooks) -------

    def _file_new(self) -> None:
        self.do_new()
        self._current_file = None
        self._update_title()

    def _file_open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open", self._last_dir())
        if not path:
            return
        if self.do_open(path):
            self._current_file = path
            self._remember_dir(path)
            self._update_title()

    def _file_save(self) -> None:
        if self._current_file is None:
            self._file_save_as()
            return
        if self.do_save(self._current_file):
            self._mark_clean()

    def _file_save_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save As", self._last_dir())
        if not path:
            return
        if self.do_save(path):
            self._current_file = path
            self._remember_dir(path)
            self._update_title()
            self._mark_clean()

    def _mark_clean(self) -> None:
        for ctrl in self._controllers:
            stack = getattr(ctrl.export_target(), "undo_stack", None)
            if stack is not None:
                stack.setClean()

    # -- document hooks (subclasses override) -------------------------------

    def do_new(self) -> None:
        """Reset to a blank document. Override in the app."""

    def do_open(self, path: str) -> bool:
        """Load the document at *path*; return True on success. Override."""
        return False

    def do_save(self, path: str) -> bool:
        """Write the document to *path*; return True on success. Override."""
        return False

    # -- last-directory helpers (only if the schema defines the field) ------

    def _last_dir(self) -> str:
        return getattr(self._settings, "last_directory", "") or ""

    def _remember_dir(self, path: str) -> None:
        if "last_directory" in getattr(self._settings, "field_names", lambda: [])():
            self._settings.last_directory = str(Path(path).parent)
            self._settings.save()
