"""Project scaffolding — generate a runnable sciappkit app skeleton.

``create_app`` emits a small, runnable application wired to the framework,
choosing one of three canvas styles (``scene`` / ``mpl`` / ``both``). It's
a self-contained generator (no external template engine), exposed on the
command line as ``create-sciapp``.
"""

from __future__ import annotations

from .generator import CANVAS_STYLES, create_app

__all__ = ["create_app", "CANVAS_STYLES"]
