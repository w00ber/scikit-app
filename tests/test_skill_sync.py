"""The repo's .claude/skills/sciapp mirror must match the canonical skill.

The canonical `sciapp` skill lives in the package (so `create-sciapp` can
bundle it into generated projects as package data):

    src/sciappkit/scaffold/skill/

Claude Code discovers skills at `.claude/skills/<name>/`, so this repo keeps
a tracked mirror there. Edit the canonical copy and run
``scripts/sync-skill.sh``; this test fails if the two trees drift.
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CANONICAL = REPO / "src" / "sciappkit" / "scaffold" / "skill"
MIRROR = REPO / ".claude" / "skills" / "sciapp"

_SYNC_HINT = "skill trees drifted — edit src/sciappkit/scaffold/skill/ then run scripts/sync-skill.sh"


def _tree(root: Path) -> dict[str, bytes]:
    """Map of relative path -> content, ignoring bytecode caches."""
    out: dict[str, bytes] = {}
    for path in sorted(root.rglob("*")):
        if path.is_dir() or "__pycache__" in path.parts:
            continue
        out[str(path.relative_to(root))] = path.read_bytes()
    return out


def test_skill_trees_exist():
    assert CANONICAL.is_dir(), f"canonical skill missing at {CANONICAL}"
    assert MIRROR.is_dir(), f"mirror skill missing at {MIRROR} — run scripts/sync-skill.sh"


def test_skill_mirror_matches_canonical():
    canonical = _tree(CANONICAL)
    mirror = _tree(MIRROR)
    assert set(canonical) == set(mirror), _SYNC_HINT
    for rel, content in canonical.items():
        assert mirror[rel] == content, f"{rel}: {_SYNC_HINT}"
