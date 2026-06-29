"""QGraphicsScene exporter (SVG / PNG / PDF + clipboard).

Lifted and generalized from Diagrammer's ``io/exporter.py``. The only
Diagrammer coupling removed is ``app_settings.export_scale`` (now a
constructor argument) — the render helpers already touch nothing but
``QGraphicsScene``. Selection highlights / handles / ports are
temporarily suppressed around every render so exports show a clean
presentation view; the port-hiding hooks are guarded by ``hasattr`` so
they're harmless for scenes that have no ports.

Clipboard copies route through the lifted
:func:`sciappkit.export.clipboard.copy_to_clipboard` cascade.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QGraphicsScene

from .clipboard import copy_to_clipboard as _copy_bytes_to_clipboard

logger = logging.getLogger(__name__)

# Cap export images so a runaway DPI/scale can't exhaust memory.
_MAX_MEGAPIXELS = 100


class SceneExporter:
    """Export a ``QGraphicsScene``.

    Implements the :class:`sciappkit.export.base.Exporter` protocol where
    ``target`` is a ``QGraphicsScene``. ``copy_to_clipboard`` copies the
    whole scene; :meth:`copy_selection_to_clipboard` copies the current
    selection.
    """

    def __init__(self, export_scale: float = 1.0) -> None:
        self.export_scale = export_scale

    # -- file exports -------------------------------------------------------

    def export_svg(self, target: QGraphicsScene, path: str, *, margin: float = 20.0) -> None:
        from PySide6.QtSvg import QSvgGenerator

        source_rect = _items_rect_with_margin(target, margin)
        out_w = source_rect.width() * self.export_scale
        out_h = source_rect.height() * self.export_scale

        generator = QSvgGenerator()
        generator.setFileName(path)
        generator.setSize(QSize(int(out_w), int(out_h)))
        generator.setViewBox(QRectF(0, 0, out_w, out_h))

        selected = target.selectedItems()
        _clear_selection_visuals(target)
        try:
            painter = QPainter()
            painter.begin(generator)
            target.render(painter, QRectF(0, 0, out_w, out_h), source_rect)
            painter.end()
        finally:
            _restore_selection_visuals(target, selected)

    def export_png(self, target: QGraphicsScene, path: str, *, dpi: int = 300, margin: float = 20.0) -> None:
        selected = target.selectedItems()
        _clear_selection_visuals(target)
        try:
            image = render_scene_to_qimage(
                target, dpi=dpi, margin=margin,
                background=QColor(Qt.GlobalColor.white),
                export_scale=self.export_scale,
            )
            image.save(path)
        finally:
            _restore_selection_visuals(target, selected)

    def export_pdf(self, target: QGraphicsScene, path: str, *, margin: float = 20.0) -> None:
        from PySide6.QtCore import QMarginsF, QSizeF
        from PySide6.QtGui import QPageLayout, QPageSize
        from PySide6.QtPrintSupport import QPrinter

        source_rect = _items_rect_with_margin(target, margin)
        scaled_size = QSizeF(
            source_rect.width() * self.export_scale,
            source_rect.height() * self.export_scale,
        )

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(path)
        page_size = QPageSize(scaled_size, QPageSize.Unit.Point)
        page_layout = QPageLayout(
            page_size, QPageLayout.Orientation.Portrait, QMarginsF(0, 0, 0, 0)
        )
        printer.setPageLayout(page_layout)

        selected = target.selectedItems()
        _clear_selection_visuals(target)
        try:
            painter = QPainter()
            painter.begin(printer)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            printer_rect = printer.pageRect(QPrinter.Unit.DevicePixel)
            target.render(painter, QRectF(printer_rect), source_rect)
            painter.end()
        finally:
            _restore_selection_visuals(target, selected)

    # -- clipboard ----------------------------------------------------------

    def copy_to_clipboard(self, target: QGraphicsScene, *, dpi: int = 300, margin: float = 5.0) -> bool:
        """Copy the whole scene to the clipboard as PDF + PNG."""
        return self._copy(target, _items_rect_with_margin(target, margin), dpi)

    def copy_selection_to_clipboard(self, target: QGraphicsScene, *, dpi: int = 300, margin: float = 5.0) -> bool:
        """Copy the current selection (or the whole scene if none) to the clipboard."""
        return self._copy(target, _selection_rect_with_margin(target, margin), dpi)

    def _copy(self, target: QGraphicsScene, source_rect: QRectF, dpi: int) -> bool:
        if source_rect.isNull() or source_rect.isEmpty():
            return False
        selected = target.selectedItems()
        _clear_selection_visuals(target)
        try:
            pdf_data = _render_pdf_bytes(target, source_rect, self.export_scale)
            png_data = _render_png_bytes(target, source_rect, dpi, self.export_scale)
        finally:
            _restore_selection_visuals(target, selected)
        return _copy_bytes_to_clipboard(pdf_data, png_data)


# ----------------------------------------------------------------------
# Rect helpers
# ----------------------------------------------------------------------

def _items_rect_with_margin(scene: QGraphicsScene, margin: float) -> QRectF:
    """Bounding rect of all items, expanded by *margin* (with empty fallback)."""
    rect = scene.itemsBoundingRect()
    if rect.isNull() or rect.isEmpty():
        rect = QRectF(-50, -50, 100, 100)
    return rect.adjusted(-margin, -margin, margin, margin)


def _selection_rect_with_margin(scene: QGraphicsScene, margin: float) -> QRectF:
    """United bounding rect of selected items (falls back to all items)."""
    selected = scene.selectedItems()
    if not selected:
        return _items_rect_with_margin(scene, margin)
    rect = QRectF()
    for item in selected:
        rect = rect.united(item.sceneBoundingRect())
    if rect.isNull() or rect.isEmpty():
        return _items_rect_with_margin(scene, margin)
    return rect.adjusted(-margin, -margin, margin, margin)


# ----------------------------------------------------------------------
# Selection-visual suppression (generic; port hooks guarded by hasattr)
# ----------------------------------------------------------------------

def _clear_selection_visuals(scene: QGraphicsScene) -> None:
    for item in scene.selectedItems():
        item.setSelected(False)
        if hasattr(item, "_ports"):
            for port in item._ports:
                if not getattr(port, "is_alignment_selected", False):
                    port.setVisible(False)


def _restore_selection_visuals(scene: QGraphicsScene, items: list) -> None:
    for item in items:
        item.setSelected(True)
        if hasattr(item, "_update_port_visibility"):
            item._update_port_visibility()


# ----------------------------------------------------------------------
# Rendering helpers
# ----------------------------------------------------------------------

def _cap_megapixels(pixel_w: int, pixel_h: int) -> tuple[int, int]:
    megapixels = pixel_w * pixel_h / 1_000_000
    if megapixels > _MAX_MEGAPIXELS:
        logger.warning(
            "Export image would be %.0f MP (%d x %d px) — capping to avoid "
            "excessive memory usage. Reduce DPI or export scale.",
            megapixels, pixel_w, pixel_h,
        )
        shrink = (_MAX_MEGAPIXELS * 1_000_000 / (pixel_w * pixel_h)) ** 0.5
        pixel_w = max(1, int(pixel_w * shrink))
        pixel_h = max(1, int(pixel_h * shrink))
    return pixel_w, pixel_h


def render_scene_to_qimage(
    scene: QGraphicsScene,
    dpi: int = 96,
    margin: float = 10.0,
    background: QColor | None = None,
    export_scale: float = 1.0,
) -> QImage:
    """Render *scene* to a QImage at the given DPI.

    Scene coords are treated as nominally 96 dpi, so *dpi* of 192 produces
    a 2x image. *export_scale* scales the output relative to scene size.
    If *background* is None the image is transparent. Also used for
    thumbnail/preview rendering.
    """
    source_rect = _items_rect_with_margin(scene, margin)
    scale = dpi / 96.0 * export_scale
    pixel_w, pixel_h = _cap_megapixels(
        max(1, int(source_rect.width() * scale)),
        max(1, int(source_rect.height() * scale)),
    )

    image = QImage(QSize(pixel_w, pixel_h), QImage.Format.Format_ARGB32_Premultiplied)
    image.setDotsPerMeterX(int(dpi / 0.0254))
    image.setDotsPerMeterY(int(dpi / 0.0254))
    image.fill(background if background is not None else Qt.GlobalColor.transparent)

    painter = QPainter()
    painter.begin(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    scene.render(painter, QRectF(0, 0, pixel_w, pixel_h), source_rect)
    painter.end()
    return image


def _render_png_bytes(scene: QGraphicsScene, source_rect: QRectF, dpi: int, export_scale: float = 1.0) -> bytes | None:
    from PySide6.QtCore import QBuffer, QIODevice

    scale = dpi / 96.0 * export_scale
    pixel_w, pixel_h = _cap_megapixels(
        max(1, int(source_rect.width() * scale)),
        max(1, int(source_rect.height() * scale)),
    )

    image = QImage(QSize(pixel_w, pixel_h), QImage.Format.Format_ARGB32_Premultiplied)
    image.setDotsPerMeterX(int(dpi / 0.0254))
    image.setDotsPerMeterY(int(dpi / 0.0254))
    image.fill(Qt.GlobalColor.transparent)

    painter = QPainter()
    painter.begin(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    scene.render(painter, QRectF(0, 0, pixel_w, pixel_h), source_rect)
    painter.end()

    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buf, "PNG")
    return bytes(buf.data())


def _render_pdf_bytes(scene: QGraphicsScene, source_rect: QRectF, export_scale: float = 1.0) -> bytes | None:
    try:
        from PySide6.QtCore import QMarginsF, QSizeF
        from PySide6.QtGui import QPageLayout, QPageSize
        from PySide6.QtPrintSupport import QPrinter
    except ImportError:
        return None

    import os
    import tempfile

    fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    try:
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(tmp_path)
        scaled_size = QSizeF(
            source_rect.width() * export_scale,
            source_rect.height() * export_scale,
        )
        page_size = QPageSize(scaled_size, QPageSize.Unit.Point)
        page_layout = QPageLayout(
            page_size, QPageLayout.Orientation.Portrait, QMarginsF(0, 0, 0, 0)
        )
        printer.setPageLayout(page_layout)

        painter = QPainter()
        painter.begin(printer)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        printer_rect = printer.pageRect(QPrinter.Unit.DevicePixel)
        scene.render(painter, QRectF(printer_rect), source_rect)
        painter.end()

        with open(tmp_path, "rb") as f:
            return f.read()
    except Exception:
        logger.debug("Failed to render PDF bytes", exc_info=True)
        return None
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
