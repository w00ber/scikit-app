"""Tests for the project scaffold (sciappkit.scaffold).

The end-to-end check (the plan's M2 gate): generate an app for each canvas
style, import it, build the window headless, and export a canvas.
"""

from __future__ import annotations

import importlib
import sys

import pytest

from sciappkit.scaffold import CANVAS_STYLES, create_app
from sciappkit.scaffold.generator import _to_class, _to_package


@pytest.fixture
def restore_defaults_path():
    # Generated settings.py repoints the global defaults loader; restore it.
    yield
    import sciappkit.settings.defaults as d

    d.set_defaults_path(d.Path(d.__file__).parent / "defaults.yaml")


def _import_generated(project, pkg):
    src = project / "src"
    sys.path.insert(0, str(src))
    return importlib.import_module(f"{pkg}.main_window")


def _forget(pkg, src):
    if str(src) in sys.path:
        sys.path.remove(str(src))
    for name in list(sys.modules):
        if name == pkg or name.startswith(pkg + "."):
            del sys.modules[name]


def test_generated_file_set(tmp_path):
    project = create_app(tmp_path, app_name="My Tool", canvas_style="both")
    assert project.name == "my_tool"
    expected = [
        "pyproject.toml", "README.md", "CLAUDE.md", ".gitignore",
        "src/my_tool/__init__.py", "src/my_tool/__main__.py",
        "src/my_tool/app.py", "src/my_tool/main_window.py",
        "src/my_tool/canvas.py", "src/my_tool/settings.py",
        "src/my_tool/shortcuts.py", "src/my_tool/defaults.yaml",
        "src/my_tool/icons/README.md",
        "docs/help.md", "docs/tutorial.md", "tests/test_app.py",
        # Packaging: PyInstaller spec + launcher shim + release workflow.
        "my_tool.spec", "my_tool_launcher.py", ".github/workflows/build.yml",
        # The bundled Claude Code skill (include_skill defaults to True).
        ".claude/skills/sciapp/SKILL.md",
        ".claude/skills/sciapp/reference/api.md",
        ".claude/skills/sciapp/recipes/new_app.md",
        ".claude/skills/sciapp/examples/minimal_mpl.py",
    ]
    for rel in expected:
        assert (project / rel).is_file(), f"missing {rel}"


def test_packaging_files_are_valid(tmp_path):
    """The emitted spec/launcher/workflow must be syntactically sound."""
    import yaml

    project = create_app(tmp_path, app_name="Pack Tool")

    launcher = (project / "pack_tool_launcher.py").read_text(encoding="utf-8")
    compile(launcher, "pack_tool_launcher.py", "exec")
    assert "from pack_tool.app import main" in launcher

    spec = (project / "pack_tool.spec").read_text(encoding="utf-8")
    assert "__PKG__" not in spec and "__TITLE__" not in spec  # fully rendered
    assert 'SRC / "pack_tool"' in spec
    assert "pack_tool_launcher.py" in spec
    assert "backend_svg" in spec  # frozen exports depend on this hiddenimport

    workflow = yaml.safe_load((project / ".github/workflows/build.yml").read_text(encoding="utf-8"))
    # PyYAML parses the bare `on:` key as boolean True.
    triggers = workflow.get("on", workflow.get(True))
    assert triggers["push"]["tags"] == ["v*"]
    assert "workflow_dispatch" in triggers
    assert set(workflow["jobs"]) == {"test", "build", "release"}
    assert workflow["jobs"]["build"]["needs"] == "test"
    assert workflow["jobs"]["release"]["needs"] == "build"


def test_skill_can_be_skipped(tmp_path):
    project = create_app(tmp_path, app_name="Bare Tool", include_skill=False)
    assert not (project / ".claude").exists()


def test_cli_no_skill_flag(tmp_path):
    from sciappkit.scaffold.cli import main

    rc = main(["Flagged App", "-d", str(tmp_path), "--no-skill"])
    assert rc == 0
    project = tmp_path / "flagged_app"
    assert (project / "pyproject.toml").is_file()
    assert not (project / ".claude").exists()


@pytest.mark.parametrize("style,expected", [("scene", 1), ("mpl", 1), ("both", 2)])
def test_generate_build_export(qapp, tmp_path, restore_defaults_path, style, expected):
    project = create_app(tmp_path, app_name=f"Gen {style}", canvas_style=style)
    pkg = _to_package(f"Gen {style}")
    try:
        mod = _import_generated(project, pkg)
        # The entry-point module must import cleanly too (icon wiring etc.).
        importlib.import_module(f"{pkg}.app")
        window = getattr(mod, _to_class(pkg))()
        assert len(window._controllers) == expected
        ctrl = window.active_controller()
        out = tmp_path / f"{style}.png"
        ctrl.exporter.export_png(ctrl.export_target(), str(out))
        assert out.exists() and out.stat().st_size > 0
    finally:
        _forget(pkg, project / "src")


def test_invalid_canvas_style_raises(tmp_path):
    with pytest.raises(ValueError):
        create_app(tmp_path, app_name="X", canvas_style="bogus")


def test_existing_nonempty_dir_guarded(tmp_path):
    create_app(tmp_path, app_name="Dup")
    with pytest.raises(FileExistsError):
        create_app(tmp_path, app_name="Dup")
    # force overwrites without error.
    create_app(tmp_path, app_name="Dup", force=True)


def test_package_name_derivation():
    assert _to_package("Spectrum Tool!") == "spectrum_tool"
    assert _to_package("3D Viewer") == "app_3d_viewer"
    assert _to_class("spectrum_tool") == "SpectrumToolWindow"


def test_cli_creates_project(tmp_path):
    from sciappkit.scaffold.cli import main

    rc = main(["Cli App", "-d", str(tmp_path), "-c", "scene"])
    assert rc == 0
    assert (tmp_path / "cli_app" / "pyproject.toml").is_file()


def test_cli_rejects_bad_style(tmp_path, capsys):
    from sciappkit.scaffold.cli import main

    with pytest.raises(SystemExit):
        # argparse choices reject this before our code runs.
        main(["App", "-d", str(tmp_path), "-c", "nope"])
