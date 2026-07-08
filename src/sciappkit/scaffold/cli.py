"""``create-sciapp`` command-line entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .generator import CANVAS_STYLES, create_app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="create-sciapp",
        description="Generate a runnable sciappkit application skeleton.",
    )
    parser.add_argument("name", help='App title, e.g. "Spectrum Tool".')
    parser.add_argument(
        "-d", "--directory", default=".",
        help="Parent directory to create the project in (default: current).",
    )
    parser.add_argument(
        "-p", "--package", default=None,
        help="Import/distribution name (derived from the title if omitted).",
    )
    parser.add_argument(
        "-c", "--canvas-style", default="both", choices=CANVAS_STYLES,
        help="Canvas kind to scaffold (default: both).",
    )
    parser.add_argument("--author", default="", help="Author name for pyproject.toml.")
    parser.add_argument(
        "-f", "--force", action="store_true",
        help="Write into an existing, non-empty project directory.",
    )
    parser.add_argument(
        "--no-skill", action="store_true",
        help="Skip copying the bundled sciapp Claude Code skill into the project.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        project = create_app(
            args.directory,
            app_name=args.name,
            package=args.package,
            canvas_style=args.canvas_style,
            author=args.author,
            force=args.force,
            include_skill=not args.no_skill,
        )
    except (ValueError, FileExistsError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    rel = Path(project)
    print(f"Created {rel}")
    print("Next steps:")
    print(f"  cd {rel}")
    print('  pip install -e ".[dev]"')
    print(f"  {project.name}            # launch")
    print("  QT_QPA_PLATFORM=offscreen pytest")
    if not args.no_skill:
        print("With Claude Code: just open the project — the sciapp skill is")
        print("preinstalled at .claude/skills/sciapp/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
