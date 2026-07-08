"""Matplotlib figure exporter (SVG / PNG / PDF + clipboard).

The file-export methods are thin ``Figure.savefig`` wrappers (the pattern
both source apps used). ``copy_to_clipboard`` is net-new: it renders the
figure to PDF + PNG bytes and routes them through the lifted
:func:`sciappkit.export.clipboard.copy_to_clipboard` cascade, giving
matplotlib figures the same editable-vector clipboard behavior as scene
exports.
"""

from __future__ import annotations

import io
import logging

from .clipboard import copy_to_clipboard as _copy_bytes_to_clipboard

logger = logging.getLogger(__name__)


class MplExporter:
    """Export a matplotlib ``Figure``.

    Implements the :class:`sciappkit.export.base.Exporter` protocol where
    ``target`` is a ``matplotlib.figure.Figure``.
    """

    def __init__(self, dpi: int = 300, bbox_inches: str | None = "tight") -> None:
        self.dpi = dpi
        self.bbox_inches = bbox_inches

    # -- file exports -------------------------------------------------------

    def export_png(self, target, path: str) -> None:
        target.savefig(path, dpi=self.dpi, bbox_inches=self.bbox_inches)

    def export_svg(self, target, path: str) -> None:
        target.savefig(path, format="svg", bbox_inches=self.bbox_inches)

    def export_pdf(self, target, path: str, *, embed_fonts: bool = True) -> None:
        import matplotlib

        # fonttype 42 embeds TrueType fonts so text stays selectable and
        # renders correctly in other viewers.
        if embed_fonts:
            old = matplotlib.rcParams.get("pdf.fonttype")
            matplotlib.rcParams["pdf.fonttype"] = 42
            try:
                target.savefig(path, format="pdf", dpi=self.dpi, bbox_inches=self.bbox_inches)
            finally:
                matplotlib.rcParams["pdf.fonttype"] = old
        else:
            target.savefig(path, format="pdf", dpi=self.dpi, bbox_inches=self.bbox_inches)

    # -- clipboard ----------------------------------------------------------

    def _render_bytes(self, target, fmt: str) -> bytes:
        buf = io.BytesIO()
        target.savefig(buf, format=fmt, dpi=self.dpi, bbox_inches=self.bbox_inches)
        return buf.getvalue()

    def _render_svg_bytes(self, target) -> bytes:
        """Render *target* to self-contained SVG bytes (glyphs as outlines).

        ``svg.fonttype = "path"`` converts text to vector outlines so the
        SVG renders identically anywhere without depending on the viewer
        having the figure's fonts installed.
        """
        import matplotlib

        old = matplotlib.rcParams.get("svg.fonttype")
        matplotlib.rcParams["svg.fonttype"] = "path"
        try:
            return self._render_bytes(target, "svg")
        finally:
            matplotlib.rcParams["svg.fonttype"] = old

    def copy_to_clipboard(self, target) -> bool:
        """Copy *target* to the clipboard as PDF + SVG (vector) + PNG (raster)."""
        try:
            pdf = self._render_bytes(target, "pdf")
            svg = self._render_svg_bytes(target)
            png = self._render_bytes(target, "png")
        except Exception:
            logger.debug("Failed to render figure for clipboard", exc_info=True)
            return False
        return _copy_bytes_to_clipboard(pdf, png, svg)
