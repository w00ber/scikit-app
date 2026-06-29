# sciappkit (scikit-app)

A framework for building canvas / matplotlib GUI applications for science.

`sciappkit` factors the shared, reusable machinery out of two PySide6
scientific desktop apps — [Diagrammer](https://github.com/w00ber/diagrammer)
(a vector diagram / schematic editor built on `QGraphicsScene`) and
[graphulator](https://github.com/w00ber/graphulator) (interactive graph
drawing for coupled-mode theory, built on an embedded matplotlib canvas) —
into one library that future scientific apps can build on.

> **Status: M1 (normalized APIs).** M0 established the project layout and
> lifted the app-agnostic "clean win" modules. M1 adds the normalized,
> unit-tested building blocks: a typed `SettingsStore`, a
> `ShortcutRegistry`/`ShortcutManager`, the `Exporter` protocol with
> matplotlib/scene exporters, the `CanvasController` protocol with two
> adapters (plus generic scene/view bases), and the `SciAppMainWindow`
> base. The project scaffold + Claude Code skill are M2; migrating the two
> source apps onto the framework is M3.

## Installation

```bash
pip install -e .            # core: PySide6-Essentials (6.8 line), matplotlib, pyyaml
pip install -e ".[math]"    # + numpy, sympy, ziamath (symbolic / LaTeX math)
pip install -e ".[web]"     # + PySide6-Addons (QtWebEngine) + markdown (KaTeX/web rendering)
pip install -e ".[macos]"   # + pyobjc (native macOS clipboard)
pip install -e ".[dev]"     # + pytest
```

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
│   └── main_window.py    # SciAppMainWindow base (menus, export/copy, theme, shortcuts)
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
    └── markdown_editor.py # MarkdownEditor: editor + live preview, formatting shortcuts
```

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
| `widgets/markdown_editor.py` | `MarkdownEditor` (editor + live `setMarkdown` preview)            |

The editor widgets expose `*_shortcut_defs()` / `bind_*_editor_shortcuts()`
helpers so their command keys (bold/italic/link/code, comment toggle, zoom,
toggle preview) are discoverable and rebindable through the
`ShortcutManager`, while still working out of the box.

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
