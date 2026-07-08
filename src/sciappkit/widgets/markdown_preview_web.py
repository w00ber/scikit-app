"""QtWebEngine-backed markdown preview (renders inline images + math).

The native :class:`~sciappkit.widgets.markdown_editor.MarkdownEditor`
preview uses Qt's ``QTextBrowser.setMarkdown``, which renders text and
formatting but **not** inline base64 data-URI images (a ``QTextDocument``
limitation). This preview renders markdown to HTML with the ``markdown``
library and displays it in a ``QWebEngineView``, so embedded images show
up; optional KaTeX support renders ``$…$`` / ``$$…$$`` math when a KaTeX
base URL is supplied.

Requires the ``[web]`` extra (PySide6-Addons / QtWebEngine + ``markdown``).
Import this module only when that extra is installed.

Note for headless/CI use: QtWebEngine's Chromium may need
``QTWEBENGINE_DISABLE_SANDBOX=1`` and ``--no-sandbox``; the test suite sets
these in ``conftest.py``.
"""

from __future__ import annotations

from PySide6.QtGui import QPalette
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget

_MARKDOWN_EXTENSIONS = ["extra", "sane_lists", "nl2br", "admonition"]

# KaTeX auto-render snippet, included only when a base URL is configured.
_KATEX_TEMPLATE = """\
<link rel="stylesheet" href="{base}/katex.min.css">
<script defer src="{base}/katex.min.js"></script>
<script defer src="{base}/contrib/auto-render.min.js"
    onload="renderMathInElement(document.body, {{
        delimiters: [
            {{left: '$$', right: '$$', display: true}},
            {{left: '$', right: '$', display: false}}
        ]
    }});"></script>
"""


class WebMarkdownPreview(QWidget):
    """A markdown preview that renders inline images (and optional math).

    ``katex_base_url`` enables math: point it at a directory/CDN containing
    ``katex.min.css``, ``katex.min.js`` and ``contrib/auto-render.min.js``.
    When unset, math delimiters are left as literal text.
    """

    def __init__(self, parent: QWidget | None = None, *, katex_base_url: str | None = None) -> None:
        super().__init__(parent)
        self._katex_base_url = katex_base_url
        self._attachments: dict[str, str] = {}   # key -> data URI
        self._view = QWebEngineView(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._view)
        self.set_markdown("")

    def set_attachments(self, mapping) -> None:
        """Register images referenced as ``attachment:<key>`` in the source.

        Accepts a mapping of key -> ``(raw_bytes, mime)`` (as held by
        ``MarkdownTextEdit.attachments``) or key -> data-URI string.
        """
        import base64

        resolved: dict[str, str] = {}
        for key, value in (mapping or {}).items():
            if isinstance(value, str):
                resolved[key] = value
            else:
                raw, mime = value
                b64 = base64.b64encode(bytes(raw)).decode("ascii")
                resolved[key] = f"data:{mime};base64,{b64}"
        self._attachments = resolved

    @property
    def view(self) -> QWebEngineView:
        return self._view

    def set_markdown(self, text: str) -> None:
        """Render *text* (markdown) into the preview."""
        self._view.setHtml(self.to_html(text))

    # Provided as the uniform name MarkdownEditor calls on either backend.
    setMarkdown = set_markdown

    def to_html(self, text: str) -> str:
        """Convert markdown *text* to a full themed HTML document.

        Pure and synchronous, so it's easy to test without rendering.
        """
        try:
            import markdown as _md

            body = _md.markdown(text or "", extensions=_MARKDOWN_EXTENSIONS)
        except ImportError:
            # Graceful fallback if the markdown lib is somehow absent.
            import html as _html

            body = f"<pre>{_html.escape(text or '')}</pre>"

        # Resolve attachment: references to inline data URIs.
        for key, uri in self._attachments.items():
            body = body.replace(f"attachment:{key}", uri)

        math = ""
        if self._katex_base_url:
            math = _KATEX_TEMPLATE.format(base=self._katex_base_url.rstrip("/"))

        return (
            "<!DOCTYPE html><html><head><meta charset='utf-8'>"
            f"<style>{self._css()}</style>{math}</head>"
            f"<body>{body}</body></html>"
        )

    def _css(self) -> str:
        """Theme-aware 'paper' CSS derived from the application palette."""
        app = QApplication.instance()
        palette = app.palette() if app is not None else self.palette()
        bg = palette.color(QPalette.ColorRole.Base).name()
        fg = palette.color(QPalette.ColorRole.Text).name()
        link = palette.color(QPalette.ColorRole.Link).name()
        faint = palette.color(QPalette.ColorRole.AlternateBase).name()
        return f"""
        body {{
            font-family: -apple-system, "Segoe UI", system-ui, sans-serif;
            font-size: 14px; line-height: 1.5;
            color: {fg}; background: {bg};
            margin: 12px 16px;
        }}
        a {{ color: {link}; }}
        h1, h2, h3 {{ line-height: 1.25; }}
        h1 {{ font-size: 1.6em; }} h2 {{ font-size: 1.3em; }}
        code, pre {{
            font-family: Menlo, Consolas, monospace;
            background: {faint}; border-radius: 4px;
        }}
        code {{ padding: 0 4px; }}
        pre {{ padding: 8px 10px; overflow-x: auto; }}
        pre code {{ background: transparent; padding: 0; }}
        img {{ max-width: 100%; height: auto; }}
        blockquote {{
            margin: 0; padding: 0 12px;
            border-left: 3px solid {faint}; opacity: 0.85;
        }}
        table {{ border-collapse: collapse; }}
        th, td {{ border: 1px solid {faint}; padding: 4px 8px; }}
        """
