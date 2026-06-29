# sciappkit public API

Signatures with one-line semantics. Import paths are exact.

## app

### `sciappkit.app.main_window.SciAppMainWindow(QMainWindow)`
```python
SciAppMainWindow(app_name, settings, shortcuts, controllers, *, parent=None)
```
Base window. `controllers` is one `CanvasController` or a sequence (a single
one fills the center; several become tabs). Owns File/Edit/View menus,
Export→SVG/PNG/PDF and Copy-to-clipboard (driven by the active controller),
theming, shortcut registration, Undo/Redo (delegated to the active scene's
`undo_stack`), title/dirty tracking, and a Recent Files menu (when the
settings schema has a `recent_files` field).

Override in subclasses:
- `do_new()`, `do_open(path) -> bool`, `do_save(path) -> bool` — document I/O.
- `populate_extra_menus(menubar)` — add app menus.
Helpers: `self._add_action(menu, text, slot, shortcut_id=None, *, checkable=False)`,
`active_controller()`, `apply_theme(mode=None)`, `is_dirty()`.
Signal: `theme_changed(str)`.

### `sciappkit.app.theming`
```python
THEMES = ("system", "light", "dark")
apply_theme(app: QApplication, mode: str) -> None
hint_text_color() -> str          # muted color legible on the active theme
```

### `sciappkit.app.settings_dialog.SettingsDialog(QDialog)`
```python
SettingsDialog(settings, shortcuts=None, parent=None)
add_bool(field, label) / add_int(field,label,*,minimum,maximum,step)
add_double(field,label,*,minimum,maximum,step,decimals)
add_text(field,label) / add_choice(field,label,choices)
apply() / restore_defaults()      # OK/Apply persist; Cancel reverts
```
Auto-adds an Appearance tab when the schema has `theme`, and a Shortcuts tab
when a `ShortcutManager` is passed. Signal: `applied()`.

## settings

### `sciappkit.settings.store`
```python
Setting(name, default=None, section=None, key=None, codec=None, mutable=False)
SettingsStore(app_name, schema, defaults=None, *, settings_dir=None, autoload=True)
  .get(name) / .set(name, value) / store.<name> attribute access
  .update(**kw) / .as_dict() / .field_names()
  .reset_all() / .reset_field(name) / .reset_section(section)
  .load() / .save() / .path / .is_first_launch
SetCodec()        # set <-> sorted list
QColorCodec()     # QColor <-> #AARRGGBB (lazy Qt import)
```
Persists JSON to `~/.<app_name>/settings.json`. `section`/`key` pull the
factory default from the defaults loader; `default` is the fallback.

### `sciappkit.settings.defaults`
```python
get(section, key, fallback=None) / get_section(section) / all_defaults()
set_defaults_path(path) / reload()
```

### `sciappkit.settings.recent_files.RecentFiles`
```python
RecentFiles(store=None, *, field="recent_files", max_items=10)
  .add(path) / .remove(path) / .clear() / .items() / .prune_missing()
```

## shortcuts

### `sciappkit.shortcuts.model`
```python
Shortcut(action_id, *, default=None, mac=None, win=None, linux=None,
         display_name="", category="", description="",
         is_single_key=False, is_menu_action=False)
ShortcutRegistry(platform=None)
  .register(sc) / .register_many(scs) / .get(id) / .all() / .by_category()
  .sequence(id) / .set_override(id, seq) / .reset(id) / .reset_all()
  .conflicts(proposed=None) / .conflict_for(seq, exclude=None)
  .export_overrides() / .import_overrides(data)
```
`default` binding may be a portable string ("Ctrl+S"), a
`QKeySequence.StandardKey`, a `QKeySequence`, or int. "Ctrl" maps to ⌘ on macOS.

### `sciappkit.shortcuts.manager.ShortcutManager(QObject)`
```python
ShortcutManager(registry, app_name, parent=None, *, config_path=None)
  .apply_to(id, action) / .bind_shortcut(id, handler, parent, *, wrap_for_input=False)
  .set_sequence(id, seq) -> bool  # False on conflict
  .clear_sequence(id) / .reset(id) / .reset_all() / .apply_all()
  .load() / .save()               # ~/.<app_name>/shortcuts.json (overrides only)
signals: shortcuts_changed(), shortcut_updated(id, old, new)
```

### `sciappkit.shortcuts.editor.ShortcutEditorWidget(QWidget)`
```python
ShortcutEditorWidget(manager, parent=None)   # grouped, editable, conflict-aware
signal: shortcuts_modified()
```

## canvas

### `sciappkit.canvas.protocol`
```python
class CanvasController(Protocol):
    exporter           # an Exporter
    mode_changed       # Signal(object)
    def widget() -> QWidget
    def export_target() -> Any         # Figure or QGraphicsScene
    def fit_to_content() -> None
    def set_interaction_mode(mode) -> None

MplCanvasController(canvas, exporter=None)      # canvas: MplCanvas; target = canvas.fig
SceneCanvasController(view, exporter=None)      # view: GraphicsViewBase; target = view.scene()
```

### `sciappkit.canvas.scene_canvas`
```python
GraphicsSceneBase(QGraphicsScene)      # .undo_stack, .mode (emits mode_changed)
GraphicsViewBase(scene, parent=None, *, grid_spacing=20.0, grid_visible=True, snap_enabled=True)
  zoom_in()/zoom_out()/zoom_reset()/zoom_at(f, scene_pos)/fit_to_content()
  .grid_spacing / .grid_visible / .snap_enabled / snap(pos)
```

### `sciappkit.canvas.mpl_canvas.MplCanvas(FigureCanvasQTAgg)`
```python
MplCanvas(parent=None, width=12, height=12, dpi=100, show_axes=False)
  .fig / .ax ; signals: click_signal/release_signal/motion_signal/scroll_signal
```

### `sciappkit.canvas.grid`
```python
draw_grid(painter, rect, spacing, scale, *, minor_color=None, major_color=None)
snap_to_grid(pos, spacing) -> QPointF
```

## export

```python
class Exporter(Protocol):                       # sciappkit.export.base
    def export_svg(target, path) / export_png(target, path) / export_pdf(target, path)
    def copy_to_clipboard(target) -> bool
MplExporter(dpi=300, bbox_inches="tight")       # target = Figure
SceneExporter(export_scale=1.0)                 # target = QGraphicsScene
sciappkit.export.clipboard.copy_to_clipboard(pdf_bytes, png_bytes) -> bool
```

## undo

```python
sciappkit.undo.stack.SnapshotCommand(text, restore, before, after)
snapshot(undo_stack, text, capture, restore)    # context manager
push_snapshot(undo_stack, text, before, after, restore)
```

## widgets

```python
sciappkit.widgets.spinbox.FineControlSpinBox(QDoubleSpinBox)   # Shift=fine, Alt=coarse
sciappkit.widgets.text_edit.LineNumberTextEdit(QPlainTextEdit) # line numbers + zoom
sciappkit.widgets.code_editor.CodeEditor(parent=None, *, language="python", indent_width=4)
    code_editor_shortcut_defs() / bind_code_editor_shortcuts(manager, editor)
sciappkit.widgets.markdown_editor.MarkdownEditor(parent=None, *, backend="native"|"web",
    katex_base_url=None)   # "web" renders inline images ([web] extra)
    markdown_editor_shortcut_defs() / bind_markdown_editor_shortcuts(manager, editor)
```

## scaffold

```python
sciappkit.scaffold.create_app(target, *, app_name, package=None,
    canvas_style="both", author="", force=False) -> Path
```
