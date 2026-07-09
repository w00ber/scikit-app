# Getting started with sciappkit

This walkthrough takes you from nothing to a running scientific desktop app,
then shows two ways to grow it: **with Claude Code assisting** ([Path A](#path-a--building-with-claude-code))
or **entirely by hand** ([Path B](#path-b--building-by-hand)). It assumes you
know Python; it does *not* assume you know Qt.

## What you'll build

A native desktop app with a drawing canvas and/or a matplotlib plot, where the
framework gives you — for free:

- a main window with **File / Edit / View menus**, document open/save plumbing,
  a Recent Files menu, and dirty-state ("unsaved changes") tracking;
- **export** of whatever's on the canvas to SVG / PNG / PDF, and
  **copy-to-clipboard as an editable vector** (PDF + SVG + PNG, so pasting into
  Illustrator, Keynote, or PowerPoint keeps real vectors);
- a **Preferences dialog** with light/dark/system theme, your own typed
  settings, and a shortcut-rebinding tab;
- **rebindable keyboard shortcuts** plus an optional on-canvas cheat-sheet
  overlay (press `?`);
- **undo/redo**, and optional **code / markdown editors** with syntax
  highlighting and live preview.

You write: what's on your canvas, your settings schema, and your document model.

## Prerequisites

- **Python ≥ 3.10** and `pip`. A virtual environment is strongly recommended:

  ```bash
  python3 -m venv .venv && source .venv/bin/activate
  ```

- No Qt knowledge or system Qt install needed — `pip` brings in PySide6
  (pinned to the Qt 6.8 line; the pin is deliberate, see
  [Troubleshooting](#troubleshooting)).
- **Headless Linux / CI only**: Qt needs a few system libraries even for
  offscreen rendering. Run `scripts/setup-test-env.sh` from a checkout of this
  repo (safe to re-run), and run tests with `QT_QPA_PLATFORM=offscreen`.
  On a normal desktop (macOS / Windows / Linux with a display) skip this.

## Install sciappkit

sciappkit is not on PyPI yet, so install straight from GitHub:

```bash
pip install "sciappkit[all] @ git+https://github.com/w00ber/scikit-app"
```

Or, if you want to read or hack on the framework itself, clone and install
editable:

```bash
git clone https://github.com/w00ber/scikit-app
cd scikit-app
pip install -e ".[all]"
```

The extras, if you'd rather pick à la carte than take `[all]`:

| Extra | What it adds |
| --- | --- |
| `[math]` | numpy, sympy, ziamath (math rendering helpers) |
| `[web]` | QtWebEngine + markdown — the web markdown preview (inline images, KaTeX) |
| `[macos]` | PyObjC — the native macOS clipboard path (there are fallbacks without it) |
| `[dev]` | pytest |
| `[all]` | everything above |

Check the install worked:

```bash
create-sciapp --help
```

## Create your app

One command scaffolds a complete, runnable project:

```bash
create-sciapp "Spectrum Tool" --canvas-style both
cd spectrum_tool
pip install -e ".[dev]"
spectrum_tool                          # launch the GUI
QT_QPA_PLATFORM=offscreen pytest       # the generated smoke test passes
```

All the flags:

| Flag | Meaning |
| --- | --- |
| `NAME` (positional) | App title, e.g. `"Spectrum Tool"` |
| `-c`, `--canvas-style` | `scene` (drawing canvas), `mpl` (matplotlib plot), or `both` (tabs; default) |
| `-d`, `--directory` | Parent directory to create the project in (default: current) |
| `-p`, `--package` | Import name (default: derived from the title → `spectrum_tool`) |
| `--author` | Author name for `pyproject.toml` |
| `-f`, `--force` | Write into an existing, non-empty directory |
| `--no-skill` | Skip bundling the Claude Code skill (included by default) |

### What you just got

```
spectrum_tool/
├── pyproject.toml            # depends on sciappkit; `spectrum_tool` launcher
├── README.md, CLAUDE.md, .gitignore
├── .claude/skills/sciapp/    # Claude Code skill — makes Path A work
├── src/spectrum_tool/
│   ├── app.py                # QApplication + main() — rarely touched
│   ├── main_window.py        # ★ your window: menus + do_new/do_open/do_save
│   ├── canvas.py             # ★ build_controllers(): what's on the canvas
│   ├── settings.py           # ★ typed settings schema
│   ├── shortcuts.py          # ★ the shortcut registry
│   ├── defaults.yaml         # factory defaults for the settings
│   └── icons/                # drop your app icon PNGs here (see its README)
├── docs/help.md, docs/tutorial.md
└── tests/test_app.py         # headless smoke test
```

The four ★ files are where all your work happens. Everything else is wiring
you can ignore until you need it.

Launch it (`spectrum_tool`) and poke around before writing any code: draw-area
and plot tabs, **File → Export** to SVG/PNG/PDF, **Edit → Copy to Clipboard**
(paste into a slide app — it's a real vector), **Tools → Preferences** for
theme, grid settings, and shortcut rebinding.

---

## Path A — building with Claude Code

The scaffold already put the `sciapp` skill into your project at
`.claude/skills/sciapp/`. It teaches Claude the framework's API, its
conventions (the Qt version pin, settings/shortcut patterns, headless
testing), a step-by-step build recipe, and two minimal reference apps — so
Claude reaches for framework blocks instead of hand-rolling Qt.

Start Claude Code in the project and drive with plain requests:

```bash
cd spectrum_tool
claude
```

Prompts that work well as first steps:

- *"Plot a damped sine on the matplotlib canvas, and add a 'damping' setting
  (0.1–10, step 0.1) that shows up in Preferences and re-plots on Apply."*
- *"Replace the placeholder rectangle on the scene canvas with draggable
  circles that snap to the grid."*
- *"Add Ctrl+D to duplicate the selected scene item, with a menu entry under
  a new Edit submenu, rebindable in Preferences."*
- *"Add a Notes dock using the framework's markdown editor with the web
  preview."*
- *"Implement do_open/do_save so the document round-trips my model as JSON,
  with undo support."*
- *"Add the on-canvas shortcut cheat-sheet overlay, toggled with ?."*

Two habits keep this smooth:

1. Ask Claude to **run the tests after each change**
   (`QT_QPA_PLATFORM=offscreen pytest`) — the scaffold's smoke test plus any
   tests you add build the window headless, so breakage is caught without a
   screen.
2. When Claude proposes hand-rolled Qt for something the framework covers
   (settings, shortcuts, export, editors), point it at the skill: *"check the
   sciapp skill first."*

## Path B — building by hand

The same journey without an assistant. Each step is self-contained; the code
is complete and matches what the scaffold generated.

### 1. Put something real on the canvas

Edit `src/spectrum_tool/canvas.py`. `build_controllers()` returns the
canvas(es) the window shows — one controller fills the window, several become
tabs. For the plot:

```python
import numpy as np

def build_controllers():
    canvas = MplCanvas(show_axes=True)
    freq = np.linspace(4.0, 6.0, 400)
    q = 40.0
    response = 1.0 / (1 + 1j * q * (freq / 5.0 - 5.0 / freq))
    canvas.ax.plot(freq, np.abs(response))
    canvas.ax.set_xlabel("Frequency (GHz)")
    canvas.ax.set_ylabel("|response|")
    return [MplCanvasController(canvas)]
```

Relaunch (`spectrum_tool`). Export and clipboard now operate on *your* plot —
that's the `CanvasController` contract doing the work: the window drives
whatever controller is active, so you never wire export menus yourself.

For a drawing canvas instead, keep the scene branch: put items into
`GraphicsSceneBase` (a `QGraphicsScene`) and return
`SceneCanvasController(view)`. Zoom/pan/grid/snap come from `GraphicsViewBase`.

### 2. Add a setting, end to end

Settings are declared once and get persistence, defaults, and reset for free.
In `src/spectrum_tool/settings.py`, add to `SCHEMA`:

```python
Setting("quality_factor", 40.0, section="plot", key="q"),
```

Give it a factory default in `src/spectrum_tool/defaults.yaml`:

```yaml
plot:
  q: 40.0
```

Surface it in Preferences — in `main_window.py`, `open_preferences()`:

```python
dialog.add_double("quality_factor", "Quality factor Q", minimum=1, maximum=500, step=1)
```

Read it anywhere as `self._settings.quality_factor`. To re-plot when the user
hits Apply, connect the dialog's `applied` signal:

```python
def open_preferences(self) -> None:
    dialog = SettingsDialog(self._settings, self._shortcuts, self)
    dialog.add_double("quality_factor", "Quality factor Q", minimum=1, maximum=500, step=1)
    dialog.applied.connect(self._replot)
    dialog.exec()
```

Settings persist to `~/.spectrum_tool/settings.json` automatically.

### 3. Add a shortcut + menu action

In `src/spectrum_tool/shortcuts.py`, register:

```python
Shortcut("tools.replot", default="Ctrl+R", category="Tools", display_name="Replot"),
```

(`"Ctrl+R"` becomes ⌘R on macOS automatically.) In `main_window.py`:

```python
def populate_extra_menus(self, menubar) -> None:
    tools = menubar.addMenu("&Tools")
    self._add_action(tools, "&Replot", self._replot, "tools.replot")
    self._add_action(tools, "&Preferences…", self.open_preferences, "edit.preferences")
```

`_add_action` binds the key through the shortcut manager, which means the
binding shows up — and can be changed — in the Preferences Shortcuts tab.

### 4. Save and open documents

Implement the three hooks in `main_window.py`; the base window already owns
the file dialogs, Recent Files menu, window title, and unsaved-changes
prompts:

```python
def do_new(self) -> None:
    self.model = {"points": []}

def do_open(self, path: str) -> bool:
    try:
        self.model = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return True

def do_save(self, path: str) -> bool:
    try:
        Path(path).write_text(json.dumps(self.model), encoding="utf-8")
    except OSError:
        return False
    return True
```

For undo without writing per-operation command classes, wrap mutations in a
snapshot:

```python
from sciappkit.undo.stack import snapshot

with snapshot(scene.undo_stack, "Add point", capture, restore):
    self.model["points"].append(p)
```

### 5. Add the shortcut cheat sheet (optional, nice)

An on-canvas overlay listing live bindings, toggled with `?`. Three pieces:
register the toggle in `shortcuts.py`:

```python
Shortcut("overlay.toggle", default="?", category="Help",
         display_name="Toggle Shortcut Hints",
         is_single_key=True, is_menu_action=True),
```

mix the overlay into your window and provide its two hooks:

```python
from sciappkit.shortcuts import ShortcutOverlayMixin, overlay_rows_from_registry

class SpectrumToolWindow(SciAppMainWindow, ShortcutOverlayMixin):
    def __init__(self):
        super().__init__(...)
        self.init_shortcut_overlay(corner="top-right")

    def shortcut_overlay_host(self):
        return self.active_controller().widget()

    def shortcut_overlay_rows(self):
        return ("Keyboard shortcuts", overlay_rows_from_registry(self._shortcuts.registry))
```

and add the checkable menu entry in `populate_extra_menus`:

```python
help_menu = menubar.addMenu("&Help")
self._add_action(help_menu, "Keyboard Shortcut &Hints",
                 self.toggle_shortcut_overlay, "overlay.toggle", checkable=True)
```

The rows come straight from the registry, so if the user rebinds a key in
Preferences, the overlay shows the new one.

### 6. Give your app an icon

The scaffold already calls `set_app_icon(app, .../icons)` in `app.py` — you
just drop PNGs into `src/spectrum_tool/icons/`. Use the macOS-style ladder
(`icon_16x16.png` … `icon_512x512.png`, plus `@2x` retina variants); Qt
combines them into one icon and picks the right size per context, and on
macOS this sets the **Dock icon at runtime** — no `.app` bundle required.
Generate the whole ladder from a single 1024×1024 master (macOS):

```bash
cd src/spectrum_tool/icons
for s in 16 32 128 256 512; do
  sips -z $s $s master.png --out icon_${s}x${s}.png
  sips -z $((s*2)) $((s*2)) master.png --out icon_${s}x${s}@2x.png
done
```

`icons/README.md` in your generated project has the same recipe, plus the
`iconutil` one-liner for building a `.icns` — which you only need if you
later freeze a distributable `.app` bundle.

### 7. Verify as you go

```bash
QT_QPA_PLATFORM=offscreen pytest
```

The generated `tests/test_app.py` builds your window headless — extend it in
the same style (construct the window, assert on your model, export a canvas
to a temp file). This is exactly how the framework tests itself.

When you want more, the deeper references live in the bundled skill (they're
good reading for humans too): `.claude/skills/sciapp/reference/api.md` (every
public signature), `conventions.md`, `canvas.md`, and
`recipes/new_app.md`.

---

## Troubleshooting

- **`qt.qpa.plugin: Could not load the Qt platform plugin` / tests hang in
  CI** — run headless: `QT_QPA_PLATFORM=offscreen pytest`. On bare Linux
  containers, first install the system libs Qt needs:
  `scripts/setup-test-env.sh` in this repo.
- **Markdown web preview errors / blank in containers** — QtWebEngine needs
  the `[web]` extra installed, and in sandboxed/root environments:
  `QTWEBENGINE_DISABLE_SANDBOX=1` and
  `QTWEBENGINE_CHROMIUM_FLAGS="--no-sandbox --disable-gpu"`.
- **Why is Qt pinned to 6.8?** Deliberate: PySide6 6.9 has Windows DLL
  issues, and Qt 6.11 regresses `QSvgRenderer` in a way that breaks vector
  export. Don't bump the pin in your app.
- **My project has no `.claude/skills/sciapp/`** — it was scaffolded with
  `--no-skill`, or predates skill bundling. Copy it from an installed
  sciappkit:

  ```bash
  python -c "import sciappkit.scaffold as s, pathlib; print(pathlib.Path(s.__file__).parent / 'skill')"
  cp -r "$(python -c "import sciappkit.scaffold as s, pathlib; print(pathlib.Path(s.__file__).parent / 'skill')")" .claude/skills/sciapp
  ```
- **Something else?** Open an issue:
  <https://github.com/w00ber/scikit-app/issues>.
