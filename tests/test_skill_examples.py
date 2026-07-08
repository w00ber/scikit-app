"""The skill's minimal examples must keep building (docs stay runnable)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

# The canonical skill lives in the package (bundled into scaffolds); the
# repo's .claude/skills/sciapp is a mirror checked by test_skill_sync.py.
_EXAMPLES = (
    Path(__file__).resolve().parent.parent
    / "src" / "sciappkit" / "scaffold" / "skill" / "examples"
)


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"skill_{name}", _EXAMPLES / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("name", ["minimal_scene", "minimal_mpl"])
def test_skill_example_builds(qapp, name):
    module = _load(name)
    win = module.build_window()
    assert win is not None
    assert len(win._controllers) == 1
