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
- **M2 — scaffold + skill** ✅ — `create-sciapp` generator
  (`scene`/`mpl`/`both`, self-contained — no external template engine) +
  the `.claude/skills/sciapp/` skill (SKILL.md, API/conventions/canvas
  reference, new-app recipe, runnable minimal examples). End-to-end
  validated: each style generates, builds headless, and exports.
- **M3 — dogfood** — Diagrammer theming now imports from
  `sciappkit.app.theming` ✅. Graphulator's clipboard adoption was dropped:
  its `main` had independently grown a **superset** figure-to-clipboard
  (PDF + SVG + PNG). That gap is now closed in the framework (see
  *SVG clipboard flavour* below), so sciappkit is the canonical superset.
- **M4 — publish.**

## M2 backlog (in-repo additions to the plan)

- **Inline image + math rendering in the markdown preview (`[web]` extra).**
  ✅ Done in M1 hardening (pulled forward): `WebMarkdownPreview` +
  `MarkdownEditor(backend="web")` render markdown → HTML in a QWebEngineView
  so inline base64 images display; optional KaTeX via `katex_base_url`. The
  native `setMarkdown` preview stays the default. Still feeds the planned
  `docs/help_window.py` (KaTeX-in-QWebEngine help) — keep for M2.

## M1 hardening checklist

- [x] Editor widgets (code + markdown) with rebindable shortcuts.
- [x] End-to-end example app (`examples/demo_app.py`) + integration test.
- [x] Editors demo (`examples/editors_demo.py`) + integration test.
- [x] Example variants for each `canvas_style` (`scene` / `mpl` / `both`).
- [x] `RecentFiles` helper + a Recent Files menu in `SciAppMainWindow`.
- [x] `ShortcutEditorWidget` for viewing/rebinding shortcuts.
- [x] `undo/stack.py` `SnapshotCommand` + `snapshot()` helper.
- [x] `[web]` `WebMarkdownPreview` (inline images + optional KaTeX).
- [x] Reusable `SettingsDialog` (theme + field binding + shortcuts tab).
- [x] Full-featured demo (`examples/full_app.py`) tying it all together.

## Post-M2 refinements

- [x] **Code-editor color schemes** (`widgets/highlight_theme.py`) — Dracula /
  Monokai / Solarized dark+light / Zenburn / GitHub-light; `CodeEditor(theme=…)`
  applies bg+fg+tokens as a matched set. Fixes the dark-mode contrast bug
  (colors were picked from the palette before dark was applied).
- [x] **Markdown image attachments** — pasted/dropped images stored out of
  band as `![alt](attachment:key)` (no base64 blob in the source); web
  preview resolves them and follows light/dark.
- [x] **Matplotlib theming** (`canvas/mpl_theme.py`) — `apply_mpl_theme` themes
  the chrome + sets a validated CVD-safe color cycle; wired through
  `MplCanvasController.apply_theme` and the app theme change.
- [x] **SVG clipboard flavour** (`export/clipboard.py`) — `copy_to_clipboard`
  gained an optional `svg_data` arg threaded through the whole macOS cascade
  (`public.svg-image`) and the Qt fallback (`image/svg+xml`), mirroring the
  superset graphulator's `main` exposed. `MplExporter` (self-contained SVG via
  `svg.fonttype="path"`) and `SceneExporter` (`QSvgGenerator` → `QBuffer`) now
  put PDF + SVG + PNG on the clipboard. Backward-compatible: `svg_data`
  defaults to `None`.
- [x] **On-canvas shortcut overlay** (`shortcuts/overlay.py`) —
  `ShortcutOverlay` (translucent context-sensitive cheat-sheet widget, lifted
  from Diagrammer's `_relayout`-fixed copy), a `ShortcutOverlayMixin` for the
  shared toggle/reposition/update wiring, and `overlay_rows_from_registry()`
  to build a zero-curation cheat sheet from a `ShortcutRegistry`. Dogfooded in
  `examples/full_app.py` (press `?`). Re-exported from `sciappkit.shortcuts`.
