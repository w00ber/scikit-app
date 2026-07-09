---
name: sciapp
description: Build a PySide6 + matplotlib scientific desktop app with the sciappkit framework. Use when creating a new canvas/plot GUI, scaffolding with create-sciapp, or wiring sciappkit building blocks — SciAppMainWindow, canvas controllers (scene/matplotlib), SettingsStore, the shortcut system, the code/markdown editors, and SVG/PNG/PDF + clipboard export.
---

# Building scientific apps with sciappkit

`sciappkit` (import name `sciappkit`, repo `scikit-app`) is a PySide6 + matplotlib
framework that factors out the shared machinery of scientific desktop apps:
a main-window base, two interchangeable canvas kinds, typed settings,
rebindable shortcuts, editors, and uniform export. Build apps from these
blocks instead of hand-rolling Qt.

## When to use this skill

- Creating a new scientific GUI app (a drawing canvas and/or a matplotlib plot).
- Adding framework features to a sciappkit app: a canvas, a setting, a
  shortcut, an export format, a code or markdown editor.
- Scaffolding a new project with `create-sciapp`.

## Start here: scaffold, don't hand-write

```bash
create-sciapp "My Tool" --canvas-style both    # scene | mpl | both
cd my_tool
pip install -e ".[dev]"
my_tool                                          # launch the GUI
QT_QPA_PLATFORM=offscreen pytest                 # generated test runs headless
```

All `create-sciapp` flags: `-d/--directory` (parent dir, default `.`),
`-p/--package` (import name, else derived from the title),
`-c/--canvas-style` (`scene`|`mpl`|`both`, default `both`), `--author`,
`-f/--force` (write into a non-empty dir), `--no-skill` (skip copying this
skill into the project — it is bundled by default so Claude Code works in
the generated app out of the box).

This emits a runnable, src-layout app wired to the framework. Then edit:

- `src/my_tool/canvas.py` — `build_controllers()`: the canvas(es).
- `src/my_tool/main_window.py` — menus + `do_new`/`do_open`/`do_save`.
- `src/my_tool/settings.py` — the typed settings schema.
- `src/my_tool/shortcuts.py` — the shortcut registry.

## The ~12-symbol public API (cheat sheet)

| Need | Symbol |
| --- | --- |
| App window base | `sciappkit.app.main_window.SciAppMainWindow` |
| Theme | `sciappkit.app.theming.apply_theme(app, mode)`, `THEMES` |
| App icon | `sciappkit.app.icons.set_app_icon(app, icons_dir)` (multi-res ladder; macOS Dock works unbundled) |
| Settings dialog | `sciappkit.app.settings_dialog.SettingsDialog` |
| Typed settings | `sciappkit.settings.store.SettingsStore`, `Setting` |
| Recent files | `sciappkit.settings.recent_files.RecentFiles` |
| Shortcuts | `sciappkit.shortcuts.model.Shortcut`, `ShortcutRegistry`; `manager.ShortcutManager`; `editor.ShortcutEditorWidget` |
| Shortcut cheat sheet | `sciappkit.shortcuts.overlay.ShortcutOverlay`, `ShortcutOverlayMixin`, `overlay_rows_from_registry(registry)` |
| Canvas contract | `sciappkit.canvas.protocol.CanvasController` |
| Canvas adapters | `MplCanvasController`, `SceneCanvasController` |
| Scene canvas | `sciappkit.canvas.scene_canvas.GraphicsSceneBase` / `GraphicsViewBase` |
| Mpl canvas | `sciappkit.canvas.mpl_canvas.MplCanvas` |
| Export | `sciappkit.export.{mpl_exporter.MplExporter, scene_exporter.SceneExporter}`; `clipboard.copy_to_clipboard(pdf, png, svg=None)` |
| Undo | `sciappkit.undo.stack.SnapshotCommand`, `snapshot(...)` |
| Editors | `sciappkit.widgets.{code_editor.CodeEditor, markdown_editor.MarkdownEditor, spinbox.FineControlSpinBox}` |
| Scaffold | `sciappkit.scaffold.create_app(...)` |

The `sciappkit.shortcuts` package re-exports its public surface, so
`from sciappkit.shortcuts import Shortcut, ShortcutRegistry, ShortcutManager,
ShortcutEditorWidget, ShortcutOverlay, ShortcutOverlayMixin,
overlay_rows_from_registry` works without the submodule paths.

Full signatures: `reference/api.md`. Conventions (settings dir, shortcut
IDs, Qt pin, headless testing): `reference/conventions.md`. Choosing and
wiring a canvas: `reference/canvas.md`. Step-by-step build:
`recipes/new_app.md`.

## Non-negotiables

- **Qt is pinned to the 6.8 line** (`PySide6-Essentials>=6.8,<6.9`). Don't
  bump it (6.9 has Windows DLL issues; 6.11 regresses SVG/PDF export).
- **Drive the canvas through the `CanvasController` protocol** so the same
  Export/Copy menu works for either canvas kind. Don't special-case.
- **QtWebEngine features** (markdown `backend="web"` with inline images) need
  the `[web]` extra; keep them optional, never a base import.
- **Tests run headless**: `QT_QPA_PLATFORM=offscreen pytest`.
