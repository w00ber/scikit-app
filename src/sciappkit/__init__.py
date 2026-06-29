"""sciappkit — a framework for building canvas / matplotlib GUIs for science.

The top-level package is intentionally lightweight: importing ``sciappkit``
does **not** pull in PySide6 or matplotlib. Import the specific submodule you
need (e.g. ``from sciappkit.canvas import grid``) so that GUI/runtime
dependencies are only loaded when actually used.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
