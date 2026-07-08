# sciappkit (scikit-app)

A framework for building canvas / matplotlib GUI applications for science.

`sciappkit` factors the shared, reusable machinery out of two PySide6
scientific desktop apps — [Diagrammer](https://github.com/w00ber/diagrammer)
(a vector diagram / schematic editor built on `QGraphicsScene`) and
[graphulator](https://github.com/w00ber/graphulator) (interactive graph
drawing for coupled-mode theory, built on an embedded matplotlib canvas) —
into one library that future scientific apps can build on.

> **Status: pre-publish (M4 pending).** M0–M2 delivered the lifted modules,
> the normalized unit-tested building blocks, the `create-sciapp` scaffold,
> and the bundled Claude Code skill; M3 dogfooding repointed Diagrammer's
> theming onto the framework. Publishing to PyPI (M4) hasn't happened yet,
> so installs come from this repo. See [docs/ROADMAP.md](docs/ROADMAP.md).

## Quick start

```bash
pip install "sciappkit[all] @ git+https://github.com/w00ber/scikit-app"
create-sciapp "My Tool"             # scaffold a runnable app
cd my_tool && pip install -e ".[dev]"
my_tool                             # launch it
```

That's a complete desktop app — menus, export, clipboard, preferences,
shortcuts — ready for your canvas and document model. **New here? Read the
[getting-started walkthrough](docs/getting-started.md)** — it takes you from
zero to a working app, with or without Claude Code assisting.

## Documentation

- **[Getting started](docs/getting-started.md)** — install, scaffold, and
  build your first app; includes a beginner walkthrough for working *with*
  Claude Code and one for building entirely by hand.
- **[Roadmap](docs/ROADMAP.md)** — milestone status and the working backlog.
- **The `sciapp` Claude Code skill** — the framework ships a skill (API
  reference, conventions, canvas guide, new-app recipe, runnable minimal
  examples) that teaches Claude Code to build with sciappkit. `create-sciapp`
  copies it into every generated project (`.claude/skills/sciapp/`), so
  Claude assistance works there out of the box. The canonical copy lives at
  [`src/sciappkit/scaffold/skill/`](src/sciappkit/scaffold/skill/) (mirrored
  to this repo's `.claude/skills/sciapp/`); its reference docs are useful
  reading for humans too.

## Installation

For **using** the framework (no checkout needed):

```bash
pip install "sciappkit[all] @ git+https://github.com/w00ber/scikit-app"
```

For **developing** the framework itself, clone and install editable:

```bash
git clone https://github.com/w00ber/scikit-app
cd scikit-app
pip install -e .                    # core: PySide6-Essentials (6.8 line), matplotlib, pyyaml
pip install -e ".[math]"            # + numpy, sympy, ziamath (symbolic / LaTeX math)
pip install -e ".[web]"             # + PySide6-Addons (QtWebEngine) + markdown (inline images / KaTeX)
pip install -e ".[macos]"           # + pyobjc (native macOS clipboard)
pip install -e ".[dev]"             # + pytest
pip install -e ".[all]"             # everything at once
pip install -e ".[math,web,dev]"    # or pick several explicitly
```

`".[all]"` installs every extra; the macOS-only dependency is skipped
automatically on other platforms (via an environment marker), so the same
command works everywhere. (Quote the argument so your shell doesn't expand
the brackets: `pip install -e ".[all]"`.)

The base install deliberately depends on **PySide6-Essentials** (no
QtWebEngine), matching Diagrammer. QtWebEngine — needed only for KaTeX math
rendering — comes with the opt-in `[web]` extra, never as a base dependency.

PySide6 is pinned to the **6.8 line** (`>=6.8,<6.9`). See the comment in
`pyproject.toml` for the regressions that motivate the pin.

## Package layout

```
src/sciappkit/
├── app/
│   ├── theming.py        # light/dark/system Fusion palettes + apply_theme()
│   ├── main_window.py    # SciAppMainWindow base (menus, export/copy, theme, shortcuts)
│   └── settings_dialog.py # reusable Settings dialog (theme + fields + shortcuts tabs)
├── canvas/
│   ├── grid.py           # grid drawing + snap-to-grid for QGraphicsScene canvases
│   ├── mpl_canvas.py     # MplCanvas: matplotlib FigureCanvas embedded in Qt
│   ├── scene_canvas.py   # GraphicsSceneBase / GraphicsViewBase (generic zoom/pan/fit/grid)
│   └── protocol.py       # CanvasController protocol + Mpl/Scene adapters
├── export/
│   ├── clipboard.py      # robust platform-aware PDF/PNG clipboard cascade
│   ├── base.py           # Exporter protocol (uniform export/copy surface)
│   ├── mpl_exporter.py   # MplExporter (Figure -> svg/png/pdf + clipboard)
│   └── scene_exporter.py # SceneExporter (QGraphicsScene -> svg/png/pdf + clipboard)
├── undo/
│   └── stack.py          # SnapshotCommand + snapshot() ctx mgr over QUndoStack
├── settings/
│   ├── defaults.py       # YAML-backed factory-defaults loader
│   ├── defaults.yaml     # framework-level default values
│   ├── store.py          # schema-driven typed SettingsStore (JSON persistence)
│   └── recent_files.py   # RecentFiles MRU helper (store-backed or standalone)
├── shortcuts/
│   ├── model.py          # Shortcut + per-app ShortcutRegistry (resolution + conflicts)
│   ├── manager.py        # ShortcutManager(QObject): signals, QAction binding, persistence
│   └── editor.py         # ShortcutEditorWidget: view/rebind shortcuts, conflict handling
└── widgets/
    ├── spinbox.py        # FineControlSpinBox (Shift/Alt fine/coarse stepping)
    ├── text_edit.py      # LineNumberTextEdit base (line numbers, zoom, theme-aware)
    ├── code_editor.py    # CodeEditor + pluggable syntax highlighting (Python shipped)
    ├── markdown_editor.py # MarkdownEditor: editor + live preview, formatting shortcuts
    └── markdown_preview_web.py # [web] QtWebEngine preview (inline images + KaTeX)
```

Runnable examples live in `examples/`: `demo_app.py` (`--style scene|mpl|both`),
`editors_demo.py` (code + markdown editors), and `full_app.py` — a
full-featured app with canvases, dockable Notes (web preview, inline
images) and Code editors, a Settings dialog (theme + fields + shortcuts),
and recent files.

## Modules lifted in M0

| Module                  | Lifted from                                             |
| ----------------------- | ------------------------------------------------------- |
| `app/theming.py`        | Diagrammer `app.py` (palette / `apply_theme`)           |
| `export/clipboard.py`   | Diagrammer `io/exporter.py` (clipboard cascade)         |
| `canvas/grid.py`        | Diagrammer `canvas/grid.py`                             |
| `settings/defaults.py`  | Diagrammer `defaults.py`                                |
| `canvas/mpl_canvas.py`  | graphulator `para_ui/canvas.py`                         |
| `widgets/spinbox.py`    | graphulator `para_ui/widgets.py` (`FineControlSpinBox`) |

## Normalized APIs added in M1

| Module                     | Role                                                                 |
| -------------------------- | ------------------------------------------------------------------- |
| `settings/store.py`        | Typed, schema-driven `SettingsStore` (Diagrammer typing + graphulator DRY persistence) |
| `settings/recent_files.py` | `RecentFiles` MRU list (store-backed or standalone); drives the Recent Files menu |
| `shortcuts/model.py`       | `Shortcut` (blended per-platform constructor) + per-app `ShortcutRegistry` |
| `shortcuts/manager.py`     | `ShortcutManager(QObject)`: signals, live QAction binding, JSON persistence |
| `shortcuts/editor.py`      | `ShortcutEditorWidget`: view/rebind shortcuts with conflict handling |
| `export/base.py`           | `Exporter` protocol (uniform `export_*` / `copy_to_clipboard`)      |
| `export/mpl_exporter.py`   | `MplExporter` for matplotlib figures                                |
| `export/scene_exporter.py` | `SceneExporter` for `QGraphicsScene` (lifted from Diagrammer)       |
| `canvas/scene_canvas.py`   | Generic `GraphicsSceneBase` / `GraphicsViewBase`                    |
| `canvas/protocol.py`       | `CanvasController` protocol + `MplCanvasController` / `SceneCanvasController` |
| `app/main_window.py`       | `SciAppMainWindow` base wiring it all together                      |
| `undo/stack.py`            | `SnapshotCommand` + `snapshot()` — snapshot-based undo over `QUndoStack` |
| `widgets/text_edit.py`     | `LineNumberTextEdit` base (line numbers, zoom, theme-aware gutter)  |
| `widgets/code_editor.py`   | `CodeEditor` + pluggable `QSyntaxHighlighter` (`PythonHighlighter`) |
| `widgets/markdown_editor.py` | `MarkdownEditor` (editor + live preview; `backend="web"` for inline images) |
| `widgets/markdown_preview_web.py` | `WebMarkdownPreview` ([web] QtWebEngine: inline images + KaTeX) |
| `app/settings_dialog.py`   | reusable `SettingsDialog` (theme + field binding + shortcut editor) |

The editor widgets expose `*_shortcut_defs()` / `bind_*_editor_shortcuts()`
helpers so their command keys (bold/italic/link/code, comment toggle, zoom,
toggle preview) are discoverable and rebindable through the
`ShortcutManager`, while still working out of the box.

## Scaffold a new app (`create-sciapp`)

```bash
create-sciapp "Spectrum Tool" --canvas-style both   # or scene / mpl
cd spectrum_tool
pip install -e ".[dev]"
spectrum_tool                       # launch the generated GUI
QT_QPA_PLATFORM=offscreen pytest    # the generated app ships with a test
```

| Flag | Meaning |
| --- | --- |
| `NAME` (positional) | App title, e.g. `"Spectrum Tool"` |
| `-c`, `--canvas-style` | `scene`, `mpl`, or `both` (default) |
| `-d`, `--directory` | Parent directory to create the project in (default: current) |
| `-p`, `--package` | Import name (default: derived from the title) |
| `--author` | Author name for `pyproject.toml` |
| `-f`, `--force` | Write into an existing, non-empty directory |
| `--no-skill` | Skip bundling the Claude Code skill (included by default) |

The generator emits a runnable, src-layout app wired to the framework
(settings, shortcuts, canvas, a `SciAppMainWindow` subclass, docs, a test,
a `CLAUDE.md`, and the `sciapp` Claude Code skill). It's also available
programmatically as `sciappkit.scaffold.create_app(...)`. The full tour of
the generated project is in the
[getting-started walkthrough](docs/getting-started.md).

## Development

The test suite runs Qt headless. Install the system libraries and Python
deps once per environment with:

```bash
./scripts/setup-test-env.sh
```

Then:

```bash
python -c "import sciappkit"          # import smoke check
QT_QPA_PLATFORM=offscreen pytest      # full suite, headless (the default)
xvfb-run -a pytest                    # or under a virtual X server
```

## License

MIT — see [LICENSE](LICENSE).
