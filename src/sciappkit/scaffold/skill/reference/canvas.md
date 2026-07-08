# Choosing and wiring a canvas

sciappkit deliberately does **not** unify the two canvas kinds under one
base class. Pick per app (or use both); a thin `CanvasController` protocol
lets the same window drive either.

## Which style?

| Pick | When | Export target |
| --- | --- | --- |
| `scene` | vector editing / diagrams / node graphs on a `QGraphicsScene` | the scene |
| `mpl` | plots, data viz, anything matplotlib draws | the `Figure` |
| `both` | a scene editor *and* a plot panel (tabs); export follows focus | per active tab |

`create-sciapp --canvas-style scene|mpl|both` scaffolds the right
`build_controllers()` for you.

## The contract

A controller satisfies:
```python
widget() -> QWidget            # embed this
export_target() -> Any         # Figure (mpl) or QGraphicsScene
exporter                       # an Exporter paired with the target
fit_to_content() -> None
set_interaction_mode(mode) -> None
mode_changed                   # Signal(object)
```
`SciAppMainWindow` takes one controller (fills the center) or several
(becomes tabs), and resolves the *active* one by focus/tab so Export/Copy
hit the right canvas.

## Scene canvas

```python
from sciappkit.canvas.scene_canvas import GraphicsSceneBase, GraphicsViewBase
from sciappkit.canvas.protocol import SceneCanvasController

scene = GraphicsSceneBase()                  # has .undo_stack and .mode
scene.addRect(0, 0, 160, 100)
view = GraphicsViewBase(scene)               # zoom/pan/fit/grid/snap built in
controller = SceneCanvasController(view)     # exporter defaults to SceneExporter
```
Subclass `GraphicsViewBase` for app interaction (item creation, selection
semantics). The base only owns zoom, pan, fit-to-content, grid drawing
(wired to `sciappkit.canvas.grid`), and the interaction-mode signal.
`GraphicsViewBase` keeps a reference to its scene — but still hold your own
reference to any scene/model you mutate.

## Matplotlib canvas

```python
from sciappkit.canvas.mpl_canvas import MplCanvas
from sciappkit.canvas.protocol import MplCanvasController

canvas = MplCanvas(show_axes=True)           # .fig / .ax; re-emits mouse events as signals
canvas.ax.plot(x, y)
controller = MplCanvasController(canvas)     # exporter defaults to MplExporter
```

## Both

Return two controllers from `build_controllers()`; they become tabs and the
shared Export/Copy menu follows the focused tab:
```python
return [SceneCanvasController(view), MplCanvasController(canvas)]
```

## Export & clipboard

Uniform across kinds — the host already calls these, but directly:
```python
ctrl.exporter.export_pdf(ctrl.export_target(), "out.pdf")
ctrl.exporter.copy_to_clipboard(ctrl.export_target())   # PDF (vector) + PNG
```
`copy_to_clipboard` routes through a platform cascade (macOS NSPasteboard →
Qt fallback). On Linux it uses Qt's `QMimeData`.
