# sciappkit conventions

## Project shape

- **src-layout**: code under `src/<package>/`; tests under `tests/`.
- Entry point: `[project.gui-scripts] <pkg> = "<pkg>.app:main"`; `app.py`
  builds the `QApplication` and the `SciAppMainWindow` subclass.
- One module each for `settings.py`, `shortcuts.py`, `canvas.py`,
  `main_window.py` (this is what `create-sciapp` emits — keep that split).

## Dependencies / Qt pin

- Base depends on **`PySide6-Essentials>=6.8,<6.9`** (no QtWebEngine),
  `matplotlib`, `pyyaml`. **Do not bump past 6.8**: 6.9 has Windows DLL
  issues; 6.11 regresses `QSvgRenderer` on the PDF surface (breaks vector
  export).
- Extras: `[math]` (numpy/sympy/ziamath), `[web]` (PySide6-Addons /
  QtWebEngine + markdown — for inline-image/KaTeX markdown preview),
  `[macos]` (pyobjc for native clipboard), `[dev]` (pytest), and `[all]`
  (everything). Anything needing QtWebEngine must be an optional `[web]`
  import, never a base dependency.

## Settings

- Each setting is declared once as a `Setting` in a schema list; the
  `SettingsStore` derives save/load/reset. Persisted to
  `~/.<app_name>/settings.json`.
- Factory defaults come from a YAML loader. Apps ship `defaults.yaml` beside
  `settings.py` and call `defaults.set_defaults_path(...)` (the scaffold does
  this). `Setting(section=, key=)` pulls a value from it.
- Non-JSON types use a `codec` (`QColorCodec`, `SetCodec`); add your own as a
  small `encode`/`decode` object to keep the store JSON-native.
- A `recent_files` (list, `mutable=True`) field auto-enables the Recent menu.

## Shortcuts

- Per-app `ShortcutRegistry` (no global singleton) + `ShortcutManager`.
  Persisted to `~/.<app_name>/shortcuts.json` (only non-default overrides).
- **Action-ID scheme**: dotted `area.action`, e.g. `file.new`, `edit.undo`,
  `view.fit`. `SciAppMainWindow` binds these IDs if present:
  `file.new/open/save/save_as/export_svg/export_png/export_pdf/quit`,
  `edit.undo/redo/copy_as_image`, `view.fit/zoom_in/zoom_out`. Register them
  so the menus get keys.
- Editor command IDs come from `code_editor_shortcut_defs()` /
  `markdown_editor_shortcut_defs()`; register them and call the matching
  `bind_*` helper to make the editor keys rebindable.
- Declare per-platform keys with `mac=`/`win=`/`linux=`; otherwise `default=`
  ("Ctrl+..." maps to ⌘ on macOS automatically). Prefer
  `QKeySequence.StandardKey` for standard actions.
- **Discoverability**: `ShortcutEditorWidget` (Settings) is for *rebinding*;
  the on-canvas `ShortcutOverlay` cheat sheet (toggled with `?`) is for
  *learning*. Register the toggle as a single-key **menu** action
  (`is_single_key=True, is_menu_action=True`) so `?` typed in a text field
  goes to the field, not the overlay.

## Theming

- `apply_theme(app, mode)` with `mode in THEMES` ("system"/"light"/"dark").
  `SciAppMainWindow` builds the View→Appearance menu and persists the choice.
- For inline-styled widgets, use `hint_text_color()` instead of hard-coded
  grays so text stays legible in dark mode.

## Canvas / export

- Drive everything through the `CanvasController` protocol; the host menu
  calls `controller.exporter.export_<fmt>(controller.export_target(), path)`
  and `controller.exporter.copy_to_clipboard(controller.export_target())`.
- Keep app-specific interaction (connections, ports, item drags) in your
  `GraphicsViewBase`/scene subclass; the base only provides zoom/pan/fit/grid.

## Testing & packaging

- Tests run headless: set `QT_QPA_PLATFORM=offscreen` (a `conftest.py` doing
  `os.environ.setdefault(...)` before importing PySide6 is the pattern). For
  QtWebEngine tests also set `QTWEBENGINE_DISABLE_SANDBOX=1` and
  `QTWEBENGINE_CHROMIUM_FLAGS="--no-sandbox --disable-gpu"`.
- For a real display in CI, `xvfb-run -a pytest` with `QT_QPA_PLATFORM=xcb`.
- Bundle data (`defaults.yaml`, `docs/*.md`) via
  `[tool.setuptools.package-data]`. For PyInstaller, resolve bundled files
  relative to `__file__` (a `_resources.py` helper), never the CWD.
