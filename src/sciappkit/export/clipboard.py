"""Robust, platform-aware clipboard writer for vector + raster exports.

Lifted from Diagrammer's ``io/exporter.py``. Given rendered ``pdf_data``
and/or ``png_data`` bytes, :func:`set_clipboard` places them on the system
clipboard so that downstream apps (Illustrator, Keynote, PowerPoint, …)
receive editable vector data where possible and a universal raster
fallback otherwise.

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


# Clipboard method used for the most recent copy (for diagnostics).
# One of: "native (ctypes)", "native (PyObjC)", "subprocess (...)", "qt".
last_clipboard_method: str = ""


def set_clipboard(pdf_data: bytes | None, png_data: bytes | None) -> bool:
    """Place *pdf_data* and *png_data* on the system clipboard.

    On macOS, uses the Objective-C runtime via ctypes to write directly
    to NSPasteboard with the correct UTIs (``com.adobe.pdf``,
    ``public.png``).  This requires no third-party packages — only
    ``libobjc.dylib`` which ships with every macOS install.

    On other platforms falls back to Qt's QMimeData.

    Sets the module-level :data:`last_clipboard_method` to indicate which
    path was taken. Returns ``True`` if something was written.
    """
    global last_clipboard_method
    import sys

    if sys.platform == "darwin" and pdf_data:
        # 1) ctypes — always available, no dependencies
        try:
            _set_clipboard_macos_ctypes(pdf_data, png_data)
            last_clipboard_method = "native (ctypes)"
            return True
        except Exception:
            logger.debug("ctypes clipboard method failed, trying next", exc_info=True)

        # 2) PyObjC — if installed in this interpreter
        try:
            _set_clipboard_macos_pyobjc(pdf_data, png_data)
            last_clipboard_method = "native (PyObjC)"
            return True
        except Exception:
            logger.debug("PyObjC clipboard method failed, trying next", exc_info=True)

        # 3) subprocess — try system Python which usually has PyObjC
        ok, method = _set_clipboard_macos_subprocess(pdf_data, png_data)
        if ok:
            last_clipboard_method = method
            return True

    last_clipboard_method = "qt"
    return _set_clipboard_qt(pdf_data, png_data)


# -- macOS: ctypes (no dependencies) ------------------------------------

def _set_clipboard_macos_ctypes(
    pdf_data: bytes, png_data: bytes | None,
) -> None:
    """Write PDF + PNG to the macOS pasteboard via the ObjC runtime.

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

    # UTI strings
    pdf_type = make_nsstring("com.adobe.pdf")
    types = [pdf_type]

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

    # Set PDF data
    pdf_nsdata = make_nsdata(pdf_data)
    fn_set = ctypes.cast(msg, ctypes.CFUNCTYPE(
        ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p,
        ctypes.c_void_p, ctypes.c_void_p,
    ))
    fn_set(pb, sel("setData:forType:"), pdf_nsdata, pdf_type)

    # Set PNG data
    if png_data and png_type:
        png_nsdata = make_nsdata(png_data)
        fn_set(pb, sel("setData:forType:"), png_nsdata, png_type)


# -- macOS: PyObjC -------------------------------------------------------

def _set_clipboard_macos_pyobjc(
    pdf_data: bytes, png_data: bytes | None,
) -> None:
    """Write PDF + PNG to the macOS pasteboard via AppKit (PyObjC).

    Raises ImportError if PyObjC is not available.
    """
    from AppKit import NSPasteboard, NSPasteboardTypePDF, NSPasteboardTypePNG

    pb = NSPasteboard.generalPasteboard()
    types = [NSPasteboardTypePDF]
    if png_data:
        types.append(NSPasteboardTypePNG)

    pb.clearContents()
    pb.declareTypes_owner_(types, None)
    pb.setData_forType_(pdf_data, NSPasteboardTypePDF)
    if png_data:
        pb.setData_forType_(png_data, NSPasteboardTypePNG)


# -- macOS: subprocess ----------------------------------------------------

def _set_clipboard_macos_subprocess(
    pdf_data: bytes, png_data: bytes | None,
) -> tuple[bool, str]:
    """Fallback: write PDF to macOS pasteboard via a subprocess.

    Tries several Python interpreters that may have AppKit available.
    """
    import os
    import shutil
    import subprocess
    import tempfile

    fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    png_tmp = None

    try:
        with open(tmp_path, "wb") as f:
            f.write(bytes(pdf_data))

        if png_data:
            fd2, png_tmp = tempfile.mkstemp(suffix=".png")
            os.close(fd2)
            with open(png_tmp, "wb") as f:
                f.write(bytes(png_data))

        script = _PASTEBOARD_SCRIPT.format(
            pdf_path=tmp_path,
            png_path=png_tmp or "",
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
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        if png_tmp:
            try:
                os.unlink(png_tmp)
            except OSError:
                pass


_PASTEBOARD_SCRIPT = '''\
from AppKit import NSPasteboard, NSPasteboardTypePDF, NSPasteboardTypePNG

pdf_path = "{pdf_path}"
png_path = "{png_path}"

with open(pdf_path, "rb") as f:
    pdf_data = f.read()

pb = NSPasteboard.generalPasteboard()
types = [NSPasteboardTypePDF]
if png_path:
    types.append(NSPasteboardTypePNG)

pb.clearContents()
pb.declareTypes_owner_(types, None)
pb.setData_forType_(pdf_data, NSPasteboardTypePDF)

if png_path:
    with open(png_path, "rb") as f:
        png_data = f.read()
    pb.setData_forType_(png_data, NSPasteboardTypePNG)
'''


def _set_clipboard_qt(pdf_data: bytes | None, png_data: bytes | None) -> bool:
    """Write to clipboard via Qt QMimeData (Linux / Windows fallback)."""
    from PySide6.QtCore import QMimeData

    mime = QMimeData()
    if pdf_data:
        mime.setData("application/pdf", QByteArray(pdf_data))
    if png_data:
        image = QImage()
        image.loadFromData(QByteArray(png_data), "PNG")
        if not image.isNull():
            mime.setImageData(image)

    QApplication.clipboard().setMimeData(mime)
    return True
