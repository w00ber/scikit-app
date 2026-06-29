# sciappkit roadmap

The authoritative design plan lives in the Diagrammer repo at
`docs/sciapp-kit-plan.md` (branch `claude/scientific-app-framework-on41vf`).
This file tracks the in-repo working backlog and any items discovered while
building, so the framework repo is self-describing.

## Status

- **M0 — scaffold + lift-and-shift** ✅ — `theming`, `clipboard`, `grid`,
  `defaults`, `mpl_canvas`, `FineControlSpinBox`. Qt pinned `>=6.8,<6.9`.
- **M1 — normalized APIs** ✅ (+ hardening in progress) — `SettingsStore`,
  `ShortcutRegistry`/`ShortcutManager`, `Exporter` + `Mpl`/`Scene`
  exporters, `CanvasController` + adapters + generic scene/view bases,
  `SciAppMainWindow`. Added beyond the plan's M1 bullet: the editor
  widgets (`LineNumberTextEdit`, `CodeEditor` + syntax highlighting,
  `MarkdownEditor` + live preview) with rebindable shortcut helpers.
- **M2 — scaffold + skill** ⏳ — `create-sciapp` copier template
  (`scene`/`mpl`/`both`) + `.claude/skills/sciapp/` with runnable examples.
- **M3 — dogfood** — repoint Diagrammer theming + graphulator clipboard to
  the library.
- **M4 — publish.**

## M2 backlog (in-repo additions to the plan)

- **Inline image + math rendering in the markdown preview (`[web]` extra).**
  The current `MarkdownEditor` preview uses Qt-native
  `QTextBrowser.setMarkdown`, which renders text/formatting but **not**
  inline base64 data-URI images (a `QTextDocument` limitation) and no math.
  Apps here need inline images. Plan: add an optional QtWebEngine-backed
  preview (`MarkdownEditor(..., backend="web")` or a `WebMarkdownPreview`)
  that renders markdown → HTML (the `markdown` lib, already in `[web]`) with
  `<img>` data URIs working, and KaTeX for `$…$` / `$$…$$` math. Gated
  behind the `[web]` extra (PySide6-Addons / QtWebEngine); the native
  preview stays the default so the base install needs no web stack. This
  also feeds the planned `docs/help_window.py` (KaTeX-in-QWebEngine help).

## M1 hardening checklist

- [x] Editor widgets (code + markdown) with rebindable shortcuts.
- [x] End-to-end example app (`examples/demo_app.py`) + integration test.
- [x] Editors demo (`examples/editors_demo.py`) + integration test.
- [x] Example variants for each `canvas_style` (`scene` / `mpl` / `both`).
- [x] `RecentFiles` helper + a Recent Files menu in `SciAppMainWindow`.
- [x] `ShortcutEditorWidget` for viewing/rebinding shortcuts.
