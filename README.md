# sciappkit (scikit-app)

A framework for building canvas / matplotlib GUI applications for science.

`sciappkit` factors the shared, reusable machinery out of two PySide6
scientific desktop apps — [Diagrammer](https://github.com/w00ber/diagrammer)
(a vector diagram / schematic editor built on `QGraphicsScene`) and
[graphulator](https://github.com/w00ber/graphulator) (interactive graph
drawing for coupled-mode theory, built on an embedded matplotlib canvas) —
into one library that future scientific apps can build on.

> **Status: M0 (scaffold + lift-and-shift).** This milestone establishes the
> project layout and lifts the "clean win" modules that are already
> app-agnostic. The canvas–controller protocol and the higher-level building
> blocks land in later milestones (M1+). The two source apps are not yet
> migrated onto the framework (that is M3).

## Installation

```bash
pip install -e .            # core: PySide6 (6.8 line), matplotlib, pyyaml
pip install -e ".[math]"    # + numpy, sympy, ziamath (symbolic / LaTeX math)
pip install -e ".[web]"     # + markdown (web/KaTeX rendering helpers)
pip install -e ".[macos]"   # + pyobjc (native macOS clipboard)
pip install -e ".[dev]"     # + pytest
```

PySide6 is pinned to the **6.8 line** (`>=6.8,<6.9`). See the comment in
`pyproject.toml` for the regressions that motivate the pin.

## Package layout

```
src/sciappkit/
├── app/
│   └── theming.py        # light/dark/system Fusion palettes + apply_theme()
├── canvas/
│   ├── grid.py           # grid drawing + snap-to-grid for QGraphicsScene canvases
│   └── mpl_canvas.py     # MplCanvas: matplotlib FigureCanvas embedded in Qt
├── export/
│   └── clipboard.py      # robust platform-aware PDF/PNG clipboard cascade
├── settings/
│   ├── defaults.py       # YAML-backed factory-defaults loader
│   └── defaults.yaml     # framework-level default values
└── widgets/
    └── spinbox.py        # FineControlSpinBox (Shift/Alt fine/coarse stepping)
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
