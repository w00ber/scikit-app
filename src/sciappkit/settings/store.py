"""Typed, schema-driven settings store with JSON persistence.

Normalizes the two source dialects: Diagrammer's typed ``AppSettings``
(discoverable, but every field is hand-listed three times — in reset, in
save, and in load) and graphulator's ``SettingsManager`` (DRY, but
untyped module-global mutation).

The blend is **schema-driven**: each field is declared once as a
:class:`Setting`; save / load / reset are derived by walking the schema,
so adding a field means editing one place. Values are reached by
attribute (``store.snap_to_grid``) for discoverability, persisted to
``~/.<app_name>/settings.json``, and factory defaults come from a YAML
defaults loader (see :mod:`sciappkit.settings.defaults`).

Non-JSON-native types round-trip through a :class:`Codec` (e.g.
:class:`QColorCodec`, :class:`SetCodec`), keeping the core
Qt-agnostic — importing this module does not require PySide6.
"""

from __future__ import annotations

import copy
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Protocol, Sequence, runtime_checkable

from . import defaults as _defaults_module

logger = logging.getLogger(__name__)


@runtime_checkable
class Codec(Protocol):
    """Serialize a runtime value to/from a JSON-native form."""

    def encode(self, value: Any) -> Any:
        """Return a JSON-serializable representation of *value*."""
        ...

    def decode(self, raw: Any) -> Any:
        """Return the runtime value reconstructed from *raw*."""
        ...


@runtime_checkable
class DefaultsLoader(Protocol):
    """The lookup surface a defaults source must provide.

    Matches :mod:`sciappkit.settings.defaults` (``get`` / ``get_section`` /
    ``all_defaults``).
    """

    def get(self, section: str, key: str, fallback: Any = None) -> Any: ...


@dataclass(frozen=True)
class Setting:
    """Declarative description of a single setting.

    The factory default is ``default``. If ``section`` and ``key`` are
    given, that value is looked up in the defaults loader at reset time and
    overrides ``default`` (so the shipped YAML is the single source of
    truth); ``default`` then acts as the hard-coded fallback. A ``codec``
    handles non-JSON-native runtime types.
    """

    name: str
    default: Any = None
    section: str | None = None
    key: str | None = None
    codec: Codec | None = None
    # Mutable defaults (set/list/dict) are deep-copied per instance so the
    # schema's template object is never shared or mutated.
    mutable: bool = False


# --------------------------------------------------------------------------
# Built-in codecs
# --------------------------------------------------------------------------

class SetCodec:
    """Encode a ``set`` as a sorted list and back."""

    def encode(self, value: Any) -> Any:
        return sorted(value)

    def decode(self, raw: Any) -> Any:
        return set(raw or [])


class QColorCodec:
    """Encode a ``QColor`` as an ``#AARRGGBB`` hex string and back.

    PySide6 is imported lazily so this module stays importable without Qt;
    only constructing/using the codec touches QtGui.
    """

    def encode(self, value: Any) -> Any:
        from PySide6.QtGui import QColor

        color = value if isinstance(value, QColor) else QColor(value)
        return color.name(QColor.NameFormat.HexArgb)

    def decode(self, raw: Any) -> Any:
        from PySide6.QtGui import QColor

        return QColor(raw)


# --------------------------------------------------------------------------
# Store
# --------------------------------------------------------------------------

# Names the store sets on itself directly (never treated as settings fields).
_INTERNAL = frozenset(
    {"_schema", "_values", "_loader", "_app_name", "_path", "_is_first_launch"}
)


class SettingsStore:
    """A typed settings object with schema-driven JSON persistence.

    Example::

        SCHEMA = [
            Setting("theme", "system", section="theme", key="mode"),
            Setting("grid_spacing", 20.0, section="grid", key="spacing"),
            Setting("hidden_libraries", set(), codec=SetCodec(), mutable=True),
        ]
        store = SettingsStore("myapp", SCHEMA)
        store.theme            # -> "system"
        store.grid_spacing = 10.0
        store.save()
    """

    def __init__(
        self,
        app_name: str,
        schema: Sequence[Setting],
        defaults: DefaultsLoader | None = None,
        *,
        settings_dir: Path | None = None,
        autoload: bool = True,
    ) -> None:
        object.__setattr__(self, "_app_name", app_name)
        object.__setattr__(self, "_schema", {s.name: s for s in schema})
        object.__setattr__(self, "_values", {})
        object.__setattr__(self, "_loader", defaults or _defaults_module)
        directory = Path(settings_dir) if settings_dir is not None else Path.home() / f".{app_name}"
        path = directory / "settings.json"
        object.__setattr__(self, "_path", path)
        object.__setattr__(self, "_is_first_launch", not path.exists())

        self.reset_all()
        if autoload:
            self.load()

    # -- attribute access ---------------------------------------------------

    def __getattr__(self, name: str) -> Any:
        # Only called when normal attribute lookup fails.
        schema = self.__dict__.get("_schema")
        if schema is not None and name in schema:
            return self.__dict__["_values"][name]
        raise AttributeError(name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in _INTERNAL:
            object.__setattr__(self, name, value)
            return
        schema = self.__dict__.get("_schema")
        if schema is not None and name in schema:
            self._values[name] = value
        else:
            object.__setattr__(self, name, value)

    # -- introspection ------------------------------------------------------

    @property
    def app_name(self) -> str:
        return self._app_name

    @property
    def path(self) -> Path:
        """Where settings are persisted (``~/.<app_name>/settings.json``)."""
        return self._path

    @property
    def is_first_launch(self) -> bool:
        """True if no settings file existed when the store was constructed."""
        return self._is_first_launch

    def fields(self) -> list[Setting]:
        return list(self._schema.values())

    def field_names(self) -> list[str]:
        return list(self._schema)

    def get(self, name: str) -> Any:
        return self._values[name]

    def set(self, name: str, value: Any) -> None:
        if name not in self._schema:
            raise KeyError(name)
        self._values[name] = value

    def update(self, **kwargs: Any) -> None:
        """Batch-assign several settings (e.g. a dialog's 'Apply')."""
        for name, value in kwargs.items():
            self.set(name, value)

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-native snapshot of every setting."""
        return {name: self._encode(self._schema[name], val) for name, val in self._values.items()}

    # -- reset --------------------------------------------------------------

    def _factory_value(self, setting: Setting) -> Any:
        value = setting.default
        if setting.section and setting.key:
            raw = self._loader.get(setting.section, setting.key, None)
            if raw is not None:
                value = setting.codec.decode(raw) if setting.codec else raw
        if setting.mutable:
            return copy.deepcopy(value)
        return value

    def reset_all(self) -> None:
        """Reset every field to its factory default."""
        for setting in self._schema.values():
            self._values[setting.name] = self._factory_value(setting)

    def reset_field(self, name: str) -> None:
        self._values[name] = self._factory_value(self._schema[name])

    def reset_section(self, section: str) -> None:
        for setting in self._schema.values():
            if setting.section == section:
                self._values[setting.name] = self._factory_value(setting)

    # -- persistence --------------------------------------------------------

    @staticmethod
    def _encode(setting: Setting, value: Any) -> Any:
        return setting.codec.encode(value) if setting.codec else value

    def save(self) -> None:
        """Write all settings to :attr:`path` as JSON (best effort)."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(self.as_dict(), indent=2), encoding="utf-8")
        except OSError as exc:
            logger.debug("Failed to save settings to %s: %s", self._path, exc)

    def load(self) -> None:
        """Load settings from :attr:`path`, keeping defaults for missing keys.

        Unknown keys are ignored and per-field decode failures fall back to
        the current (default) value, so a partial or slightly stale file
        never breaks startup.
        """
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return
        except (OSError, ValueError) as exc:
            logger.debug("Failed to load settings from %s: %s", self._path, exc)
            return
        if not isinstance(data, dict):
            return

        for name, setting in self._schema.items():
            if name not in data:
                continue
            raw = data[name]
            try:
                self._values[name] = setting.codec.decode(raw) if setting.codec else raw
            except Exception:
                logger.debug("Failed to decode setting %r; keeping default", name, exc_info=True)


def build_schema(*settings: Setting | Iterable[Setting]) -> list[Setting]:
    """Flatten ``Setting`` objects and iterables into a single schema list."""
    out: list[Setting] = []
    for item in settings:
        if isinstance(item, Setting):
            out.append(item)
        else:
            out.extend(item)
    return out


# Re-export so ``from sciappkit.settings.store import field`` users aren't
# surprised; ``field`` is occasionally handy when composing dataclasses.
__all__ = [
    "Codec",
    "DefaultsLoader",
    "Setting",
    "SetCodec",
    "QColorCodec",
    "SettingsStore",
    "build_schema",
    "field",
]
