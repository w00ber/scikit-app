"""Tests for sciappkit.settings.store."""

from __future__ import annotations

import json

import pytest

from sciappkit.settings.store import (
    SetCodec,
    Setting,
    SettingsStore,
    build_schema,
)


class DictLoader:
    """Minimal DefaultsLoader backed by a nested dict."""

    def __init__(self, data):
        self._data = data

    def get(self, section, key, fallback=None):
        return self._data.get(section, {}).get(key, fallback)


SCHEMA = [
    Setting("theme", "system", section="theme", key="mode"),
    Setting("grid_spacing", 20.0, section="grid", key="spacing"),
    Setting("snap", True),
    Setting("hidden", set(), codec=SetCodec(), mutable=True),
]


def _store(tmp_path, loader=None, **kw):
    return SettingsStore(
        "testapp",
        SCHEMA,
        loader or DictLoader({}),
        settings_dir=tmp_path,
        **kw,
    )


def test_defaults_seed_from_loader(tmp_path):
    loader = DictLoader({"grid": {"spacing": 5.0}, "theme": {"mode": "dark"}})
    store = _store(tmp_path, loader)
    assert store.grid_spacing == 5.0      # from loader
    assert store.theme == "dark"          # from loader
    assert store.snap is True             # from literal default (no section)


def test_defaults_fall_back_to_literal(tmp_path):
    store = _store(tmp_path)  # empty loader
    assert store.grid_spacing == 20.0
    assert store.theme == "system"


def test_attribute_set_and_save_load_roundtrip(tmp_path):
    store = _store(tmp_path)
    store.theme = "light"
    store.grid_spacing = 12.5
    store.snap = False
    store.hidden = {"b", "a"}
    store.save()

    # File is valid JSON with encoded values (set -> sorted list).
    data = json.loads(store.path.read_text())
    assert data["hidden"] == ["a", "b"]

    # A fresh store loads the persisted values.
    store2 = _store(tmp_path)
    assert store2.theme == "light"
    assert store2.grid_spacing == 12.5
    assert store2.snap is False
    assert store2.hidden == {"a", "b"}


def test_path_and_first_launch(tmp_path):
    store = _store(tmp_path)
    assert store.path == tmp_path / "settings.json"
    assert store.is_first_launch is True
    store.save()
    store2 = _store(tmp_path)
    assert store2.is_first_launch is False


def test_mutable_default_not_shared(tmp_path):
    a = _store(tmp_path)
    a.hidden.add("x")
    b = _store(tmp_path / "other")
    assert b.hidden == set()  # b's default not polluted by a's mutation


def test_reset_all_and_reset_field(tmp_path):
    store = _store(tmp_path)
    store.theme = "dark"
    store.grid_spacing = 99.0
    store.reset_field("theme")
    assert store.theme == "system"
    assert store.grid_spacing == 99.0
    store.reset_all()
    assert store.grid_spacing == 20.0


def test_reset_section(tmp_path):
    loader = DictLoader({"grid": {"spacing": 7.0}})
    store = _store(tmp_path, loader)
    store.grid_spacing = 1.0
    store.reset_section("grid")
    assert store.grid_spacing == 7.0


def test_corrupt_file_keeps_defaults(tmp_path):
    (tmp_path / "settings.json").write_text("not json{{{")
    store = _store(tmp_path)  # autoload should swallow the error
    assert store.theme == "system"


def test_unknown_keys_ignored(tmp_path):
    (tmp_path / "settings.json").write_text(json.dumps({"theme": "dark", "bogus": 1}))
    store = _store(tmp_path)
    assert store.theme == "dark"
    assert "bogus" not in store.field_names()


def test_update_and_as_dict(tmp_path):
    store = _store(tmp_path)
    store.update(theme="light", grid_spacing=8.0)
    assert store.theme == "light"
    snap = store.as_dict()
    assert snap["theme"] == "light"
    assert snap["hidden"] == []  # encoded form


def test_set_unknown_field_raises(tmp_path):
    store = _store(tmp_path)
    with pytest.raises(KeyError):
        store.set("nope", 1)


def test_build_schema_flattens():
    schema = build_schema(Setting("a"), [Setting("b"), Setting("c")])
    assert [s.name for s in schema] == ["a", "b", "c"]


def test_qcolor_codec_roundtrip(qapp, tmp_path):
    from PySide6.QtGui import QColor

    from sciappkit.settings.store import QColorCodec

    schema = [
        Setting("stroke", QColor(50, 50, 50), section="shape", key="stroke_color",
                codec=QColorCodec()),
    ]
    loader = DictLoader({"shape": {"stroke_color": "#ff112233"}})
    store = SettingsStore("ctest", schema, loader, settings_dir=tmp_path)
    # Seeded (and decoded) from the loader's hex string.
    assert isinstance(store.stroke, QColor)
    assert store.stroke.name(QColor.NameFormat.HexArgb) == "#ff112233"

    store.stroke = QColor(0, 128, 255)
    store.save()
    assert json.loads(store.path.read_text())["stroke"] == "#ff0080ff"

    store2 = SettingsStore("ctest", schema, loader, settings_dir=tmp_path)
    assert store2.stroke.name(QColor.NameFormat.HexArgb) == "#ff0080ff"
