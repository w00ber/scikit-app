"""The About dialog, and the diagnostics it reports.

Two halves on purpose. :func:`about_info` and :func:`diagnostics_text` are
PURE — no Qt, no window — so what the dialog claims about a build can be
asserted in a test; :class:`AboutDialog` only lays them out.

The point of the dialog is the **diagnostics**, not the credits: a bug
report that names the app version, the Qt build and the geometry/render
stack underneath it is actionable, and one that does not is a conversation.
So the component list is app-supplied (:meth:`SciAppMainWindow.about_components`)
and the whole block copies to the clipboard in one click.
"""

from __future__ import annotations

import platform
import sys
from dataclasses import dataclass, field

__all__ = ["AboutInfo", "about_info", "diagnostics_text", "AboutDialog"]


@dataclass(frozen=True)
class AboutInfo:
    """Everything the dialog shows, resolved from installed metadata."""

    app_name: str
    version: str
    summary: str = ""
    #: SPDX expression when the project declares one ("MIT"), else "".
    license_label: str = ""
    #: Full licence text when the project ships one, else "".
    license_text: str = ""
    #: Display name -> URL, in declaration order.
    urls: dict[str, str] = field(default_factory=dict)
    #: Component -> version, for the diagnostics block.
    components: dict[str, str] = field(default_factory=dict)
    credits: str = ""


def _dist_version(name: str) -> str:
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version(name)
    except PackageNotFoundError:
        return ""


def base_components() -> dict[str, str]:
    """The versions every sciappkit app shares: Python, Qt, the framework.

    An app adds its own stack on top (``about_components``) — this module
    must not import shapely or VTK to find out what an app is built on.
    """
    out = {"Python": platform.python_version()}
    try:
        import PySide6
        from PySide6.QtCore import qVersion

        out["PySide6"] = PySide6.__version__
        out["Qt"] = qVersion()
    except Exception:  # pragma: no cover — Qt is a hard dep in practice
        pass
    kit = _dist_version("sciappkit")
    if kit:
        out["sciappkit"] = kit
    out["Platform"] = f"{platform.system()} {platform.release()} ({platform.machine()})"
    return out


def about_info(
    app_name: str,
    distribution: str | None = None,
    *,
    components: dict[str, str] | None = None,
    credits: str = "",
) -> AboutInfo:
    """Resolve *distribution*'s installed metadata into an :class:`AboutInfo`.

    Missing metadata is never fatal — a source tree with no ``.dist-info``
    still opens the dialog, just with blanks. ``distribution`` defaults to
    the lowercased app name, which is the convention these apps follow.
    """
    dist = distribution or app_name.lower()
    version = _dist_version(dist)
    summary = license_label = license_text = ""
    urls: dict[str, str] = {}
    try:
        from importlib.metadata import metadata

        meta = metadata(dist)
        summary = meta.get("Summary") or ""
        # Two spellings, and a project may use either: License-Expression is
        # the SPDX id, License is free text — which for a `license = {file=}`
        # project is the WHOLE licence, so it is a body, not a label.
        license_label = meta.get("License-Expression") or ""
        raw = meta.get("License") or ""
        if raw and "\n" not in raw.strip() and len(raw) <= 40:
            license_label = license_label or raw.strip()
        elif raw:
            license_text = raw
            # A `license = {file = "LICENSE"}` project has no SPDX id in its
            # metadata, so the label comes off the text's own first line —
            # which for every common licence IS its name ("MIT License").
            first = next((ln.strip() for ln in raw.splitlines() if ln.strip()), "")
            if not license_label and 0 < len(first) <= 60:
                license_label = first
        for entry in meta.get_all("Project-URL") or []:
            name, _, url = entry.partition(",")
            urls[name.strip()] = url.strip()
    except Exception:
        pass

    merged = base_components()
    if version:
        merged = {app_name: version, **merged}
    for key, value in (components or {}).items():
        if value:
            merged[key] = value

    return AboutInfo(
        app_name=app_name,
        version=version,
        summary=summary,
        license_label=license_label,
        license_text=license_text,
        urls=urls,
        components=merged,
        credits=credits,
    )


def diagnostics_text(info: AboutInfo) -> str:
    """The copyable block: one ``name: version`` per line.

    This is what a bug report should carry, so it is plain text and stays
    stable — no decoration, no alignment that depends on the longest key.
    """
    lines = [f"{name}: {value}" for name, value in info.components.items()]
    lines.append(f"Executable: {sys.executable}")
    return "\n".join(lines)


class AboutDialog:  # pragma: no cover — thin Qt shell over the pure parts
    """Modal About box. Constructed lazily so importing this module costs
    no Qt widgets; see :func:`show_about`."""

    def __new__(cls, info: AboutInfo, parent=None, icon=None):
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtWidgets import (
            QDialog,
            QDialogButtonBox,
            QHBoxLayout,
            QLabel,
            QPlainTextEdit,
            QTabWidget,
            QVBoxLayout,
            QWidget,
        )

        dlg = QDialog(parent)
        dlg.setWindowTitle(f"About {info.app_name}")
        outer = QVBoxLayout(dlg)

        # -- header: icon, name, version, summary
        head = QHBoxLayout()
        if icon is not None and not icon.isNull():
            badge = QLabel()
            badge.setPixmap(icon.pixmap(64, 64))
            head.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)
        titles = QVBoxLayout()
        name = QLabel(f"<h2 style='margin:0'>{info.app_name}</h2>")
        titles.addWidget(name)
        titles.addWidget(QLabel(f"Version {info.version or 'unknown'}"))
        if info.summary:
            blurb = QLabel(info.summary)
            blurb.setWordWrap(True)
            titles.addWidget(blurb)
        if info.license_label:
            # the label may already read "MIT License" (taken off the text)
            # or be a bare SPDX id ("MIT") — only the latter needs the noun
            label = info.license_label
            if "licen" not in label.lower():
                label = f"{label} License"
            titles.addWidget(QLabel(label))
        if info.urls:
            links = " · ".join(
                f'<a href="{url}">{name}</a>' for name, url in info.urls.items()
            )
            link_label = QLabel(links)
            link_label.setOpenExternalLinks(True)
            titles.addWidget(link_label)
        head.addLayout(titles, 1)
        outer.addLayout(head)

        # -- tabs: the diagnostics always, credits and licence when supplied
        tabs = QTabWidget()
        diag = QPlainTextEdit(diagnostics_text(info))
        diag.setReadOnly(True)
        tabs.addTab(diag, "Details")
        if info.credits:
            credits = QPlainTextEdit(info.credits)
            credits.setReadOnly(True)
            tabs.addTab(credits, "Credits")
        if info.license_text:
            lic = QPlainTextEdit(info.license_text)
            lic.setReadOnly(True)
            tabs.addTab(lic, "Licence")
        outer.addWidget(tabs, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        copy_btn = buttons.addButton(
            "Copy diagnostics", QDialogButtonBox.ButtonRole.ActionRole
        )

        def _copy() -> None:
            clip = QGuiApplication.clipboard()
            if clip is not None:
                clip.setText(diagnostics_text(info))
            copy_btn.setText("Copied")

        copy_btn.clicked.connect(_copy)
        buttons.rejected.connect(dlg.reject)
        outer.addWidget(buttons)

        dlg.resize(460, 380)
        # kept so tests and callers can reach them without digging
        dlg.info = info
        dlg.copy_button = copy_btn
        dlg.tabs = tabs
        return dlg


def show_about(owner: "QWidget", info: AboutInfo) -> None:  # noqa: F821
    """Open the About box modally, reusing the owner's window icon."""
    dlg = AboutDialog(info, parent=owner, icon=owner.windowIcon())
    dlg.exec()
