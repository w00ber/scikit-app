"""The uniform exporter interface.

Both canvas kinds export through the same small surface so a host (e.g.
:class:`sciappkit.app.main_window.SciAppMainWindow`) can drive
Export→SVG/PNG/PDF and Copy-to-clipboard without knowing whether the
active canvas is a matplotlib ``Figure`` or a ``QGraphicsScene``.

``target`` is whatever the canvas controller's ``export_target()``
returns: a ``Figure`` for :class:`~sciappkit.export.mpl_exporter.MplExporter`
or a ``QGraphicsScene`` for
:class:`~sciappkit.export.scene_exporter.SceneExporter`.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Exporter(Protocol):
    """Render an export *target* to a file or the system clipboard."""

    def export_svg(self, target: Any, path: str) -> None: ...

    def export_png(self, target: Any, path: str) -> None: ...

    def export_pdf(self, target: Any, path: str) -> None: ...

    def copy_to_clipboard(self, target: Any) -> bool:
        """Copy *target* to the clipboard; return ``True`` on success."""
        ...
