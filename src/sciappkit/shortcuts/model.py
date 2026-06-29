"""Keyboard shortcut definitions and per-app registry (pure data).

Normalizes the two source dialects: Diagrammer's module-level
``SHORTCUTS`` dict + polymorphic ``Shortcut`` (leans on
``QKeySequence.StandardKey`` for correct per-platform standard actions,
group-form conflict detection) and graphulator's dataclass definitions +
``ShortcutManager`` (signals, input-focus guard).

This module is the data layer: a :class:`Shortcut` description and a
per-app :class:`ShortcutRegistry` (deliberately **not** a global
singleton) that resolves bindings per platform, tracks user overrides,
and computes conflicts. The Qt glue — signals, applying to ``QAction`` /
``QShortcut``, and JSON persistence — lives in
:mod:`sciappkit.shortcuts.manager`.

Only ``QKeySequence`` (QtGui) is needed here for coercion and normalized
comparison.
"""

from __future__ import annotations

import sys
from typing import Iterable, Union

from PySide6.QtGui import QKeySequence

# A binding may be declared in any of these forms; ``StandardKey`` is
# preferred for standard actions (New/Open/Save/…) so Qt picks the right
# per-platform sequence automatically.
BindingValue = Union[QKeySequence.StandardKey, QKeySequence, str, int, None]


def detect_platform() -> str:
    """Return ``"mac"``, ``"win"`` or ``"linux"`` for the current OS."""
    if sys.platform == "darwin":
        return "mac"
    if sys.platform.startswith("win"):
        return "win"
    return "linux"


def to_key_sequence(value: BindingValue) -> QKeySequence:
    """Coerce a polymorphic binding value into a ``QKeySequence``."""
    if value is None or value == "":
        return QKeySequence()
    if isinstance(value, QKeySequence):
        return value
    # StandardKey, str, and int are all accepted by the QKeySequence ctor.
    return QKeySequence(value)


def portable_text(seq: QKeySequence | str | None) -> str:
    """Normalized, platform-independent string form (for storage/compare)."""
    if seq is None:
        return ""
    if isinstance(seq, str):
        seq = QKeySequence(seq)
    return seq.toString(QKeySequence.SequenceFormat.PortableText)


def native_text(seq: QKeySequence | str | None) -> str:
    """Human-facing string form (e.g. ``⌘S`` on macOS)."""
    if seq is None:
        return ""
    if isinstance(seq, str):
        seq = QKeySequence(seq)
    return seq.toString(QKeySequence.SequenceFormat.NativeText)


class Shortcut:
    """A single rebindable action.

    The blended constructor: per-platform keys (``mac`` / ``win`` /
    ``linux``) win over ``default``; values may be a ``StandardKey``,
    ``QKeySequence``, portable string, or int.
    """

    def __init__(
        self,
        action_id: str,
        *,
        default: BindingValue = None,
        mac: BindingValue = None,
        win: BindingValue = None,
        linux: BindingValue = None,
        display_name: str = "",
        category: str = "",
        description: str = "",
        is_single_key: bool = False,
        is_menu_action: bool = False,
    ) -> None:
        self.action_id = action_id
        self.default = default
        self.mac = mac
        self.win = win
        self.linux = linux
        self.display_name = display_name or action_id
        self.category = category
        self.description = description
        # A bare single key (e.g. "r") needs an input-focus guard so it
        # doesn't fire while typing in a text field.
        self.is_single_key = is_single_key
        self.is_menu_action = is_menu_action
        self._user_override: str | None = None  # portable text, or None

    # -- resolution ---------------------------------------------------------

    def _platform_value(self, platform: str) -> BindingValue:
        value = {"mac": self.mac, "win": self.win, "linux": self.linux}.get(platform)
        return value if value is not None else self.default

    def default_sequence(self, platform: str) -> QKeySequence:
        return to_key_sequence(self._platform_value(platform))

    def active_sequence(self, platform: str) -> QKeySequence:
        if self._user_override is not None:
            return QKeySequence(self._user_override)
        return self.default_sequence(platform)

    def display_text(self, platform: str) -> str:
        return native_text(self.active_sequence(platform))

    @property
    def is_overridden(self) -> bool:
        return self._user_override is not None

    # -- override management ------------------------------------------------

    def set_override(self, seq: QKeySequence | str | None, platform: str) -> None:
        """Set (or clear) the user override.

        An override equal to the platform default collapses to "no
        override" so defaults can evolve without stale entries.
        """
        portable = portable_text(seq) if seq not in (None, "") else ""
        if portable == "":
            self._user_override = None
            return
        if portable == portable_text(self.default_sequence(platform)):
            self._user_override = None
        else:
            self._user_override = portable

    def reset(self) -> None:
        self._user_override = None


class ShortcutRegistry:
    """A per-app collection of :class:`Shortcut` definitions.

    Not a global singleton — each app builds and owns one. Resolves
    bindings for :attr:`platform`, tracks overrides, and computes
    conflicts. Serializes only non-default overrides.
    """

    def __init__(self, platform: str | None = None) -> None:
        self._platform = platform or detect_platform()
        self._shortcuts: dict[str, Shortcut] = {}

    @property
    def platform(self) -> str:
        return self._platform

    # -- population ---------------------------------------------------------

    def register(self, shortcut: Shortcut) -> Shortcut:
        self._shortcuts[shortcut.action_id] = shortcut
        return shortcut

    def register_many(self, shortcuts: Iterable[Shortcut]) -> None:
        for sc in shortcuts:
            self.register(sc)

    # -- lookup -------------------------------------------------------------

    def get(self, action_id: str) -> Shortcut | None:
        return self._shortcuts.get(action_id)

    def all(self) -> list[Shortcut]:
        return sorted(self._shortcuts.values(), key=lambda s: (s.category, s.action_id))

    def by_category(self) -> dict[str, list[Shortcut]]:
        out: dict[str, list[Shortcut]] = {}
        for sc in self.all():
            out.setdefault(sc.category, []).append(sc)
        return out

    def action_ids(self) -> list[str]:
        return list(self._shortcuts)

    # -- resolution ---------------------------------------------------------

    def sequence(self, action_id: str) -> QKeySequence:
        sc = self._shortcuts.get(action_id)
        return sc.active_sequence(self._platform) if sc else QKeySequence()

    def default_sequence(self, action_id: str) -> QKeySequence:
        sc = self._shortcuts.get(action_id)
        return sc.default_sequence(self._platform) if sc else QKeySequence()

    def display_text(self, action_id: str) -> str:
        sc = self._shortcuts.get(action_id)
        return sc.display_text(self._platform) if sc else ""

    # -- overrides ----------------------------------------------------------

    def set_override(self, action_id: str, seq: QKeySequence | str | None) -> None:
        sc = self._shortcuts.get(action_id)
        if sc is not None:
            sc.set_override(seq, self._platform)

    def reset(self, action_id: str) -> None:
        sc = self._shortcuts.get(action_id)
        if sc is not None:
            sc.reset()

    def reset_all(self) -> None:
        for sc in self._shortcuts.values():
            sc.reset()

    def is_modified(self, action_id: str) -> bool:
        sc = self._shortcuts.get(action_id)
        return bool(sc and sc.is_overridden)

    def has_custom(self) -> bool:
        return any(sc.is_overridden for sc in self._shortcuts.values())

    # -- conflicts ----------------------------------------------------------

    def _active_portables(self, proposed: dict[str, str] | None = None) -> dict[str, str]:
        """Map action_id -> active portable string, applying *proposed*."""
        result: dict[str, str] = {}
        for action_id, sc in self._shortcuts.items():
            if proposed is not None and action_id in proposed:
                result[action_id] = portable_text(proposed[action_id])
            else:
                result[action_id] = portable_text(sc.active_sequence(self._platform))
        return result

    def conflicts(self, proposed: dict[str, str] | None = None) -> dict[str, list[str]]:
        """Return ``{portable_key: [action_id, …]}`` for any collisions.

        Only groups of two or more sharing a non-empty sequence are
        returned. *proposed* overlays in-flight edits (action_id ->
        portable string) so a settings UI can validate before applying.
        """
        groups: dict[str, list[str]] = {}
        for action_id, portable in self._active_portables(proposed).items():
            if portable:
                groups.setdefault(portable, []).append(action_id)
        return {key: sorted(ids) for key, ids in groups.items() if len(ids) > 1}

    def conflict_for(self, seq: QKeySequence | str, exclude: str | None = None) -> str | None:
        """Return the first action already bound to *seq* (or ``None``)."""
        target = portable_text(seq)
        if not target:
            return None
        for action_id, portable in self._active_portables().items():
            if action_id != exclude and portable == target:
                return action_id
        return None

    # -- (de)serialization (non-default overrides only) ---------------------

    def export_overrides(self) -> dict[str, str]:
        return {
            action_id: sc._user_override
            for action_id, sc in self._shortcuts.items()
            if sc._user_override is not None
        }

    def import_overrides(self, data: dict[str, str]) -> None:
        for action_id, portable in data.items():
            sc = self._shortcuts.get(action_id)
            if sc is not None:
                sc.set_override(portable, self._platform)
