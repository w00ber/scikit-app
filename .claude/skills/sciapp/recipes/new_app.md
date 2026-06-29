# Recipe: build a new sciappkit app

## 1. Scaffold

```bash
create-sciapp "Spectrum Tool" --canvas-style both
cd spectrum_tool
pip install -e ".[dev]"
QT_QPA_PLATFORM=offscreen pytest      # the generated smoke test passes
spectrum_tool                          # launch
```

You now have `src/spectrum_tool/{app,main_window,canvas,settings,shortcuts}.py`,
`defaults.yaml`, `docs/`, a test, and `CLAUDE.md`.

## 2. Put something on the canvas

Edit `canvas.py` → `build_controllers()`. For a plot:
```python
canvas = MplCanvas(show_axes=True)
canvas.ax.plot(freqs, np.abs(response))
return [MplCanvasController(canvas)]
```
For a scene editor, subclass `GraphicsViewBase` and add your interaction;
return `SceneCanvasController(view)`. See `reference/canvas.md`.

## 3. Add a setting

In `settings.py` add to `SCHEMA`:
```python
Setting("line_width", 2.0, section="plot", key="line_width"),
```
Add the same key to `defaults.yaml` under `plot:`. Read it as
`store.line_width`. Surface it in Preferences (`main_window.py`):
```python
dialog.add_double("line_width", "Line width", minimum=0.5, maximum=10, step=0.5)
```

## 4. Add a shortcut + a menu action

In `shortcuts.py` register a `Shortcut("tools.run", default="Ctrl+R",
category="Tools", display_name="Run")`. In `main_window.py`:
```python
def populate_extra_menus(self, menubar):
    tools = menubar.addMenu("&Tools")
    self._add_action(tools, "&Run", self.run, "tools.run")
```
`_add_action` binds the shortcut via the manager (rebindable in the
Shortcuts tab of Preferences). For a keys-only action (no menu item) use
`self._shortcuts.bind_shortcut("tools.run", self.run, self)`.

## 5. Wire the document model

Implement the hooks in `main_window.py` — Export/Copy/Recent/title/dirty are
already handled by the base:
```python
def do_new(self):  self.model = Model()
def do_open(self, path):
    self.model = Model.load(json.loads(Path(path).read_text())); return True
def do_save(self, path):
    Path(path).write_text(json.dumps(self.model.to_dict())); return True
```
For undo without per-op commands, wrap mutations:
```python
from sciappkit.undo.stack import snapshot
with snapshot(scene.undo_stack, "Edit", self.model.to_dict, self.model.load):
    self.model.mutate()
```

## 6. Add editors (optional)

Dock a code or markdown editor and bind its shortcuts:
```python
from sciappkit.widgets.markdown_editor import (MarkdownEditor,
    markdown_editor_shortcut_defs, bind_markdown_editor_shortcuts)
# register markdown_editor_shortcut_defs() in shortcuts.py first
notes = MarkdownEditor(backend="web")        # inline images; needs [web] extra
bind_markdown_editor_shortcuts(self._shortcuts, notes)
```

## 7. Verify

`QT_QPA_PLATFORM=offscreen pytest`. Add tests that build the window and
export a canvas (see the generated `tests/test_app.py`). Keep the Qt pin at
6.8 and keep QtWebEngine behind the `[web]` extra.
