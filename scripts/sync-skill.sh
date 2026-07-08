#!/usr/bin/env bash
# Sync the repo's own Claude Code skill mirror from the canonical copy.
#
# The canonical `sciapp` skill lives inside the package at
#   src/sciappkit/scaffold/skill/
# so `create-sciapp` can bundle it into generated projects (it ships as
# package data). Claude Code, however, discovers skills at
#   .claude/skills/<name>/
# so this repo keeps a tracked mirror there. Edit the canonical copy, then
# run this script; tests/test_skill_sync.py fails if the two trees drift.
#
# Safe to re-run.
set -euo pipefail

repo="$(cd "$(dirname "$0")/.." && pwd)"
canonical="$repo/src/sciappkit/scaffold/skill"
mirror="$repo/.claude/skills/sciapp"

rm -rf "$mirror"
mkdir -p "$mirror"
# Copy everything except bytecode caches.
(cd "$canonical" && find . -name __pycache__ -prune -o -type f -print) |
while IFS= read -r rel; do
    mkdir -p "$mirror/$(dirname "$rel")"
    cp "$canonical/$rel" "$mirror/$rel"
done

echo "Synced $canonical -> $mirror"
