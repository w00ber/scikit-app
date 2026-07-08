"""Robust, platform-aware clipboard writer for vector + raster exports.

Lifted from Diagrammer's ``io/exporter.py``. Given rendered ``pdf_data``
and/or ``png_data`` bytes, :func:`copy_to_clipboard` places them on the
system clipboard so that downstream apps (Illustrator, Keynote,
PowerPoint, …) receive editable vector data where possible and a
universal raster fallback otherwise.

The macOS path is the interesting bit: it cascades through three
strategies so an editable PDF lands on the ``NSPasteboard`` with the
correct UTIs regardless of how Python was installed:

  1. **ctypes** — call ``libobjc.dylib`` directly. Always available on
     macOS, needs no third-party packages.
  2. **PyObjC** — used if ``AppKit`` is importable in this interpreter.
  3. **subprocess** — shell out to a system Python that has PyObjC.

On Linux / Windows (or if every macOS strategy fails) it falls back to
Qt's ``QMimeData``. The strategy actually used is recorded in
:data:`last_clipboard_method` for diagnostics.

This module renders nothing itself — the caller supplies the bytes (e.g.
via ``QPrinter`` for PDF and ``QImage`` for PNG) so the cascade stays
app-agnostic.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

logger = logging.getLogger(__name__)

__all__ = ["copy_to_clipboard", "last_clipboard_method"]


# Clipboard method used for the most recent copy (for diagnostics).
# One of: "native (ctypes)", "native (PyObjC)", "subprocess (...)", "qt".
last_clipboard_method: str = ""


def copy_to_clipboard(
    pdf_data: bytes | None,
    png_data: bytes | None,
    svg_data: bytes | None = None,
) -> bool:
    """Place *pdf_data*, *png_data* and/or *svg_data* on the clipboard.

    On macOS, uses the Objective-C runtime via ctypes to write directly
    to NSPasteboard with the correct UTIs (``com.adobe.pdf``,
    ``public.svg-image``, ``public.png``).  This requires no third-party
    packages — only ``libobjc.dylib`` which ships with every macOS install.

    On other platforms falls back to Qt's QMimeData (MIME types
    ``application/pdf``, ``image/svg+xml`` and the image data for PNG).

    *svg_data* is optional so existing ``copy_to_clipboard(pdf, png)``
    callers keep working unchanged. Vector flavours (PDF, SVG) are
    declared ahead of the raster PNG so vector-preferring targets
    (Illustrator, Keynote, PowerPoint) pick them up.

    Sets the module-level :data:`last_clipboard_method` to indicate which
    path was taken. Returns ``True`` if something was written.
    """
    global last_clipboard_method
    import sys

    if sys.platform == "darwin" and (pdf_data or svg_data):
        # 1) ctypes — always available, no dependencies
        try:
            _set_clipboard_macos_ctypes(pdf_data, png_data, svg_data)
            last_clipboard_method = "native (ctypes)"
            return True
        except Exception:
            logger.debug("ctypes clipboard method failed, trying next", exc_info=True)

        # 2) PyObjC — if installed in this interpreter
        try:
            _set_clipboard_macos_pyobjc(pdf_data, png_data, svg_data)
            last_clipboard_method = "native (PyObjC)"
            return True
        except Exception:
            logger.debug("PyObjC clipboard method failed, trying next", exc_info=True)

        # 3) subprocess — try system Python which usually has PyObjC
        ok, method = _set_clipboard_macos_subprocess(pdf_data, png_data, svg_data)
        if ok:
            last_clipboard_method = method
            return True

    last_clipboard_method = "qt"
    return _set_clipboard_qt(pdf_data, png_data, svg_data)


# -- macOS: ctypes (no dependencies) ------------------------------------

def _set_clipboard_macos_ctypes(
    pdf_data: bytes | None, png_data: bytes | None, svg_data: bytes | None = None,
) -> None:
    """Write PDF + SVG + PNG to the macOS pasteboard via the ObjC runtime.

    Uses ctypes to call ``libobjc.dylib`` directly — works on every
    macOS install without any third-party packages.  Raises on failure.
    """
    import ctypes
    import ctypes.util

    # Load the Objective-C runtime
    objc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("objc"))

    # Configure objc_msgSend signatures
    objc.objc_getClass.restype = ctypes.c_void_p
    objc.objc_getClass.argtypes = [ctypes.c_char_p]
    objc.sel_registerName.restype = ctypes.c_void_p
    objc.sel_registerName.argtypes = [ctypes.c_char_p]

    # Generic messenger — we cast per-call as needed
    msg = objc.objc_msgSend
    msg.restype = ctypes.c_void_p
    msg.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

    def cls(name: str) -> ctypes.c_void_p:
        return objc.objc_getClass(name.encode())

    def sel(name: str) -> ctypes.c_void_p:
        return objc.sel_registerName(name.encode())

    def send(obj, selector, *args):
        return msg(obj, selector, *args)

    # NSData from bytes
    def make_nsdata(raw: bytes) -> ctypes.c_void_p:
        NSData = cls("NSData")
        buf = ctypes.create_string_buffer(raw)
        # +[NSData dataWithBytes:length:]
        fn = ctypes.cast(msg, ctypes.CFUNCTYPE(
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_uint64,
        ))
        return fn(
            NSData, sel("dataWithBytes:length:"),
            buf, len(raw),
        )

    # NSString from Python str
    def make_nsstring(s: str) -> ctypes.c_void_p:
        NSString = cls("NSString")
        encoded = s.encode("utf-8")
        buf = ctypes.create_string_buffer(encoded)
        fn = ctypes.cast(msg, ctypes.CFUNCTYPE(
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_uint64,
        ))
        return fn(
            NSString, sel("stringWithUTF8String:"),
            buf, 0,  # second arg ignored for this selector
        )

    # NSArray from list of ObjC objects
    def make_nsarray(items: list) -> ctypes.c_void_p:
        NSArray = cls("NSArray")
        arr_type = ctypes.c_void_p * len(items)
        c_arr = arr_type(*items)
        fn = ctypes.cast(msg, ctypes.CFUNCTYPE(
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p), ctypes.c_uint64,
        ))
        return fn(
            NSArray, sel("arrayWithObjects:count:"),
            c_arr, len(items),
        )

    # UTI strings — declare vector flavours (PDF, SVG) ahead of the
    # raster PNG so vector-preferring targets pick them up first.
    types = []

    pdf_type = None
    if pdf_data:
        pdf_type = make_nsstring("com.adobe.pdf")
        types.append(pdf_type)

    svg_type = None
    if svg_data:
        svg_type = make_nsstring("public.svg-image")
        types.append(svg_type)

    png_type = None
    if png_data:
        png_type = make_nsstring("public.png")
        types.append(png_type)

    ns_types = make_nsarray(types)

    # Get the general pasteboard
    NSPasteboard = cls("NSPasteboard")
    pb = send(NSPasteboard, sel("generalPasteboard"))
    if not pb:
        raise RuntimeError("Failed to get NSPasteboard")

    # Clear and declare types
    send(pb, sel("clearContents"))

    fn_declare = ctypes.cast(msg, ctypes.CFUNCTYPE(
        ctypes.c_int64, ctypes.c_void_p, ctypes.c_void_p,
        ctypes.c_void_p, ctypes.c_void_p,
    ))
    fn_declare(pb, sel("declareTypes:owner:"), ns_types, None)

    fn_set = ctypes.cast(msg, ctypes.CFUNCTYPE(
        ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p,
        ctypes.c_void_p, ctypes.c_void_p,
    ))

    # Set PDF data
    if pdf_data and pdf_type:
        pdf_nsdata = make_nsdata(pdf_data)
        fn_set(pb, sel("setData:forType:"), pdf_nsdata, pdf_type)

    # Set SVG data
    if svg_data and svg_type:
        svg_nsdata = make_nsdata(svg_data)
        fn_set(pb, sel("setData:forType:"), svg_nsdata, svg_type)

    # Set PNG data
    if png_data and png_type:
        png_nsdata = make_nsdata(png_data)
        fn_set(pb, sel("setData:forType:"), png_nsdata, png_type)


# -- macOS: PyObjC -------------------------------------------------------

def _set_clipboard_macos_pyobjc(
    pdf_data: bytes | None, png_data: bytes | None, svg_data: bytes | None = None,
) -> None:
    """Write PDF + SVG + PNG to the macOS pasteboard via AppKit (PyObjC).

    Raises ImportError if PyObjC is not available. SVG has no
    ``NSPasteboardType*`` constant, so its UTI is passed as a raw string.
    """
    from AppKit import NSPasteboard, NSPasteboardTypePDF, NSPasteboardTypePNG

    svg_uti = "public.svg-image"

    pb = NSPasteboard.generalPasteboard()
    types = []
    if pdf_data:
        types.append(NSPasteboardTypePDF)
    if svg_data:
        types.append(svg_uti)
    if png_data:
        types.append(NSPasteboardTypePNG)

    pb.clearContents()
    pb.declareTypes_owner_(types, None)
    if pdf_data:
        pb.setData_forType_(pdf_data, NSPasteboardTypePDF)
    if svg_data:
        pb.setData_forType_(svg_data, svg_uti)
    if png_data:
        pb.setData_forType_(png_data, NSPasteboardTypePNG)


# -- macOS: subprocess ----------------------------------------------------

def _set_clipboard_macos_subprocess(
    pdf_data: bytes | None, png_data: bytes | None, svg_data: bytes | None = None,
) -> tuple[bool, str]:
    """Fallback: write PDF + SVG + PNG to macOS pasteboard via a subprocess.

    Tries several Python interpreters that may have AppKit available.
    """
    import os
    import shutil
    import subprocess
    import tempfile

    tmp_paths: list[str] = []

    def _write_temp(data: bytes, suffix: str) -> str:
        fd, path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        tmp_paths.append(path)
        with open(path, "wb") as f:
            f.write(bytes(data))
        return path

    try:
        pdf_path = _write_temp(pdf_data, ".pdf") if pdf_data else ""
        svg_path = _write_temp(svg_data, ".svg") if svg_data else ""
        png_path = _write_temp(png_data, ".png") if png_data else ""

        script = _PASTEBOARD_SCRIPT.format(
            pdf_path=pdf_path,
            svg_path=svg_path,
            png_path=png_path,
        )

        candidates = ["/usr/bin/python3"]
        for name in ("python3", "python"):
            found = shutil.which(name)
            if found and found not in candidates:
                candidates.append(found)

        for python in candidates:
            try:
                result = subprocess.run(
                    [python, "-c", script],
                    capture_output=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    return True, f"subprocess ({python})"
            except (OSError, subprocess.SubprocessError) as exc:
                logger.debug("Subprocess clipboard via %s failed: %s", python, exc)
                continue

        return False, ""
    except Exception:
        logger.debug("Subprocess clipboard fallback failed entirely", exc_info=True)
        return False, ""
    finally:
        for path in tmp_paths:
            try:
                os.unlink(path)
            except OSError:
                pass


_PASTEBOARD_SCRIPT = '''\
from AppKit import NSPasteboard, NSPasteboardTypePDF, NSPasteboardTypePNG

pdf_path = {pdf_path!r}
svg_path = {svg_path!r}
png_path = {png_path!r}

# Declare vector flavours (PDF, SVG) ahead of the raster PNG.
pb = NSPasteboard.generalPasteboard()
types = []
if pdf_path:
    types.append(NSPasteboardTypePDF)
if svg_path:
    types.append("public.svg-image")
if png_path:
    types.append(NSPasteboardTypePNG)

pb.clearContents()
pb.declareTypes_owner_(types, None)

if pdf_path:
    with open(pdf_path, "rb") as f:
        pb.setData_forType_(f.read(), NSPasteboardTypePDF)
if svg_path:
    with open(svg_path, "rb") as f:
        pb.setData_forType_(f.read(), "public.svg-image")
if png_path:
    with open(png_path, "rb") as f:
        pb.setData_forType_(f.read(), NSPasteboardTypePNG)
'''


def _set_clipboard_qt(
    pdf_data: bytes | None, png_data: bytes | None, svg_data: bytes | None = None,
) -> bool:
    """Write to clipboard via Qt QMimeData (Linux / Windows fallback)."""
    from PySide6.QtCore import QMimeData

    mime = QMimeData()
    if pdf_data:
        mime.setData("application/pdf", QByteArray(pdf_data))
    if svg_data:
        mime.setData("image/svg+xml", QByteArray(svg_data))
    if png_data:
        image = QImage()
        image.loadFromData(QByteArray(png_data), "PNG")
        if not image.isNull():
            mime.setImageData(image)

    QApplication.clipboard().setMimeData(mime)
    return True
