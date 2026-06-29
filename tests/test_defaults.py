"""Tests for sciappkit.settings.defaults."""

from __future__ import annotations

import pytest

from sciappkit.settings import defaults


@pytest.fixture(autouse=True)
def _restore_default_path():
    """Reset the loader back to the framework defaults after each test."""
    yield
    import sciappkit.settings.defaults as d
    d.set_defaults_path(d.Path(d.__file__).parent / "defaults.yaml")


def test_framework_defaults_load():
    assert defaults.get("grid", "spacing") == 20.0
    assert defaults.get("grid", "major_every") == 5
    assert defaults.get("theme", "mode") == "system"


def test_get_fallback_for_missing_key():
    assert defaults.get("grid", "nope", "fallback") == "fallback"
    assert defaults.get("missing_section", "x", 42) == 42


def test_get_section_returns_copy():
    section = defaults.get_section("grid")
    assert section["spacing"] == 20.0
    section["spacing"] = 999  # mutating the copy must not affect the cache
    assert defaults.get("grid", "spacing") == 20.0


def test_all_defaults_includes_sections():
    data = defaults.all_defaults()
    assert "grid" in data
    assert "theme" in data


def test_set_defaults_path_and_reload(tmp_path):
    custom = tmp_path / "defaults.yaml"
    custom.write_text(
        "wiring:\n  line_width: 3.0\n  line_color: \"#000000\"\n",
        encoding="utf-8",
    )
    defaults.set_defaults_path(custom)
    assert defaults.get("wiring", "line_width") == 3.0
    assert defaults.get("wiring", "line_color") == "#000000"
    # Old framework keys are gone now that we switched files.
    assert defaults.get("grid", "spacing") is None


def test_simple_yaml_parser_types(tmp_path):
    path = tmp_path / "d.yaml"
    path.write_text(
        "section:\n"
        "  an_int: 5\n"
        "  a_float: 2.5\n"
        "  a_bool: true\n"
        "  a_str: \"hello\"  # trailing comment\n",
        encoding="utf-8",
    )
    parsed = defaults._parse_simple_yaml(path)
    assert parsed["section"]["an_int"] == 5
    assert isinstance(parsed["section"]["an_int"], int)
    assert parsed["section"]["a_float"] == 2.5
    assert parsed["section"]["a_bool"] is True
    assert parsed["section"]["a_str"] == "hello"
