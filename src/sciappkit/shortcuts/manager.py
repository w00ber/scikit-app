"""Qt glue for the shortcut system: signals, QAction binding, persistence.

Wraps a :class:`~sciappkit.shortcuts.model.ShortcutRegistry` (the pure
data layer) and adds what a running app needs: change signals, live
binding to ``QAction`` / ``QShortcut`` (re-pushed when a binding changes),
an input-focus guard for bare single-key shortcuts, conflict-guarded
edits, and JSON persistence to ``~/.<app_name>/shortcuts.json``.

Both source apps left persistence to the caller; this is where the
framework closes that gap. Only non-default overrides are written, so
shipped defaults can change without leaving stale entries on disk.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import QWidget

from .model import ShortcutRegistry, portable_text

logger = logging.getLogger(__name__)

PERSISTENCE_VERSION = 1


class ShortcutManager(QObject):
    """Per-app shortcut controller over a :class:`ShortcutRegistry`."""

    #: Emitted on any change (rebind / reset / import) — invalidate caches.
    shortcuts_changed = Signal()
    #: Emitted on a single rebind: (action_id, old_portable, new_portable).
    shortcut_updated = Signal(str, str, str)

    def __init__(
        self,
        registry: ShortcutRegistry,
        app_name: str,
        parent: QObject | None = None,
        *,
        config_path: Path | None = None,
    ) -> None:
        super().__init__(parent)
        self._registry = registry
        self._app_name = app_name
        self._config_path = (
            Path(config_path)
            if config_path is not None
            else Path.home() / f".{app_name}" / "shortcuts.json"
        )
        self._actions: dict[str, list[QAction]] = {}
        self._qshortcuts: dict[str, list[QShortcut]] = {}
        self._input_focus_wrapper: Callable[[Callable], Callable] | None = None

    # -- accessors ----------------------------------------------------------

    @property
    def registry(self) -> ShortcutRegistry:
        return self._registry

    @property
    def platform(self) -> str:
        return self._registry.platform

    @property
    def config_path(self) -> Path:
        return self._config_path

    def sequence(self, action_id: str) -> QKeySequence:
        return self._registry.sequence(action_id)

    def default_sequence(self, action_id: str) -> QKeySequence:
        return self._registry.default_sequence(action_id)

    def display_text(self, action_id: str) -> str:
        return self._registry.display_text(action_id)

    def conflicts(self, proposed: dict[str, str] | None = None) -> dict[str, list[str]]:
        return self._registry.conflicts(proposed)

    def conflict_for(self, seq: QKeySequence | str, exclude: str | None = None) -> str | None:
        return self._registry.conflict_for(seq, exclude)

    # -- input-focus guard --------------------------------------------------

    def set_input_focus_wrapper(self, wrapper: Callable[[Callable], Callable]) -> None:
        """Install a wrapper that suppresses single-key shortcuts in inputs.

        ``wrapper(handler) -> handler`` is applied to the handler of any
        :attr:`Shortcut.is_single_key` binding created via
        :meth:`bind_shortcut`.
        """
        self._input_focus_wrapper = wrapper

    # -- edits (conflict-guarded; emit signals; live-update) ----------------

    def set_sequence(self, action_id: str, seq: QKeySequence | str | None) -> bool:
        """Rebind *action_id*. Returns ``False`` (no-op) on conflict."""
        sc = self._registry.get(action_id)
        if sc is None:
            return False
        new_portable = portable_text(seq) if seq not in (None, "") else ""
        if new_portable and self._registry.conflict_for(new_portable, exclude=action_id):
            return False
        old_portable = portable_text(self._registry.sequence(action_id))
        self._registry.set_override(action_id, seq)
        self._refresh(action_id)
        self.shortcut_updated.emit(action_id, old_portable, new_portable)
        self.shortcuts_changed.emit()
        return True

    def clear_sequence(self, action_id: str) -> None:
        old_portable = portable_text(self._registry.sequence(action_id))
        self._registry.set_override(action_id, "")
        self._refresh(action_id)
        self.shortcut_updated.emit(action_id, old_portable, "")
        self.shortcuts_changed.emit()

    def reset(self, action_id: str) -> None:
        self._registry.reset(action_id)
        self._refresh(action_id)
        self.shortcuts_changed.emit()

    def reset_all(self) -> None:
        self._registry.reset_all()
        for action_id in self._registry.action_ids():
            self._refresh(action_id)
        self.shortcuts_changed.emit()

    # -- Qt binding ---------------------------------------------------------

    def apply_to(self, action_id: str, action: QAction) -> bool:
        """Bind *action* to *action_id* and track it for live updates."""
        self._actions.setdefault(action_id, []).append(action)
        action.setShortcut(self._registry.sequence(action_id))
        return True

    def bind_shortcut(
        self,
        action_id: str,
        handler: Callable,
        parent: QWidget,
        *,
        wrap_for_input: bool = False,
        context: Qt.ShortcutContext = Qt.ShortcutContext.WindowShortcut,
    ) -> QShortcut | None:
        """Create a tracked ``QShortcut`` for a keys-without-a-menu action."""
        sc = self._registry.get(action_id)
        if sc is None:
            return None
        if wrap_for_input and self._input_focus_wrapper is not None:
            handler = self._input_focus_wrapper(handler)
        qsc = QShortcut(self._registry.sequence(action_id), parent)
        qsc.setContext(context)
        qsc.activated.connect(handler)
        self._qshortcuts.setdefault(action_id, []).append(qsc)
        return qsc

    def apply_all(self) -> None:
        """Re-push the current sequence onto every bound action/shortcut."""
        for action_id in set(self._actions) | set(self._qshortcuts):
            self._refresh(action_id)

    def _refresh(self, action_id: str) -> None:
        seq = self._registry.sequence(action_id)
        for action in self._actions.get(action_id, []):
            action.setShortcut(seq)
        for qsc in self._qshortcuts.get(action_id, []):
            qsc.setKey(seq)

    # -- JSON persistence ---------------------------------------------------

    def save(self) -> None:
        """Persist non-default overrides (best effort)."""
        payload = {
            "version": PERSISTENCE_VERSION,
            "platform": self._registry.platform,
            "overrides": self._registry.export_overrides(),
        }
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            self._config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError as exc:
            logger.debug("Failed to save shortcuts to %s: %s", self._config_path, exc)

    def load(self) -> None:
        """Load overrides from disk, tolerating a missing/corrupt file."""
        try:
            data = json.loads(self._config_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return
        except (OSError, ValueError) as exc:
            logger.debug("Failed to load shortcuts from %s: %s", self._config_path, exc)
            return
        overrides = data.get("overrides") if isinstance(data, dict) else None
        if isinstance(overrides, dict):
            self._registry.import_overrides(overrides)
            self.apply_all()
            self.shortcuts_changed.emit()
