"""A directional "sun" over a scene, and the modeless window that aims it.

No VTK here — sciappkit ships none, deliberately. What lives here is the
pure direction math and the Qt panel; applying the result to a renderer is
the app's job, because only the app knows what its renderer is.

The angles are measured from the SCENE'S UP AXIS (+Z), not from the
camera: these apps draw wafers, "up" is the substrate normal, and a light
that followed the camera would defeat the purpose — the whole point is a
fixed raking light that makes two adjacent faces of one material read
differently.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

__all__ = ["SunState", "sun_direction", "LightingWindow", "open_lighting"]

#: Angles snap to this. Fine control is not useful here — the difference a
#: degree makes is invisible, and a coarse grid makes the control quick.
STEP_DEG = 5


@dataclass(frozen=True)
class SunState:
    """Everything the lighting window edits.

    Defaults ARE the look these apps had before the feature existed: no
    sun, the 0.3 camera fill, no ambient occlusion. So a project saved
    before this, or one whose lighting was never touched, renders exactly
    as it used to.
    """

    enabled: bool = False
    #: Polar angle from +Z. 0 = straight overhead, 90 = grazing.
    theta_deg: float = 45.0
    #: Azimuth in the plan, counter-clockwise from +X.
    phi_deg: float = 135.0
    intensity: float = 0.8
    #: The camera-following fill that keeps a section cut's walls lit.
    fill: float = 0.3
    ao: bool = False
    ao_strength: float = 0.5


def sun_direction(theta_deg: float, phi_deg: float) -> tuple[float, float, float]:
    """Unit vector FROM the scene TOWARD the light, θ measured from +Z.

    A directional light is placed along this from the focal point; the
    distance is irrelevant (the light is non-positional, so only the
    direction is read), which is what "at infinity" means here.
    """
    theta = math.radians(theta_deg)
    phi = math.radians(phi_deg)
    return (math.sin(theta) * math.cos(phi),
            math.sin(theta) * math.sin(phi),
            math.cos(theta))


def _snap(value: float) -> int:
    return int(round(float(value) / STEP_DEG) * STEP_DEG)


class LightingWindow:  # pragma: no cover — thin Qt shell over SunState
    """Modeless lighting controls. See :func:`open_lighting`."""

    def __new__(cls, state: SunState, on_change, parent=None,
                on_save_default=None):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import (
            QCheckBox,
            QDial,
            QDialog,
            QDialogButtonBox,
            QDoubleSpinBox,
            QFormLayout,
            QLabel,
            QSpinBox,
            QVBoxLayout,
        )

        dlg = QDialog(parent)
        dlg.setWindowTitle("Lighting")
        # A real window, not a dialog-on-top: lighting is judged by looking
        # at the model, so this must not sit above the thing it describes
        # or keep the app alive on its own.
        dlg.setWindowFlags(Qt.WindowType.Window)
        dlg.setModal(False)
        dlg.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)

        outer = QVBoxLayout(dlg)
        form = QFormLayout()
        outer.addLayout(form)

        enabled = QCheckBox("Directional light")
        form.addRow(enabled)

        # Azimuth is genuinely circular and a dial reads as a compass over
        # the chip; elevation is not, so it stays a spin box.
        dial = QDial()
        dial.setRange(0, 360)
        dial.setSingleStep(STEP_DEG)
        dial.setPageStep(STEP_DEG * 3)
        dial.setNotchesVisible(True)
        dial.setWrapping(True)
        dial.setFixedSize(96, 96)
        form.addRow("Direction (φ)", dial)
        phi_label = QLabel("")
        form.addRow("", phi_label)

        theta = QSpinBox()
        theta.setRange(0, 90)
        theta.setSingleStep(STEP_DEG)
        theta.setSuffix("°")
        theta.setToolTip("0° = straight overhead, 90° = grazing the surface")
        form.addRow("Elevation (θ)", theta)

        intensity = QDoubleSpinBox()
        intensity.setRange(0.0, 2.0)
        intensity.setSingleStep(0.05)
        form.addRow("Brightness", intensity)

        fill = QDoubleSpinBox()
        fill.setRange(0.0, 1.0)
        fill.setSingleStep(0.05)
        fill.setToolTip("Light that follows the camera. Keeps a cross-section's "
                        "walls from going black; 0 makes the sun harsher.")
        form.addRow("Fill", fill)

        ao = QCheckBox("Ambient occlusion")
        ao.setToolTip("Darkens creases and contacts. Usually the better tool "
                      "for telling apart adjacent faces of one material.")
        form.addRow(ao)
        ao_strength = QDoubleSpinBox()
        ao_strength.setRange(0.0, 1.0)
        ao_strength.setSingleStep(0.05)
        form.addRow("Occlusion", ao_strength)

        widgets = (enabled, dial, theta, intensity, fill, ao, ao_strength)

        def load(st: SunState) -> None:
            for w in widgets:
                w.blockSignals(True)
            enabled.setChecked(st.enabled)
            dial.setValue(_snap(st.phi_deg) % 360)
            theta.setValue(_snap(st.theta_deg))
            intensity.setValue(st.intensity)
            fill.setValue(st.fill)
            ao.setChecked(st.ao)
            ao_strength.setValue(st.ao_strength)
            for w in widgets:
                w.blockSignals(False)
            _sync_enabled()

        def _sync_enabled() -> None:
            on = enabled.isChecked()
            for w in (dial, theta, intensity):
                w.setEnabled(on)
            ao_strength.setEnabled(ao.isChecked())
            phi_label.setText(f"{dial.value()}°")

        def _current() -> SunState:
            return SunState(
                enabled=enabled.isChecked(),
                theta_deg=float(theta.value()),
                phi_deg=float(dial.value()),
                intensity=float(intensity.value()),
                fill=float(fill.value()),
                ao=ao.isChecked(),
                ao_strength=float(ao_strength.value()),
            )

        def emit() -> None:
            _sync_enabled()
            on_change(_current())

        enabled.toggled.connect(lambda *_: emit())
        dial.valueChanged.connect(lambda v: (dial.setValue(_snap(v) % 360)
                                             if _snap(v) % 360 != v else emit()))
        theta.valueChanged.connect(lambda *_: emit())
        intensity.valueChanged.connect(lambda *_: emit())
        fill.valueChanged.connect(lambda *_: emit())
        ao.toggled.connect(lambda *_: emit())
        ao_strength.valueChanged.connect(lambda *_: emit())

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        reset = buttons.addButton("Reset",
                                  QDialogButtonBox.ButtonRole.ResetRole)
        reset.setToolTip("Back to the default lighting")
        reset.clicked.connect(lambda: (load(SunState()), emit()))
        save_default = None
        if on_save_default is not None:
            # Lighting is saved per PROJECT (it belongs with the camera —
            # a framing lit one way, reopened lit another, is not the
            # picture that was saved), so this is how a preference outlives
            # one project instead.
            save_default = buttons.addButton(
                "Set as Default", QDialogButtonBox.ButtonRole.ActionRole)
            save_default.setToolTip("Use this lighting for new projects")

            def _save() -> None:
                on_save_default(_current())
                save_default.setText("Saved")

            save_default.clicked.connect(_save)
        buttons.rejected.connect(dlg.close)
        outer.addWidget(buttons)

        load(state)
        dlg.load_state = load
        dlg.reset_button = reset
        dlg.save_default_button = save_default
        dlg.controls = {
            "enabled": enabled, "dial": dial, "theta": theta,
            "intensity": intensity, "fill": fill, "ao": ao,
            "ao_strength": ao_strength,
        }
        return dlg


def open_lighting(owner, state: SunState, on_change, on_save_default=None):
    """Show the lighting window for *owner*, reusing the one it already has.

    One window per owner, raised rather than stacked — the same rule the
    walkthrough reader follows, and for the same reason: it is kept open
    while the thing it controls is being looked at.
    """
    win = getattr(owner, "_lighting_window", None)
    if win is None:
        win = LightingWindow(state, on_change, parent=owner,
                             on_save_default=on_save_default)
        owner._lighting_window = win
    else:
        win.load_state(state)
    win.show()
    win.raise_()
    win.activateWindow()
    return win
