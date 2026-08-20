"""The directional sun: its geometry, and the modeless window that aims it."""

from __future__ import annotations

import math

import pytest

from sciappkit.app.lighting import (
    STEP_DEG,
    LightingWindow,
    SunState,
    open_lighting,
    sun_direction,
)


# -- the pure half ----------------------------------------------------------

class TestTheDirection:
    def test_theta_is_measured_from_the_up_axis(self):
        """0 is straight overhead — these apps draw wafers, so 'up' is the
        substrate normal, not the camera."""
        assert sun_direction(0, 0) == pytest.approx((0.0, 0.0, 1.0))
        assert sun_direction(0, 123) == pytest.approx((0.0, 0.0, 1.0))

    def test_ninety_degrees_grazes_the_surface(self):
        assert sun_direction(90, 0) == pytest.approx((1.0, 0.0, 0.0), abs=1e-9)
        assert sun_direction(90, 90) == pytest.approx((0.0, 1.0, 0.0), abs=1e-9)

    def test_phi_turns_counter_clockwise_in_plan(self):
        x, y, _ = sun_direction(90, 45)
        assert x == pytest.approx(y)
        assert x > 0

    def test_it_is_a_unit_vector(self):
        for theta in (0, 17, 45, 90):
            for phi in (0, 33, 180, 300):
                v = sun_direction(theta, phi)
                assert math.sqrt(sum(c * c for c in v)) == pytest.approx(1.0)


class TestTheDefaultsAreThePreFeatureLook:
    """A project saved before this feature, or one never touched, must
    render exactly as it used to."""

    def test_no_sun_and_no_occlusion(self):
        st = SunState()
        assert st.enabled is False
        assert st.ao is False

    def test_the_fill_is_the_intensity_the_canvases_already_used(self):
        assert SunState().fill == pytest.approx(0.3)


# -- the window -------------------------------------------------------------

@pytest.fixture()
def window(qapp):
    seen = []
    win = LightingWindow(SunState(), seen.append)
    win.seen = seen
    yield win
    win.close()


class TestTheWindow:
    def test_it_is_modeless_and_does_not_hold_the_app_open(self, window):
        """Lighting is judged by looking at the model, so the controls have
        to stay usable while the model is being looked at."""
        from PySide6.QtCore import Qt

        assert window.isModal() is False
        assert window.testAttribute(Qt.WidgetAttribute.WA_QuitOnClose) is False

    def test_editing_a_control_reports_a_new_state(self, window):
        window.controls["enabled"].setChecked(True)
        assert window.seen and window.seen[-1].enabled is True

    def test_the_angles_snap(self, window):
        assert window.controls["theta"].singleStep() == STEP_DEG
        assert window.controls["dial"].singleStep() == STEP_DEG

    def test_the_azimuth_wraps(self, window):
        """φ is circular; 359 -> 0 must not be a long drag back."""
        assert window.controls["dial"].wrapping() is True

    def test_the_sun_controls_are_dead_while_it_is_off(self, window):
        assert window.controls["theta"].isEnabled() is False
        window.controls["enabled"].setChecked(True)
        assert window.controls["theta"].isEnabled() is True

    def test_reset_restores_the_original_look(self, window):
        c = window.controls
        c["enabled"].setChecked(True)
        c["theta"].setValue(15)
        c["ao"].setChecked(True)
        window.reset_button.click()
        assert window.seen[-1] == SunState()

    def test_there_is_no_default_button_without_somewhere_to_put_it(self, window):
        assert window.save_default_button is None

    def test_set_as_default_reports_the_current_state(self, qapp):
        saved = []
        win = LightingWindow(SunState(), lambda _s: None,
                             on_save_default=saved.append)
        win.controls["enabled"].setChecked(True)
        win.controls["theta"].setValue(20)
        win.save_default_button.click()
        assert saved and saved[-1].enabled is True
        assert saved[-1].theta_deg == 20
        win.close()


class TestOpening:
    def test_one_window_per_owner_reused(self, qapp):
        from PySide6.QtWidgets import QWidget

        owner = QWidget()
        a = open_lighting(owner, SunState(), lambda _s: None)
        b = open_lighting(owner, SunState(), lambda _s: None)
        assert a is b
        owner.deleteLater()

    def test_reopening_reloads_the_current_state(self, qapp):
        from PySide6.QtWidgets import QWidget

        owner = QWidget()
        win = open_lighting(owner, SunState(), lambda _s: None)
        open_lighting(owner, SunState(enabled=True, theta_deg=25),
                      lambda _s: None)
        assert win.controls["enabled"].isChecked() is True
        assert win.controls["theta"].value() == 25
        owner.deleteLater()
