"""Factory-defaults loader.

Lifted from Diagrammer's ``defaults.py`` and generalized for the
framework. Reads a ``defaults.yaml`` file that defines an application's
original (factory) default values — the baseline a Settings dialog's
"Reset to Original Defaults" button restores to.

By default it reads the framework-level ``defaults.yaml`` shipped beside
this module. Applications point it at their own file once at startup::

    from sciappkit.settings import defaults
    defaults.set_defaults_path("/path/to/my_app/defaults.yaml")
    spacing = defaults.get("grid", "spacing", 20.0)

If PyYAML is unavailable, a minimal built-in parser handles the
flat ``section: / key: value`` structure these files use.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Default to the framework-level defaults shipped beside this module.
_DEFAULTS_PATH: Path = Path(__file__).parent / "defaults.yaml"
_CACHE: dict | None = None


def set_defaults_path(path: str | Path) -> None:
    """Point the loader at an application-specific ``defaults.yaml``.

    Clears the cache so the next lookup reads the new file.
    """
    global _DEFAULTS_PATH, _CACHE
    _DEFAULTS_PATH = Path(path)
    _CACHE = None


def reload() -> dict:
    """Discard the cache and reload the defaults file from disk."""
    global _CACHE
    _CACHE = None
    return _load()


def _load() -> dict:
    global _CACHE
    if _CACHE is not None:
        return _CACHE

    try:
        import yaml
        _CACHE = yaml.safe_load(_DEFAULTS_PATH.read_text(encoding="utf-8")) or {}
    except ImportError:
        # Fallback: simple YAML-subset parser for flat key-value pairs
        _CACHE = _parse_simple_yaml(_DEFAULTS_PATH)
    except (OSError, ValueError) as exc:
        logger.debug("Failed to load defaults file %s: %s", _DEFAULTS_PATH, exc)
        _CACHE = {}
    return _CACHE


def _parse_simple_yaml(path: Path) -> dict:
    """Minimal YAML parser that handles our nested key: value structure."""
    result: dict = {}
    current_section: dict | None = None
    section_name = ""

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.debug("Failed to read defaults file %s: %s", path, exc)
        return result

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Top-level section (no leading whitespace)
        if not line[0].isspace() and stripped.endswith(":"):
            section_name = stripped[:-1]
            current_section = {}
            result[section_name] = current_section
            continue

        # Key-value within a section
        if current_section is not None and ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip()
            # Strip inline comments
            if "#" in val:
                val = val[:val.index("#")].strip()
            # Strip quotes
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            elif val.startswith("'") and val.endswith("'"):
                val = val[1:-1]
            # Type conversion
            if val.lower() == "true":
                val = True
            elif val.lower() == "false":
                val = False
            else:
                try:
                    val = float(val)
                    if val == int(val):
                        val = int(val)
                except (ValueError, OverflowError):
                    pass
            current_section[key] = val

    return result


def get(section: str, key: str, fallback: object = None) -> object:
    """Look up a factory default value."""
    data = _load()
    sec = data.get(section, {})
    return sec.get(key, fallback)


def get_section(section: str) -> dict:
    """Return all defaults for a section."""
    return dict(_load().get(section, {}))


def all_defaults() -> dict:
    """Return the entire defaults dict."""
    return dict(_load())
