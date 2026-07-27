"""A reusable Settings/Preferences dialog.

Edits a :class:`~sciappkit.settings.store.SettingsStore` through a tabbed
dialog: a **General** tab the app populates with field-binding helpers
(``add_bool`` / ``add_int`` / ``add_double`` / ``add_text`` / ``add_choice``),
an **Appearance** tab with a live theme selector (shown when the schema has
a ``theme`` field), and a **Shortcuts** tab embedding
:class:`~sciappkit.shortcuts.editor.ShortcutEditorWidget` (when a
``ShortcutManager`` is supplied).

OK/Apply write the store to disk; Cancel reverts to the values captured
when the dialog opened; "Restore Defaults" reseeds from the defaults
loader. Theme changes preview live and are rolled back on Cancel.
"""

from __future__ import annotations

import copy
from typing import Any, Callable, Sequence

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .theming import THEMES, apply_theme


class SettingsDialog(QDialog):
    """A tabbed settings editor bound to a :class:`SettingsStore`."""

    #: Emitted after settings are written (Apply / OK).
    applied = Signal()

    def __init__(self, settings, shortcuts=None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self._settings = settings
        self._shortcuts = shortcuts
        self._binders: list[tuple[str, Callable[[], Any], Callable[[Any], None]]] = []
        # Snapshot for revert-on-cancel (deep-copied for mutable values).
        self._snapshot = {
            name: copy.deepcopy(settings.get(name)) for name in settings.field_names()
        }
        self._theme_combo: QComboBox | None = None

        self._tabs = QTabWidget()
        self._general = QWidget()
        self._form = QFormLayout(self._general)
        self._tabs.addTab(self._general, "General")

        layout = QVBoxLayout(self)
        layout.addWidget(self._tabs)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Apply
            | QDialogButtonBox.StandardButton.RestoreDefaults
        )
        self._buttons.accepted.connect(self._on_ok)
        self._buttons.rejected.connect(self._on_cancel)
        self._buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply)
        self._buttons.button(QDialogButtonBox.StandardButton.RestoreDefaults).clicked.connect(
            self.restore_defaults
        )
        layout.addWidget(self._buttons)

        # Optional built-in tabs.
        if "theme" in settings.field_names():
            self._build_appearance_tab()
        if shortcuts is not None:
            self._build_shortcuts_tab()

    # -- field-binding helpers (populate the General tab) --------------------

    def add_bool(self, field: str, label: str) -> QCheckBox:
        w = QCheckBox()
        w.setChecked(bool(self._settings.get(field)))
        self._register(field, w, w.isChecked, lambda v: w.setChecked(bool(v)))
        self._form.addRow(label, w)
        return w

    def add_int(self, field: str, label: str, *, minimum: int = 0, maximum: int = 1_000_000, step: int = 1) -> QSpinBox:
        w = QSpinBox()
        w.setRange(minimum, maximum)
        w.setSingleStep(step)
        w.setValue(int(self._settings.get(field)))
        self._register(field, w, w.value, lambda v: w.setValue(int(v)))
        self._form.addRow(label, w)
        return w

    def add_double(
        self, field: str, label: str, *,
        minimum: float = 0.0, maximum: float = 1_000_000.0, step: float = 1.0, decimals: int = 2,
    ) -> QDoubleSpinBox:
        w = QDoubleSpinBox()
        w.setRange(minimum, maximum)
        w.setSingleStep(step)
        w.setDecimals(decimals)
        w.setValue(float(self._settings.get(field)))
        self._register(field, w, w.value, lambda v: w.setValue(float(v)))
        self._form.addRow(label, w)
        return w

    def add_text(self, field: str, label: str) -> QLineEdit:
        w = QLineEdit(str(self._settings.get(field) or ""))
        self._register(field, w, w.text, lambda v: w.setText(str(v or "")))
        self._form.addRow(label, w)
        return w

    def add_choice(self, field: str, label: str, choices: Sequence[Any]) -> QComboBox:
        w = QComboBox()
        for choice in choices:
            w.addItem(str(choice), choice)
        self._select_value(w, self._settings.get(field))
        self._register(field, w, lambda: w.currentData(), lambda v: self._select_value(w, v))
        self._form.addRow(label, w)
        return w

    def add_button(self, label: str, text: str, slot: Callable[[], None]) -> QPushButton:
        """Add an immediate-action button row to the General tab.

        Unlike the field binders, the button is not bound to a setting:
        *slot* runs when clicked, independent of OK/Apply/Cancel (use for
        one-shot actions like resetting a window layout)."""
        w = QPushButton(text)
        w.clicked.connect(slot)
        self._form.addRow(label, w)
        return w

    # -- built-in tabs ------------------------------------------------------

    def _build_appearance_tab(self) -> None:
        tab = QWidget()
        form = QFormLayout(tab)
        combo = QComboBox()
        for mode in THEMES:
            combo.addItem(mode.capitalize(), mode)
        self._select_value(combo, self._settings.get("theme"))
        combo.currentIndexChanged.connect(lambda _i: self._preview_theme(combo.currentData()))
        self._theme_combo = combo
        self._register("theme", combo, lambda: combo.currentData(),
                       lambda v: self._select_value(combo, v))
        form.addRow("Theme", combo)
        self._tabs.addTab(tab, "Appearance")

    def _build_shortcuts_tab(self) -> None:
        from ..shortcuts.editor import ShortcutEditorWidget

        self._shortcut_editor = ShortcutEditorWidget(self._shortcuts)
        self._tabs.addTab(self._shortcut_editor, "Shortcuts")

    # -- internals ----------------------------------------------------------

    def _register(self, field: str, widget, read: Callable[[], Any], write: Callable[[Any], None]) -> None:
        self._binders.append((field, read, write))

    @staticmethod
    def _select_value(combo: QComboBox, value: Any) -> None:
        idx = combo.findData(value)
        if idx < 0:
            idx = max(0, combo.findText(str(value)))
        combo.setCurrentIndex(idx)

    def _preview_theme(self, mode: str) -> None:
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is not None and mode in THEMES:
            apply_theme(app, mode)

    def _refresh_widgets(self) -> None:
        for field, _read, write in self._binders:
            write(self._settings.get(field))

    # -- actions ------------------------------------------------------------

    def apply(self) -> None:
        for field, read, _write in self._binders:
            self._settings.set(field, read())
        self._settings.save()
        if self._shortcuts is not None:
            self._shortcuts.save()
        self.applied.emit()

    def restore_defaults(self) -> None:
        self._settings.reset_all()
        self._refresh_widgets()
        if self._theme_combo is not None:
            self._preview_theme(self._settings.get("theme"))

    def _on_ok(self) -> None:
        self.apply()
        self.accept()

    def _on_cancel(self) -> None:
        # Roll back to the values captured when the dialog opened.
        for name, value in self._snapshot.items():
            self._settings.set(name, copy.deepcopy(value))
        if self._theme_combo is not None:
            self._preview_theme(self._settings.get("theme"))
        self.reject()
